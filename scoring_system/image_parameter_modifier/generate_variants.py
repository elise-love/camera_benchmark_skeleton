from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageEnhance


PARAMETER_RANGES = {
    "brightness": (-30.0, 30.0),
    "contrast": (0.80, 1.30),
    "saturation": (0.75, 1.35),
    "hue_shift": (-8.0, 8.0),
    "gamma": (0.80, 1.35),
    "temperature": (-15.0, 15.0),
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
HALTON_BASES = (2, 3, 5, 7, 11, 13)


@dataclass(frozen=True)
class VariantParameters:
    brightness: float
    contrast: float
    saturation: float
    hue_shift: float
    gamma: float
    temperature: float

    def as_row(self, image_name: str, output_name: str) -> dict[str, str]:
        return {
            "source_image": image_name,
            "output_image": output_name,
            "brightness": f"{self.brightness:.4f}",
            "contrast": f"{self.contrast:.4f}",
            "saturation": f"{self.saturation:.4f}",
            "hue_shift": f"{self.hue_shift:.4f}",
            "gamma": f"{self.gamma:.4f}",
            "temperature": f"{self.temperature:.4f}",
        }


def halton_value(index: int, base: int) -> float:
    result = 0.0
    fraction = 1.0 / base
    while index > 0:
        result += fraction * (index % base)
        index //= base
        fraction /= base
    return result

#算出組和數
def build_parameter_sets(count: int) -> list[VariantParameters]:
    if count < 1:
        raise ValueError("count must be at least 1")

    names = list(PARAMETER_RANGES)
    variants: list[VariantParameters] = []

    for variant_index in range(1, count + 1):
        values = {}
        for name, base in zip(names, HALTON_BASES):
            low, high = PARAMETER_RANGES[name]
            unit_value = halton_value(variant_index, base)
            values[name] = low + unit_value * (high - low)
        variants.append(VariantParameters(**values))

    return variants


def clip_rgb(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb, 0, 255).astype(np.uint8)


def split_alpha(image: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    has_alpha = "A" in image.getbands()
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    alpha = rgba.getchannel("A") if has_alpha else None
    return rgb, alpha


def restore_alpha(rgb: Image.Image, alpha: Image.Image | None) -> Image.Image:
    if alpha is None:
        return rgb
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def adjust_hue(rgb: Image.Image, hue_shift: float) -> Image.Image:
    hsv = rgb.convert("HSV")
    h, s, v = hsv.split()
    hue_delta = int(round((hue_shift / 360.0) * 255.0))

    h_array = np.asarray(h, dtype=np.int32)
    shifted_h = ((h_array + hue_delta) % 256).astype(np.uint8)
    shifted = Image.merge("HSV", (Image.fromarray(shifted_h, mode="L"), s, v))
    return shifted.convert("RGB")


def adjust_gamma(rgb: Image.Image, gamma: float) -> Image.Image:
    if gamma <= 0:
        raise ValueError("gamma must be positive")

    array = np.asarray(rgb, dtype=np.float32) / 255.0
    corrected = np.power(array, 1.0 / gamma) * 255.0
    return Image.fromarray(clip_rgb(corrected), mode="RGB")


def adjust_temperature(rgb: Image.Image, temperature: float) -> Image.Image:
    array = np.asarray(rgb, dtype=np.float32)
    array[..., 0] += temperature
    array[..., 1] += temperature * 0.15
    array[..., 2] -= temperature
    return Image.fromarray(clip_rgb(array), mode="RGB")


def apply_parameters(image: Image.Image, parameters: VariantParameters) -> Image.Image:
    rgb, alpha = split_alpha(image)

    rgb = ImageEnhance.Contrast(rgb).enhance(parameters.contrast)
    rgb = ImageEnhance.Color(rgb).enhance(parameters.saturation)
    rgb = adjust_hue(rgb, parameters.hue_shift)
    rgb = adjust_gamma(rgb, parameters.gamma)

    array = np.asarray(rgb, dtype=np.float32)
    array += parameters.brightness
    rgb = Image.fromarray(clip_rgb(array), mode="RGB")
    rgb = adjust_temperature(rgb, parameters.temperature)

    return restore_alpha(rgb, alpha)


def iter_images(input_dir: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def make_output_name(source: Path, variant_index: int) -> str:
    return f"{source.stem}_variant_{variant_index:03d}{source.suffix.lower()}"


def save_variant(image: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_image = image
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        save_image = image.convert("RGB")
        save_image.save(output_path, quality=95, subsampling=0)
        return
    save_image.save(output_path)


def generate_variants(input_dir: Path, output_dir: Path, count: int) -> int:
    image_paths = list(iter_images(input_dir))
    if not image_paths:
        raise FileNotFoundError(f"No image files found in {input_dir}")

    parameter_sets = build_parameter_sets(count)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "variant_parameters.csv"
    fieldnames = [
        "source_image",
        "output_image",
        "brightness",
        "contrast",
        "saturation",
        "hue_shift",
        "gamma",
        "temperature",
    ]

    total_written = 0
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for source_path in image_paths:
            with Image.open(source_path) as source_image:
                for index, parameters in enumerate(parameter_sets, start=1):
                    output_name = make_output_name(source_path, index)
                    output_path = output_dir / output_name
                    variant = apply_parameters(source_image, parameters)
                    save_variant(variant, output_path)
                    writer.writerow(parameters.as_row(source_path.name, output_name))
                    total_written += 1

    return total_written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate image variants by spreading parameter combinations across fixed ranges."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=Path(__file__).with_name("image"),
        help="Folder containing source images. Defaults to ./image beside this script.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("output"),
        help="Folder to write generated variants. Defaults to ./output beside this script.",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=40,
        help="Number of variants to generate per source image. Defaults to 40.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_written = generate_variants(args.input_dir, args.output_dir, args.count)
    print(f"Generated {total_written} image(s) in {args.output_dir}")


if __name__ == "__main__":
    main()
