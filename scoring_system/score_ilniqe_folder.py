import argparse
import csv
import importlib.util
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
DEFAULT_ILNIQE_DIR = ROOT / "il-niqe" / "IL-NIQE"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def load_ilniqe_module(ilniqe_dir):
    sys.path.insert(0, str(ilniqe_dir))
    spec = importlib.util.spec_from_file_location("local_ilniqe", ilniqe_dir / "IL-NIQE.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score_one(image_path, ilniqe_dir, version, resize):
    image_path = Path(image_path)
    ilniqe_dir = Path(ilniqe_dir)
    ilniqe_module = load_ilniqe_module(ilniqe_dir)

    rgb_image = np.array(Image.open(image_path).convert("RGB"))
    bgr_image = rgb_image[..., ::-1].copy()

    start = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        raw_score = ilniqe_module.calculate_ilniqe(
            bgr_image,
            0,
            input_order="HWC",
            resize=resize,
            version=version,
        )

    return {
        "image": image_path.name,
        "path": str(image_path),
        "score": float(np.real(np.asarray(raw_score)).squeeze()),
        "version": version,
        "resize": resize,
        "seconds": round(time.perf_counter() - start, 3),
    }


def find_images(path):
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def write_csv(rows, csv_path):
    with Path(csv_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image", "score", "version", "resize", "seconds", "path"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Batch-score images with the local IL-NIQE implementation.")
    parser.add_argument("image_path", type=Path, help="Image file or folder to score.")
    parser.add_argument("--ilniqe-dir", type=Path, default=DEFAULT_ILNIQE_DIR)
    parser.add_argument("--version", choices=("python", "matlab"), default="python")
    parser.add_argument("--no-resize", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    images = find_images(args.image_path)
    if not images:
        raise SystemExit(f"No supported images found in {args.image_path}")

    csv_path = args.csv or Path(args.image_path) / "ilniqe_scores.csv"
    json_path = args.json or Path(args.image_path) / "ilniqe_scores.json"
    workers = max(1, min(args.workers, len(images)))

    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                score_one,
                image,
                args.ilniqe_dir,
                args.version,
                not args.no_resize,
            ): image
            for image in images
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['image']}: {result['score']:.6f} ({result['seconds']:.1f}s)", flush=True)

    results.sort(key=lambda item: item["image"])
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(results, csv_path)
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote JSON: {json_path}")


if __name__ == "__main__":
    main()
