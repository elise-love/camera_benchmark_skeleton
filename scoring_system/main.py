import argparse
import csv
import importlib.util
import json
import os
import subprocess
import sys
import time
import types
import warnings
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "comparison_outputs"

NIQE_DIR = ROOT / "niqe"
ILNIQE_DIR = ROOT / "il-niqe" / "IL-NIQE"
BRISQUE_PACKAGE_DIR = ROOT / "brisque" / "brisque"
MUSIQ_MODEL_HANDLE = "https://tfhub.dev/google/musiq/koniq-10k/1"
NIMA_ROOT = ROOT / "NIMA" / "image-quality-assessment" / "image-quality-assessment"
NIMA_SRC_ROOT = NIMA_ROOT / "src"
NIMA_WEIGHTS = {
    "technical": NIMA_ROOT / "models" / "MobileNet" / "weights_mobilenet_technical_0.11.hdf5",
    "aesthetic": NIMA_ROOT / "models" / "MobileNet" / "weights_mobilenet_aesthetic_0.07.hdf5",
}

SUPPORTED_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
DEFAULT_METRICS = ("niqe", "ilniqe", "brisque", "musiq", "nima")
TENSORFLOW_PYTHON = Path(
    r"C:\Users\User\anaconda3\envs\pic\python.exe"
)


def quiet_tensorflow():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    warnings.filterwarnings(
        "ignore",
        message=r".*tf\.losses\.sparse_softmax_cross_entropy is deprecated.*",
    )


@contextmanager
def suppress_stderr(enabled=True):
    if not enabled:
        yield
        return

    stderr_fd = sys.stderr.fileno()
    saved_stderr_fd = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(saved_stderr_fd)


def same_executable(left, right):
    try:
        return Path(left).resolve().samefile(Path(right).resolve())
    except OSError:
        return str(Path(left).resolve()).lower() == str(Path(right).resolve()).lower()


def ensure_tensorflow_python(metrics):
    if not {"musiq", "nima"}.intersection(metrics):
        return
    if importlib.util.find_spec("tensorflow") is not None and (
        "musiq" not in metrics or importlib.util.find_spec("tensorflow_hub") is not None
    ):
        return
    if os.environ.get("IQA_NO_PYTHON_REEXEC") == "1":
        return
    if not TENSORFLOW_PYTHON.exists() or same_executable(sys.executable, TENSORFLOW_PYTHON):
        return

    print(f"TensorFlow is not installed in this Python: {sys.executable}", flush=True)
    print(f"Restarting with TensorFlow Python: {TENSORFLOW_PYTHON}", flush=True)
    os.environ["IQA_NO_PYTHON_REEXEC"] = "1"
    command = [str(TENSORFLOW_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]
    raise SystemExit(subprocess.call(command))


def load_module(name, file_path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def scalar(value):
    return float(np.real(np.asarray(value)).reshape(-1)[0])


def find_images(input_path, recursive):
    input_path = Path(input_path)
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image extension: {input_path}")
        return [input_path]

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    return sorted(
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def image_to_gray_array(image_path):
    with Image.open(image_path) as image:
        return np.array(image.convert("LA"))[:, :, 0]


class NIQEScorer:
    name = "niqe"

    def __init__(self):
        sys.path.insert(0, str(NIQE_DIR))
        self.module = load_module("local_niqe", NIQE_DIR / "niqe.py")

    def score(self, image_path):
        return scalar(self.module.niqe(image_to_gray_array(image_path)))


def install_cv2_compat_stub():
    if "cv2" in sys.modules:
        return
    try:
        import cv2  # noqa: F401

        return
    except ImportError:
        pass

    def cvt_color(img, code):
        if code != 4:
            raise ValueError("The cv2 compatibility stub only supports COLOR_BGR2RGB.")
        return img[..., ::-1].copy()

    sys.modules["cv2"] = types.SimpleNamespace(COLOR_BGR2RGB=4, cvtColor=cvt_color)


class ILNIQEScorer:
    name = "ilniqe"

    def __init__(self, version, resize):
        missing = [
            path
            for path in (
                ILNIQE_DIR / "IL-NIQE.py",
                ILNIQE_DIR / "python_templateModel.mat",
                ILNIQE_DIR / "templateModel.mat",
            )
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError("Missing IL-NIQE files: " + ", ".join(map(str, missing)))

        install_cv2_compat_stub()
        sys.path.insert(0, str(ILNIQE_DIR))
        self.module = load_module("local_ilniqe", ILNIQE_DIR / "IL-NIQE.py")
        self.version = version
        self.resize = resize

    def score(self, image_path):
        with Image.open(image_path) as image:
            rgb_image = np.array(image.convert("RGB"))
        bgr_image = rgb_image[..., ::-1].copy()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            value = self.module.calculate_ilniqe(
                bgr_image,
                0,
                input_order="HWC",
                resize=self.resize,
                version=self.version,
            )
        return scalar(value)


class BRISQUEScorer:
    name = "brisque"

    def __init__(self):
        sys.path.insert(0, str(BRISQUE_PACKAGE_DIR))
        from brisque import BRISQUE

        self.scorer = BRISQUE(url=False)

    def score(self, image_path):
        with Image.open(image_path) as image:
            rgb_image = np.asarray(image.convert("RGB"))
        return scalar(self.scorer.score(rgb_image))


class MUSIQScorer:
    name = "musiq"

    def __init__(self, model_handle):
        try:
            quiet_tensorflow()
            with suppress_stderr():
                import tensorflow as tf
                import tensorflow_hub as hub
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "MUSIQ needs TensorFlow and TensorFlow Hub. Install them with: "
                "python -m pip install tensorflow tensorflow-hub"
            ) from exc

        quiet_tensorflow()
        tf.get_logger().setLevel("ERROR")
        self.tf = tf
        with suppress_stderr():
            self.predict_fn = hub.load(model_handle).signatures["serving_default"]

    def score(self, image_path):
        image_bytes = Path(image_path).read_bytes()
        image_tensor = self.tf.constant(image_bytes, dtype=self.tf.string)
        output = self.predict_fn(image_bytes_tensor=image_tensor)
        return scalar(list(output.values())[0].numpy())


class NIMAScorer:
    name = "nima"

    def __init__(self, weights_file):
        if not weights_file.exists():
            raise FileNotFoundError(f"NIMA weights file not found: {weights_file}")

        try:
            quiet_tensorflow()
            with suppress_stderr():
                import tensorflow as tf
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "NIMA needs TensorFlow. Install it with: python -m pip install tensorflow"
            ) from exc

        quiet_tensorflow()
        tf.get_logger().setLevel("ERROR")
        sys.path.insert(0, str(NIMA_SRC_ROOT))
        from handlers.model_builder import Nima
        from utils.utils import calc_mean_score

        self.tf = tf
        self.calc_mean_score = calc_mean_score
        self.model = Nima("MobileNet", weights=None)
        self.model.build()
        self.model.nima_model.load_weights(weights_file)
        self.preprocess = self.model.preprocessing_function()
        self.bins = np.arange(1, 11, dtype=np.float32)

    def score(self, image_path):
        image = self.tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
        array = self.tf.keras.preprocessing.image.img_to_array(image)
        batch = self.preprocess(np.asarray([array], dtype=np.float32))
        distribution = np.asarray(self.model.nima_model.predict(batch, verbose=0)[0], dtype=np.float32)
        distribution = distribution / distribution.sum()
        mean = float(self.calc_mean_score(distribution))
        std = float(np.sqrt(np.sum(distribution * (self.bins - mean) ** 2)))
        return mean, std, [round(float(value), 8) for value in distribution]


def build_scorer(metric, args):
    if metric == "niqe":
        return NIQEScorer()
    if metric == "ilniqe":
        return ILNIQEScorer(args.ilniqe_version, not args.no_ilniqe_resize)
    if metric == "brisque":
        return BRISQUEScorer()
    if metric == "musiq":
        return MUSIQScorer(args.musiq_model)
    if metric == "nima":
        weights_file = args.nima_weights or NIMA_WEIGHTS[args.nima_type]
        return NIMAScorer(weights_file.resolve())
    raise ValueError(f"Unknown metric: {metric}")


def empty_row(image_path, input_root, metrics):
    rel_path = image_path.name
    if input_root.is_dir():
        try:
            rel_path = str(image_path.relative_to(input_root))
        except ValueError:
            rel_path = image_path.name

    row = {
        "image": rel_path,
        "path": str(image_path.resolve()),
        "seconds_total": "",
    }
    for metric in metrics:
        row[f"{metric}_score"] = ""
        row[f"{metric}_seconds"] = ""
        row[f"{metric}_error"] = ""
    row["nima_std"] = ""
    row["nima_distribution"] = ""
    return row


def score_images(image_paths, input_root, metrics, args):
    rows = [empty_row(path, input_root, metrics) for path in image_paths]

    for metric in metrics:
        print(f"\nLoading {metric.upper()}...", flush=True)
        try:
            scorer = build_scorer(metric, args)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            print(f"  Cannot load {metric.upper()}: {message}", flush=True)
            for row in rows:
                row[f"{metric}_error"] = message
            continue

        for index, (image_path, row) in enumerate(zip(image_paths, rows), start=1):
            start = time.perf_counter()
            try:
                if metric == "nima":
                    mean, std, distribution = scorer.score(image_path)
                    row["nima_score"] = round(mean, 6)
                    row["nima_std"] = round(std, 6)
                    row["nima_distribution"] = json.dumps(distribution)
                else:
                    row[f"{metric}_score"] = round(float(scorer.score(image_path)), 6)
                row[f"{metric}_seconds"] = round(time.perf_counter() - start, 3)
                print(
                    f"  [{index}/{len(image_paths)}] {image_path.name}: "
                    f"{row[f'{metric}_score']}",
                    flush=True,
                )
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                row[f"{metric}_error"] = message

                print(
                    f"  [{index}/{len(image_paths)}] "
                    f"{image_path.name}: ERROR - {message}",
                    flush=True,
                )
    return rows


def write_csv(rows, csv_path, metrics):
    fieldnames = ["image", "path"]
    for metric in metrics:
        fieldnames.extend([f"{metric}_score", f"{metric}_seconds", f"{metric}_error"])
        if metric == "nima":
            fieldnames.extend(["nima_std", "nima_distribution"])
    fieldnames.append("seconds_total")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_metrics(value):
    if value.lower() == "all":
        return list(DEFAULT_METRICS)
    metrics = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = sorted(set(metrics) - set(DEFAULT_METRICS))
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown metrics: {', '.join(unknown)}")
    return metrics


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run NIQE, IL-NIQE, BRISQUE, MUSIQ, and NIMA on images in the data folder."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DATA_DIR,
        help=f"Image file or folder to score. Default: {DATA_DIR}",
    )
    parser.add_argument(
        "--metrics",
        type=parse_metrics,
        default=list(DEFAULT_METRICS),
        help="Comma-separated metrics to run, or 'all'. Default: all",
    )
    parser.add_argument("--no-recursive", action="store_true", help="Only scan the top-level input folder.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--ilniqe-version", choices=("python", "matlab"), default="python")
    parser.add_argument("--no-ilniqe-resize", action="store_true")
    parser.add_argument("--musiq-model", default=MUSIQ_MODEL_HANDLE)
    parser.add_argument("--nima-type", choices=("technical", "aesthetic"), default="technical")
    parser.add_argument("--nima-weights", type=Path, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_tensorflow_python(args.metrics)
    input_root = args.input.resolve()
    metrics = args.metrics
    csv_path = args.csv or args.output_dir / "all_iqa_scores.csv"
    json_path = args.json or args.output_dir / "all_iqa_scores.json"

    image_paths = find_images(input_root, recursive=not args.no_recursive)
    if not image_paths:
        raise SystemExit(f"No supported images found in: {input_root}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_root}")
    print(f"Images: {len(image_paths)}")
    print(f"Metrics: {', '.join(metrics)}")

    total_start = time.perf_counter()
    rows = score_images(image_paths, input_root, metrics, args)
    for row in rows:
        row["seconds_total"] = round(time.perf_counter() - total_start, 3)

    write_csv(rows, csv_path, metrics)
    json_path.write_text(
        json.dumps(
            {
                "input": str(input_root),
                "metrics": metrics,
                "count": len(rows),
                "results": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nWrote CSV:  {csv_path.resolve()}")
    print(f"Wrote JSON: {json_path.resolve()}")


if __name__ == "__main__":
    main()
