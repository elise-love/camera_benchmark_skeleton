import argparse
import csv
import importlib.util
import json
import sys
import types
import warnings
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
from torchvision import models, transforms
from torchvision.transforms import functional as tvf


ROOT = Path(__file__).resolve().parent
PYTHON_EXE_HINT = (
    r"C:\Users\user\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)

NIQE_DIR = ROOT / "niqe"
ILNIQE_DIR = ROOT / "il-niqe" / "IL-NIQE"
NIMA_DIR = ROOT / "Neural-IMage-Assessment" / "Neural-IMage-Assessment"
DEEPLPF_DIR = ROOT / "deeplpf-image-enhancement" / "deeplpf-image-enhancement"

DEFAULT_IMAGE = (
    DEEPLPF_DIR
    / "adobe5k_dpe"
    / "deeplpf_example_test_input"
    / "a4576-DSC_0217_input.png"
)
DEFAULT_REFERENCE = (
    DEEPLPF_DIR
    / "adobe5k_dpe"
    / "deeplpf_example_test_output"
    / "a4576-DSC_0217_gt.png"
)
DEFAULT_DEEPLPF_MODEL = (
    DEEPLPF_DIR
    / "pretrained_models"
    / "adobe_dpe"
    / "deeplpf_validpsnr_23.378_validloss_0.033_testpsnr_23.904_testloss_0.031_epoch_424_model.pt"
)
SUPPORTED_IMAGE_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def image_to_gray_array(image_path):
    return np.array(Image.open(image_path).convert("LA"))[:, :, 0]


def score_niqe(image_path):
    sys.path.insert(0, str(NIQE_DIR))
    niqe_module = load_module("local_niqe", NIQE_DIR / "niqe.py")
    score = float(niqe_module.niqe(image_to_gray_array(image_path)))
    return {
        "status": "ok",
        "score": score,
        "interpretation": "lower is better; blind natural-image quality score",
    }


def install_cv2_compat_stub():
    if "cv2" in sys.modules:
        return

    def cvt_color(img, code):
        if code != 4:
            raise ValueError("The local cv2 compatibility stub only supports COLOR_BGR2RGB.")
        return img[..., ::-1].copy()

    sys.modules["cv2"] = types.SimpleNamespace(COLOR_BGR2RGB=4, cvtColor=cvt_color)


def score_ilniqe(image_path, version="python", resize=True):
    missing_files = [
        file_path
        for file_path in (
            ILNIQE_DIR / "IL-NIQE.py",
            ILNIQE_DIR / "python_templateModel.mat",
            ILNIQE_DIR / "templateModel.mat",
        )
        if not file_path.exists()
    ]
    if missing_files:
        return {
            "status": "skipped",
            "reason": "IL-NIQE files are missing: "
            + ", ".join(str(file_path) for file_path in missing_files),
        }

    install_cv2_compat_stub()
    sys.path.insert(0, str(ILNIQE_DIR))
    ilniqe_module = load_module("local_ilniqe", ILNIQE_DIR / "IL-NIQE.py")

    rgb_image = np.array(Image.open(image_path).convert("RGB"))
    bgr_image = rgb_image[..., ::-1].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        raw_score = ilniqe_module.calculate_ilniqe(
            bgr_image,
            0,
            input_order="HWC",
            resize=resize,
            version=version,
        )

    score = float(np.real(np.asarray(raw_score)).squeeze())
    return {
        "status": "ok",
        "score": score,
        "version": version,
        "resize": resize,
        "interpretation": "lower is better; blind feature-enriched natural-image quality score",
    }


def score_nima(image_path, checkpoint_path):
    if checkpoint_path is None:
        return {
            "status": "skipped",
            "reason": "NIMA checkpoint not provided. Pass --nima-model path/to/model.pth to enable it.",
        }

    nima_model_module = load_module("local_nima_model", NIMA_DIR / "model" / "model.py")
    base_model = models.vgg16(weights=None)
    model = nima_model_module.NIMA(base_model)
    model.classifier[-1] = torch.nn.Softmax(dim=1)

    state = torch.load(checkpoint_path, map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.eval()

    transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        distribution = model(tensor).squeeze(0).cpu().numpy()

    bins = np.arange(1, 11, dtype=np.float32)
    mean = float(np.sum(distribution * bins))
    std = float(np.sqrt(np.sum(distribution * (bins - mean) ** 2)))
    return {
        "status": "ok",
        "mean": mean,
        "std": std,
        "distribution": [float(x) for x in distribution],
        "interpretation": "higher mean is better; learned aesthetic/technical opinion score from 1 to 10",
    }


def patch_torch_cuda_for_cpu():
    if torch.cuda.is_available():
        return

    torch.Tensor.cuda = lambda self, *args, **kwargs: self
    torch.nn.Module.cuda = lambda self, *args, **kwargs: self
    torch.cuda.FloatTensor = torch.FloatTensor


def run_deeplpf(image_path, checkpoint_path, output_dir, reference_path=None):
    if checkpoint_path is None or not checkpoint_path.exists():
        return {
            "status": "skipped",
            "reason": "DeepLPF checkpoint not found.",
        }

    patch_torch_cuda_for_cpu()
    sys.path.insert(0, str(DEEPLPF_DIR))
    deeplpf_model_module = load_module("local_deeplpf_model", DEEPLPF_DIR / "model.py")

    net = deeplpf_model_module.DeepLPFNet()
    state = torch.load(checkpoint_path, map_location="cpu")
    net.load_state_dict(state)
    net.eval()

    image = Image.open(image_path).convert("RGB")
    tensor = tvf.to_tensor(image).unsqueeze(0)
    with torch.no_grad():
        enhanced = torch.clamp(net(tensor), 0.0, 1.0).squeeze(0).cpu()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{image_path.stem}_deeplpf.png"
    tvf.to_pil_image(enhanced).save(output_path)

    result = {
        "status": "ok",
        "output_image": str(output_path),
        "interpretation": "image enhancement model; PSNR/SSIM require a reference image",
    }

    if reference_path is not None:
        reference = np.array(Image.open(reference_path).convert("RGB"), dtype=np.float32) / 255.0
        predicted = np.array(Image.open(output_path).convert("RGB"), dtype=np.float32) / 255.0
        if reference.shape != predicted.shape:
            predicted = np.array(
                Image.fromarray((predicted * 255).astype(np.uint8)).resize(
                    (reference.shape[1], reference.shape[0]),
                    Image.Resampling.BICUBIC,
                ),
                dtype=np.float32,
            ) / 255.0
        result["psnr"] = float(peak_signal_noise_ratio(reference, predicted, data_range=1.0))
        result["ssim"] = float(
            structural_similarity(reference, predicted, data_range=1.0, channel_axis=2)
        )
        result["interpretation"] = "higher PSNR/SSIM means the enhanced output is closer to the reference"

    return result


def write_csv(results, csv_path):
    rows = []
    result_items = results["results"] if "results" in results else [results]
    for item in result_items:
        for mechanism, payload in item["mechanisms"].items():
            row = {
                "image": item["image"],
                "reference": item.get("reference"),
                "mechanism": mechanism,
                "status": payload.get("status", ""),
            }
            for key in (
                "score",
                "mean",
                "std",
                "psnr",
                "ssim",
                "version",
                "resize",
                "reason",
                "output_image",
            ):
                if key in payload:
                    row[key] = payload[key]
            rows.append(row)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "image",
                "reference",
                "mechanism",
                "status",
                "score",
                "mean",
                "std",
                "psnr",
                "ssim",
                "version",
                "resize",
                "reason",
                "output_image",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def find_images(path):
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            file
            for file in path.iterdir()
            if file.is_file() and file.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )
    raise FileNotFoundError(f"Image path does not exist: {path}")


def default_reference_for(image_path):
    if image_path == DEFAULT_IMAGE.resolve():
        return DEFAULT_REFERENCE.resolve()
    return None


def score_image(image_path, args, reference_path):
    return {
        "image": str(image_path),
        "reference": str(reference_path) if reference_path else None,
        "mechanisms": {
            "niqe": score_niqe(image_path),
            "ilniqe": score_ilniqe(
                image_path,
                version=args.ilniqe_version,
                resize=not args.no_ilniqe_resize,
            )
            if args.ilniqe
            else {
                "status": "skipped",
                "reason": "IL-NIQE disabled with --no-ilniqe.",
            },
            "nima": score_nima(image_path, args.nima_model),
            "deeplpf": run_deeplpf(
                image_path,
                args.deeplpf_model.resolve() if args.deeplpf_model else None,
                args.output_dir.resolve(),
                reference_path,
            ),
        },
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the available image scoring/enhancement mechanisms on one shared image."
    )
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE, help="Image file or folder of images.")
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Optional reference/ground-truth image for DeepLPF PSNR and SSIM.",
    )
    parser.add_argument("--nima-model", type=Path, default=None)
    parser.add_argument(
        "--ilniqe",
        dest="ilniqe",
        action="store_true",
        default=True,
        help="Enable IL-NIQE scoring. This is the default.",
    )
    parser.add_argument(
        "--no-ilniqe",
        dest="ilniqe",
        action="store_false",
        help="Skip IL-NIQE scoring for faster runs.",
    )
    parser.add_argument(
        "--ilniqe-version",
        choices=("python", "matlab"),
        default="python",
        help="Template model to use for IL-NIQE.",
    )
    parser.add_argument(
        "--no-ilniqe-resize",
        action="store_true",
        help="Disable IL-NIQE's MATLAB-like resize step.",
    )
    parser.add_argument("--deeplpf-model", type=Path, default=DEFAULT_DEEPLPF_MODEL)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "comparison_outputs")
    parser.add_argument("--json", type=Path, default=ROOT / "comparison_outputs" / "results.json")
    parser.add_argument("--csv", type=Path, default=ROOT / "comparison_outputs" / "results.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    image_paths = find_images(args.image.resolve())
    if args.reference and len(image_paths) > 1:
        raise ValueError("--reference can only be used when --image is a single image file.")

    scored = []
    for image_path in image_paths:
        reference_path = args.reference.resolve() if args.reference else default_reference_for(image_path)
        scored.append(score_image(image_path, args, reference_path))

    results = scored[0] if len(scored) == 1 else {"source": str(args.image.resolve()), "results": scored}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_csv(results, args.csv)

    print(json.dumps(results, indent=2))
    print()
    print(f"Wrote JSON: {args.json}")
    print(f"Wrote CSV:  {args.csv}")
    print(f"Python used here: {PYTHON_EXE_HINT}")


if __name__ == "__main__":
    main()
