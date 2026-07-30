# camera_backend.py
"""
可插拔相機後端（移植自正式系統 benchmark_opt/camera_backends.py）。

CameraKit 與 OpenCV 兩個後端二擇一：CameraKit 白平衡可調但需獨佔相機串流；
OpenCV 白平衡不可調但任何機器都能拿來測流程。auto 模式優先 CameraKit，失敗退回 OpenCV。
"""

from __future__ import annotations

import config


class OpenCVBackend:
    kind = "opencv"

    def __init__(self, index: int = 0):
        import camera_controls as cc
        self._cc = cc
        self.cap = cc.open_camera(index)

    def camera_axes(self):
        return dict(config.OPENCV_CAMERA_AXES)   # 無白平衡搜尋軸

    def reference_capture(self):
        return dict(config.DEFAULT_CAPTURE_RESETS["opencv"])

    def set_capture(self, d: dict, settle_s: float = 0.5):
        safe = config.clip_capture_params(d, self.camera_axes())
        self._cc.apply_capture_params(self.cap, safe, settle_s=settle_s)

    def reset_capture(self, settle_s: float = 1.0):
        self.set_capture(self.reference_capture(), settle_s=settle_s)

    def restore_capture(self, settle_s: float = 1.0):
        self.reset_capture(settle_s=settle_s)

    def read(self):
        return self.cap.read()

    def release(self):
        try:
            self.reset_capture(settle_s=0.2)
            self.cap.release()
        except Exception:
            pass


class CameraKitBackend:
    kind = "camerakit"

    def __init__(self, index: int = 0):
        from camerakit_backend import CameraKitCamera
        self.cam = CameraKitCamera(index)

    def camera_axes(self):
        return dict(config.CAMERAKIT_CAMERA_AXES)

    def reference_capture(self):
        return dict(config.DEFAULT_CAPTURE_RESETS["camerakit"])

    def set_capture(self, d: dict, settle_s: float = 0.6):
        safe = config.clip_capture_params(d, self.camera_axes())
        self.cam.set_capture(safe, settle_s=settle_s)

    def reset_capture(self, settle_s: float = 1.2):
        self.set_capture(self.reference_capture(), settle_s=settle_s)

    def restore_capture(self, settle_s: float = 1.2):
        self.reset_capture(settle_s=settle_s)

    def read(self):
        return self.cam.read()

    def release(self):
        try:
            self.reset_capture(settle_s=0.2)
            self.cam.release()
        except Exception:
            pass


class MockBackend:
    """不需要真相機：讀不到相機時，用純色漸層假畫面把整條流程走一遍。"""
    kind = "mock"

    def __init__(self, index: int = 0):
        import numpy as np
        self._np = np
        self._t = 0

    def camera_axes(self):
        return dict(config.OPENCV_CAMERA_AXES)

    def reference_capture(self):
        return dict(config.DEFAULT_CAPTURE_RESETS["mock"])

    def set_capture(self, d: dict, settle_s: float = 0.0):
        pass

    def reset_capture(self, settle_s: float = 0.0):
        pass

    def restore_capture(self, settle_s: float = 0.0):
        pass

    def read(self):
        np = self._np
        self._t += 1
        h, w = 720, 1280
        shade = int(128 + 100 * np.sin(self._t / 20.0))
        frame = np.full((h, w, 3), shade, dtype=np.uint8)
        return True, frame

    def release(self):
        pass


def open_backend(name: str | None = None, index: int | None = None):
    name = name or config.CAMERA_BACKEND
    index = config.CAMERA_INDEX if index is None else index

    if name == "mock":
        return MockBackend()
    if name == "opencv":
        return OpenCVBackend(index)
    if name == "camerakit":
        return CameraKitBackend(index)
    # auto
    try:
        b = CameraKitBackend(index)
        print("[backend] 使用 CameraKit（白平衡可調）")
        return b
    except Exception as e:
        print(f"[backend] CameraKit 不可用（{type(e).__name__}: {e}）→ 退回 OpenCV（無白平衡）")
        return OpenCVBackend(index)
