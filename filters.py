# filters.py
"""
後製濾鏡（移植自正式系統 camera_filters.py，拿掉沒用到的 guided_filter 以精簡依賴）。
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class FilterParams:
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue_shift: float = 0.0
    gamma: float = 1.0
    temperature: float = 0.0
    enum: str = "none"


def _apply_gamma(bgr: np.ndarray, gamma: float) -> np.ndarray:
    if gamma <= 0 or abs(gamma - 1.0) < 1e-6:
        return bgr
    inv = 1.0 / gamma
    table = (np.linspace(0, 1, 256) ** inv * 255).astype(np.uint8)
    return cv2.LUT(bgr, table)


def apply_filters_rgba(rgba: np.ndarray, p: FilterParams) -> np.ndarray:
    """rgba: HxWx4 uint8 → 回傳同尺寸 HxWx4 uint8。"""
    if rgba is None:
        return rgba
    if rgba.dtype != np.uint8:
        rgba = rgba.astype(np.uint8, copy=False)
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("apply_filters_rgba expects RGBA uint8 image (HxWx4).")

    rgb = rgba[:, :, :3]
    a = rgba[:, :, 3:4]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    bgr = cv2.convertScaleAbs(bgr, alpha=float(p.contrast), beta=float(p.brightness))
    bgr = _apply_gamma(bgr, float(p.gamma))

    if abs(p.saturation - 1.0) > 1e-6 or abs(p.hue_shift) > 1e-6:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 0] = (hsv[:, :, 0] + (p.hue_shift * 0.5)) % 180.0
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * p.saturation, 0, 255)
        bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    if abs(p.temperature) > 1e-6:
        t = float(p.temperature)
        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)
        r = np.clip(r + t * 1.2, 0, 255)
        b = np.clip(b - t * 1.2, 0, 255)
        bgr = np.stack([b, g, r], axis=2).astype(np.uint8)

    enum = (p.enum or "none").lower()
    if enum == "bw":
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    rgb2 = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.concatenate([rgb2, a], axis=2)
