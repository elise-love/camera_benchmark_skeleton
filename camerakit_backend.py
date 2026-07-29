# camerakit_backend.py
"""
IPEVO CameraKit 相機封裝（曝光 1–15 / 白平衡 2200–7500K 皆可調，OpenCV 對這台相機做不到白平衡）。

移植自正式系統 take_pic_benchmark_tainan/camerakit_backend.py，邏輯不變。
DLL 資產（IPEVOCameraKit/）已經複製一份放在本模組底下（config.IPEVO_CAMERAKIT_DIR），
不依賴正式系統。

前置：pip install pythonnet；Windows 需要 .NET Framework。
"""

from __future__ import annotations

import os
import glob
import struct
import ctypes
import threading
import time

import numpy as np

import config

_HERE = os.path.dirname(os.path.abspath(__file__))
_ARCH = "x64" if struct.calcsize("P") * 8 == 64 else "x86"

_CK = None  # 快取載入的命名空間，避免重複 AddReference


def _find_camerakit_dll() -> str:
    search_roots = [_HERE, config.IPEVO_CAMERAKIT_DIR]
    for root in search_roots:
        hits = glob.glob(os.path.join(root, "**", "AssetsLibrary", _ARCH, "CameraKit.dll"),
                         recursive=True)
        if hits:
            return hits[0]
    raise FileNotFoundError(
        f"找不到 {_ARCH} 版 CameraKit.dll。找過：{search_roots}。"
        f"請確認 {config.IPEVO_CAMERAKIT_DIR} 底下有完整的 IPEVOCameraKit 資料夾。")


def _load_camerakit():
    global _CK
    if _CK is not None:
        return _CK

    dll_path = _find_camerakit_dll()
    assets = os.path.dirname(dll_path)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(assets)
    os.environ["PATH"] = assets + os.pathsep + os.environ.get("PATH", "")

    try:
        from pythonnet import load
        load("netfx")
    except Exception:
        pass
    import clr
    clr.AddReference(dll_path)
    from com.ipevo.windows.CameraKit import (ICCamerasManager, ICCamera,  # type: ignore
                                             ICCameraStreamProxy)
    _CK = (ICCamerasManager, ICCamera, ICCameraStreamProxy)
    return _CK


class CameraKitCamera:
    """介面對齊 cv2.VideoCapture 的 read()/release()，方便跟 opencv 後端互換。"""

    def __init__(self, index: int = 0, prefer=(1920, 1080), warmup_s: float = 2.5):
        self._Mgr, self._ICCamera, self._Proxy = _load_camerakit()
        mgr = self._Mgr.sharedManager
        mgr.startMonitor()
        time.sleep(2.0)
        cams = list(mgr.cameras)
        if not cams:
            raise RuntimeError("CameraKit 沒偵測到相機（沒插、被佔用、或型號不支援）")
        if index >= len(cams):
            raise IndexError(f"相機 index {index} 超出範圍（共 {len(cams)} 台）")
        self._cam = cams[index]
        self.name = self._cam.CameraInstanceName

        FK = self._ICCamera.FormatKey
        fmts = list(self._cam.supportedFormats())
        chosen = fmts[0]
        for f in fmts:
            try:
                if int(f[FK.Width]) == prefer[0] and int(f[FK.Height]) == prefer[1]:
                    chosen = f
                    break
            except Exception:
                pass
        self.width = int(chosen[FK.Width])
        self.height = int(chosen[FK.Height])

        self._lock = threading.Lock()
        self._latest = None
        self._proxy = self._Proxy.sharedProxy
        self._observer = self._Proxy.StreamObserver(self._on_frame)
        self._proxy.addStreamObserver(self._cam, self._observer)
        self._cam.setFormat(chosen)
        self._proxy.startStreamObserver(self._cam)

        t0 = time.time()
        while time.time() - t0 < warmup_s:
            with self._lock:
                if self._latest is not None:
                    break
            time.sleep(0.05)

    def _on_frame(self, camera, buffer, bufferLength, frameWidth=0, frameHeight=0):
        try:
            addr = buffer.ToInt64() if hasattr(buffer, "ToInt64") else int(buffer)
            if addr == 0 or bufferLength <= 0:
                return
            raw = (ctypes.c_ubyte * bufferLength).from_address(addr)
            arr = np.frombuffer(raw, dtype=np.uint8).copy()
            if arr.size == self.width * self.height * 4:
                # CameraKit streams BGR32 rows in bottom-up bitmap order.
                # Normalize it here so preview, raw capture, and processed output share the same orientation.
                bgr = arr.reshape((self.height, self.width, 4))[::-1, :, :3].copy()
                with self._lock:
                    self._latest = bgr
        except Exception:
            pass

    def isOpened(self) -> bool:  # noqa: N802
        return self._cam is not None

    def read(self):
        with self._lock:
            if self._latest is None:
                return False, None
            return True, self._latest.copy()

    def set_capture(self, params: dict, settle_s: float = 0.6):
        """params 可含 exposure(1-15) / auto_exposure(bool) / white_balance(2200-7500) / auto_wb(bool)。"""
        params = config.clip_capture_params(params, config.CAMERAKIT_CAMERA_AXES)
        cam = self._cam
        if params.get("auto_exposure") is not None:
            cam.setAutoExposure(bool(params["auto_exposure"]))
        if params.get("auto_wb") is not None:
            cam.setAutoWhiteBalance(bool(params["auto_wb"]))
        if params.get("exposure") is not None:
            cam.setAutoExposure(False)
            cam.setExposure(int(round(params["exposure"])))
        if params.get("white_balance") is not None:
            cam.setAutoWhiteBalance(False)
            cam.setWhiteBalance(int(round(params["white_balance"])))
        if settle_s > 0:
            time.sleep(settle_s)

    def release(self):
        try:
            self._proxy.stopStreamObserver(self._cam)
            self._proxy.removeStreamObserver(self._cam, self._observer)
        except Exception:
            pass
        self._cam = None
