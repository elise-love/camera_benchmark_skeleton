import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
LOCAL_PACKAGE_DIR = ROOT / "brisque"
DEFAULT_DATA_DIR = ROOT / "data"

# Prefer the BRISQUE source included in this folder over a globally installed copy.
sys.path.insert(0, str(LOCAL_PACKAGE_DIR))

from brisque import BRISQUE  # noqa: E402


def find_pngs(path):
    path = Path(path)
    if path.is_file():
        if path.suffix.lower() != ".png":
            raise ValueError(f"Not a PNG file: {path}")
        return [path]
    return sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".png")


def score_image(scorer, image_path):
    start = time.perf_counter()
    with Image.open(image_path) as image:
        rgb_image = np.asarray(image.convert("RGB"))
        raw_score = scorer.score(rgb_image)
        score = float(np.asarray(raw_score).reshape(-1)[0])

    return {
        "image": image_path.name,
        "score": score,
        "seconds": round(time.perf_counter() - start, 3),
        "path": str(image_path.resolve()),
        "error": "",
    }


def write_csv(results, output_path):
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["image", "score", "seconds", "path", "error"])
        writer.writeheader()
        writer.writerows(results)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Score PNG images with BRISQUE. Lower scores indicate better image quality."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"PNG file or folder to score (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument("--csv", type=Path, help="CSV output path")
    parser.add_argument("--json", type=Path, help="JSON output path")
    return parser.parse_args()


def main():
    args = parse_args()
    images = find_pngs(args.input)
    if not images:
        raise SystemExit(f"No PNG images found in: {args.input}")

    output_dir = args.input.parent if args.input.is_file() else args.input
    csv_path = args.csv or output_dir / "brisque_scores.csv"
    json_path = args.json or output_dir / "brisque_scores.json"

    scorer = BRISQUE(url=False)
    results = []
    for index, image_path in enumerate(images, start=1):
        try:
            result = score_image(scorer, image_path)
            print(
                f"[{index}/{len(images)}] {result['image']}: "
                f"{result['score']:.6f} ({result['seconds']:.3f}s)",
                flush=True,
            )
        except Exception as exc:
            result = {
                "image": image_path.name,
                "score": "",
                "seconds": "",
                "path": str(image_path.resolve()),
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"[{index}/{len(images)}] {image_path.name}: ERROR - {result['error']}", flush=True)
        results.append(result)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(results, csv_path)
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    success_count = sum(not result["error"] for result in results)
    print(f"\nScored {success_count}/{len(results)} PNG images.")
    print(f"CSV:  {csv_path.resolve()}")
    print(f"JSON: {json_path.resolve()}")

    if success_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
