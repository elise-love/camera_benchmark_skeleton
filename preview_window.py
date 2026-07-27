# preview_window.py
"""
拍照畫面：純 OpenCV 視窗（cv2.imshow），不用任何 GUI 套件。
  - FrameHub：唯一一個持續呼叫 backend.read() 的地方，其他人只讀「最新一張」的快照，
    避免多個執行緒同時對同一台相機呼叫 read()。
  - PreviewWindow：背景執行緒，負責把 FrameHub 的最新畫面套上目前濾鏡、畫上倒數/狀態文字、
    imshow 出來。只有這個執行緒會呼叫 cv2 的視窗函式。

倒數數字、狀態文字都是「main.py 設定共享狀態、這裡負責畫出來」，main.py 不用等這裡畫完。
"""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from filters import apply_filters_rgba, FilterParams

WINDOW_TITLE = "拍照預覽（ESC 結束）"


class FrameHub:
    """唯一的相機讀取執行緒，其他人只從這裡拿最新一張畫面的複本。"""

    def __init__(self, backend):
        self.backend = backend
        self._lock = threading.Lock()
        self._latest_bgr: np.ndarray | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok, bgr = self.backend.read()
            if ok and bgr is not None:
                with self._lock:
                    self._latest_bgr = bgr
            else:
                time.sleep(0.01)

    def get_latest_bgr(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest_bgr is None else self._latest_bgr.copy()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)


class PreviewWindow:
    def __init__(self, hub: FrameHub):
        self.hub = hub
        self._lock = threading.Lock()
        self._filter_params = FilterParams()
        self._countdown: int | None = None
        # cv2.putText 只能畫 ASCII（Hershey 向量字型不支援中文），所以疊在畫面上的
        # caption 一律用英文；中文狀態訊息交給 status_display 印在 terminal 上。
        self._caption = "Initializing..."
        self._stop = threading.Event()
        self._quit_requested = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def set_filter_params(self, params: FilterParams) -> None:
        with self._lock:
            self._filter_params = params

    def set_countdown(self, n: int | None) -> None:
        with self._lock:
            self._countdown = n

    def set_caption(self, text: str) -> None:
        with self._lock:
            self._caption = text

    def is_quit_requested(self) -> bool:
        return self._quit_requested.is_set()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        cv2.destroyAllWindows()

    def _draw_overlay(self, bgr: np.ndarray, countdown, caption: str) -> np.ndarray:
        h, w = bgr.shape[:2]

        # 底部狀態列（跟 terminal 同步顯示，方便對照畫面跟文字）
        cv2.rectangle(bgr, (0, h - 50), (w, h), (0, 0, 0), -1)
        cv2.putText(bgr, caption, (16, h - 16), cv2.FONT_HERSHEY_SIMPLEX,
                   0.9, (255, 255, 255), 2, cv2.LINE_AA)

        if countdown is not None:
            text = str(countdown)
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 8.0
            thickness = 14
            (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
            x = (w - tw) // 2
            y = (h + th) // 2
            cv2.putText(bgr, text, (x, y), font, scale, (0, 0, 0), thickness + 6, cv2.LINE_AA)
            cv2.putText(bgr, text, (x, y), font, scale, (0, 0, 255), thickness, cv2.LINE_AA)

        return bgr

    def _loop(self) -> None:
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
        while not self._stop.is_set():
            bgr = self.hub.get_latest_bgr()
            if bgr is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Waiting for camera...", (24, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.imshow(WINDOW_TITLE, placeholder)
                key = cv2.waitKey(20) & 0xFF
                if key == 27:
                    self._quit_requested.set()
                continue

            with self._lock:
                filt = self._filter_params
                countdown = self._countdown
                caption = self._caption

            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            rgba = np.concatenate([rgb, np.full((*rgb.shape[:2], 1), 255, np.uint8)], axis=2)
            processed = apply_filters_rgba(rgba, filt)
            preview_bgr = cv2.cvtColor(processed[:, :, :3], cv2.COLOR_RGB2BGR)

            preview_bgr = self._draw_overlay(preview_bgr, countdown, caption)
            cv2.imshow(WINDOW_TITLE, preview_bgr)

            key = cv2.waitKey(20) & 0xFF
            if key == 27:  # ESC
                self._quit_requested.set()
