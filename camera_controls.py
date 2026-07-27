# camera_controls.py
"""
OpenCV/DirectShow 硬體擷取參數控制（曝光/白平衡…）。只在 CAMERA_BACKEND=opencv 這條
後備路徑會用到；CameraKit 後端有自己一套（見 camerakit_backend.py），白平衡才可靠。

移植自正式系統的 camera_controls.py，只保留這個模組會用到的部分。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict

import cv2

CAPTURE_PROP_MAP: dict[str, int] = {
    "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE,
    "exposure":      cv2.CAP_PROP_EXPOSURE,
    "auto_wb":       cv2.CAP_PROP_AUTO_WB,
    "white_balance": cv2.CAP_PROP_WB_TEMPERATURE,
    "gain":          cv2.CAP_PROP_GAIN,
}

# 手動值要生效，對應的自動旗標要先關。key=手動屬性，value=(自動屬性, 關閉值)
AUTO_GUARDS: dict[str, tuple[str, float]] = {
    "exposure":      ("auto_exposure", 0.25),
    "white_balance": ("auto_wb",       0.0),
}


@dataclass
class CaptureParams:
    auto_exposure: float | None = None
    exposure:      float | None = None
    auto_wb:       float | None = None
    white_balance: float | None = None
    gain:          float | None = None

    @classmethod
    def from_dict(cls, d: dict | None) -> "CaptureParams":
        d = d or {}
        allowed = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in allowed and v is not None})

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def open_camera(index: int = 0) -> cv2.VideoCapture:
    """DirectShow 是 Windows 上控制 UVC 屬性最可靠的 backend。"""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"無法開啟相機 index={index}")
    return cap


def apply_capture_params(cap: cv2.VideoCapture, params: "CaptureParams | dict",
                         settle_s: float = 0.4) -> dict:
    if isinstance(params, dict):
        params = CaptureParams.from_dict(params)

    for manual_key, (auto_key, off_val) in AUTO_GUARDS.items():
        if getattr(params, manual_key) is not None and getattr(params, auto_key) is None:
            cap.set(CAPTURE_PROP_MAP[auto_key], off_val)

    report: dict[str, dict] = {}
    for key in ("auto_exposure", "auto_wb", "exposure", "white_balance", "gain"):
        val = getattr(params, key)
        if val is None:
            continue
        ok = cap.set(CAPTURE_PROP_MAP[key], float(val))
        report[key] = {"requested": float(val), "set_returned": bool(ok)}

    if settle_s > 0:
        time.sleep(settle_s)
    for _ in range(5):
        cap.grab()
    return report
