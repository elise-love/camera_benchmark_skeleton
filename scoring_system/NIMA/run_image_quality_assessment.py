import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf


ROOT = Path(__file__).resolve().parent
IQA_ROOT = ROOT / "image-quality-assessment" / "image-quality-assessment"
SRC_ROOT = IQA_ROOT / "src"
DEFAULT_IMAGE_DIR = ROOT / "data_image"
DEFAULT_WEIGHTS = (
    IQA_ROOT
    / "models"
    / "MobileNet"
    / "weights_mobilenet_technical_0.11.hdf5"
)

sys.path.insert(0, str(SRC_ROOT))

from handlers.model_builder import Nima  # noqa: E402
from utils.utils import calc_mean_score  # noqa: E402


SUPPORTED_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".webp"}


def find_images(image_dir):
    return sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_batch(image_paths, preprocess):
    images = []
    for image_path in image_paths:
        image = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
        images.append(tf.keras.preprocessing.image.img_to_array(image))
    return preprocess(np.asarray(images, dtype=np.float32))


def score_folder(image_dir, weights_file, output_csv, output_json, batch_size):
    image_paths = find_images(image_dir)
    if not image_paths:
        raise ValueError(f"No images found in {image_dir}")

    nima = Nima("MobileNet", weights=None)
    nima.build()
    nima.nima_model.load_weights(weights_file)
    preprocess = nima.preprocessing_function()

    rows = []
    bins = np.arange(1, 11, dtype=np.float32)
    for start in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[start : start + batch_size]
        batch = load_batch(batch_paths, preprocess)
        predictions = nima.nima_model.predict(batch, verbose=0)
        for image_path, distribution in zip(batch_paths, predictions):
            distribution = np.asarray(distribution, dtype=np.float32)
            distribution = distribution / distribution.sum()
            mean_score = float(calc_mean_score(distribution))
            std = float(np.sqrt(np.sum(distribution * (bins - mean_score) ** 2)))
            rows.append(
                {
                    "filename": image_path.name,
                    "mean_score": round(mean_score, 6),
                    "std": round(std, 6),
                    "distribution": [round(float(value), 8) for value in distribution],
                }
            )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["filename", "mean_score", "std"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "filename": row["filename"],
                    "mean_score": row["mean_score"],
                    "std": row["std"],
                }
            )

    output_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--weights-file", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_IMAGE_DIR / "nima_iqa_technical_scores.csv",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_IMAGE_DIR / "nima_iqa_technical_scores.json",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main():
    args = parse_args()
    rows = score_folder(
        args.image_dir.resolve(),
        args.weights_file.resolve(),
        args.output_csv.resolve(),
        args.output_json.resolve(),
        args.batch_size,
    )
    for rank, row in enumerate(
        sorted(rows, key=lambda item: item["mean_score"], reverse=True), start=1
    ):
        print(f"{rank:02d} {row['filename']} mean={row['mean_score']:.4f} std={row['std']:.4f}")
    print(f"Wrote CSV: {args.output_csv.resolve()}")
    print(f"Wrote JSON: {args.output_json.resolve()}")


if __name__ == "__main__":
    main()
