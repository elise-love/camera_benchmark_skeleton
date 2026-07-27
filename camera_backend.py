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
        return {"capture.exposure": ("float", -11.0, -3.0)}   # 無白平衡軸

    def reference_capture(self):
        return {"auto_exposure": 0.75, "auto_wb": 1}

    def set_capture(self, d: dict, settle_s: float = 0.5):
        self._cc.apply_capture_params(self.cap, d, settle_s=settle_s)

    def read(self):
        return self.cap.read()

    def release(self):
        try:
            self.cap.release()
        except Exception:
            pass


class CameraKitBackend:
    kind = "camerakit"

    def __init__(self, index: int = 0):
        from camerakit_backend import CameraKitCamera
        self.cam = CameraKitCamera(index)

    def camera_axes(self):
        return {"capture.exposure":      ("int", 1, 15),
                "capture.white_balance": ("float", 2200.0, 7500.0)}

    def reference_capture(self):
        return {"auto_exposure": True, "auto_wb": True}

    def set_capture(self, d: dict, settle_s: float = 0.6):
        self.cam.set_capture(d, settle_s=settle_s)

    def read(self):
        return self.cam.read()

    def release(self):
        try:
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
        return {"capture.exposure": ("float", -11.0, -3.0)}

    def reference_capture(self):
        return {"auto_exposure": 0.75, "auto_wb": 1}

    def set_capture(self, d: dict, settle_s: float = 0.0):
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
