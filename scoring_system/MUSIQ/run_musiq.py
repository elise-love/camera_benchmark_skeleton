"""
MUSIQ image quality scoring script.
Uses Google's MUSIQ model from TF Hub (KonIQ-10k weights, score range 0-100).
"""

import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import json
import glob
import sys
import warnings
from contextlib import contextmanager

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


with suppress_stderr():
    import tensorflow as tf
    import tensorflow_hub as hub

tf.get_logger().setLevel("ERROR")

MODEL_HANDLE = "https://tfhub.dev/google/musiq/koniq-10k/1"

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "data_image")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "musiq_scores.json")


def main():
    print(f"Loading MUSIQ model from TF Hub: {MODEL_HANDLE}")
    with suppress_stderr():
        model = hub.load(MODEL_HANDLE)
    predict_fn = model.signatures["serving_default"]

    png_files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.png")))
    print(f"Found {len(png_files)} images.\n")

    results = []
    for path in png_files:
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            image_bytes = f.read()
        image_tensor = tf.constant(image_bytes, dtype=tf.string)
        output = predict_fn(image_bytes_tensor=image_tensor)
        score = float(list(output.values())[0].numpy().squeeze())
        results.append({"file": filename, "musiq_score": round(score, 4)})
        print(f"  {filename:60s}  score: {score:.2f}")

    results.sort(key=lambda x: x["musiq_score"], reverse=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {OUTPUT_JSON}")
    print("\n--- Ranking (highest to lowest) ---")
    for rank, r in enumerate(results, 1):
        print(f"  #{rank:2d}  {r['file']:60s}  {r['musiq_score']:.2f}")


if __name__ == "__main__":
    main()
