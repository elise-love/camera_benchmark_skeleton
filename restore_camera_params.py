from __future__ import annotations

import argparse
import sys
import time

import config
from camera_backend import open_backend


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset camera capture parameters to the backend's default mode."
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "camerakit", "opencv", "mock"),
        default=config.CAMERA_BACKEND,
        help="Camera backend to open. Defaults to config.CAMERA_BACKEND.",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=config.CAMERA_INDEX,
        help="Camera index to restore. Defaults to config.CAMERA_INDEX.",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=1.5,
        help="Seconds to wait after resetting camera controls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend = open_backend(args.backend, index=args.index)
    try:
        reset_params = backend.reference_capture()
        backend.reset_capture(settle_s=args.settle)
        time.sleep(0.2)
        print(f"Reset {backend.kind} camera capture params to default: {reset_params}")
        return 0
    finally:
        backend.release()


if __name__ == "__main__":
    sys.exit(main())
