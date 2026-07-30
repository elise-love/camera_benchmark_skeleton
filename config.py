# config.py
"""
全域設定。這個模組跟 take_pic_benchmark_tainan（正式系統）完全分開、不共用任何東西：
CameraKit.dll 的資產（IPEVOCameraKit/）跟評分模型（scoring_system/）都直接複製了一份
放在本模組底下，不讀、不 import、不修改正式系統的任何檔案。
"""

from __future__ import annotations

import copy
import os

MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(MODULE_ROOT, "data")

# 本模組自帶的資產（複製自正式系統，之後兩邊各自獨立維護，不會互相影響）
SCORING_SYSTEM_DIR = os.path.join(MODULE_ROOT, "scoring_system")
IPEVO_CAMERAKIT_DIR = os.path.join(MODULE_ROOT, "IPEVOCameraKit")

# ── 拍照節奏 ──────────────────────────────────────────────────────────
COUNTDOWN_SECONDS = 10          # 每張拍照前的倒數秒數（畫面 + terminal 都會顯示）
MIN_INTERVAL_SECONDS = 10       # 兩張照片之間至少間隔幾秒（跟評分/Optuna 處理時間取較長者）

# ── 相機預設值（每個新 user 都從這組「預設值」開始搜尋）───────────────
DEFAULT_CAMERA_PROFILE = {
    "camera": {"index": 0, "resolution": "1280x720", "fps": 30},
    "filters": {
        "brightness": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "hue_shift": 0.0,
        "gamma": 1.0,
        "temperature": 0.0,
        "enum": "none",
    },
    "capture": {
        "auto_exposure": 0.75,
        "exposure": None,
        "auto_wb": 1,
        "white_balance": None,
    },
}

# ── 參數安全範圍 ─────────────────────────────────────────────────────
# 這些範圍保留一點實驗對比幅度，但避免 Optuna 為了追分把照片推到不可用的極端狀態。
# tuple 格式固定為：(型別, 最小值, 最大值)
OPENCV_CAMERA_AXES = {
    "capture.exposure": ("float", -9.0, -4.0),
}

CAMERAKIT_CAMERA_AXES = {
    "capture.exposure": ("int", 4, 12),
    "capture.white_balance": ("int", 3500, 5600),
}

# 非搜尋軸也要有保護；例如手動載入舊參數或直接呼叫 set_capture() 時仍會套用。
CAPTURE_PARAM_RANGES = {
    "capture.white_balance": ("int", 2200, 7500),
    "capture.gain": ("float", 0.0, 255.0),
}

# 後製（濾鏡）搜尋軸，與相機後端無關
FILTER_AXES = {
    "filters.saturation":  ("float", 0.80, 1.30),
    "filters.gamma":       ("float", 0.85, 1.30),
    "filters.brightness":  ("float", -22.0, 22.0),
    "filters.contrast":    ("float", 0.85, 1.28),
    "filters.temperature": ("float", -10.0, 10.0),
    "filters.hue_shift":   ("float", -5.0, 5.0),
}

COLOR_HEALTH = {
    "min_score": 0.25,
    "cast_free_spread": 0.18,
    "cast_bad_spread": 0.80,
    "brightness_low": 70.0,
    "brightness_high": 190.0,
    "brightness_bad_low": 40.0,
    "brightness_bad_high": 225.0,
    "clip_free_fraction": 0.18,
    "clip_bad_fraction": 0.35,
}

PRE_CAPTURE_MIN_COLOR_HEALTH = 0.45
SAFE_CAPTURE_FALLBACKS = {
    "camerakit": {
        "exposure": 8,
        "white_balance": 4600,
    },
    "opencv": {
        "exposure": -6.5,
    },
}

DEFAULT_CAPTURE_RESETS = {
    "camerakit": {
        "auto_exposure": True,
        "auto_wb": True,
    },
    "opencv": {
        "auto_exposure": 0.75,
        "auto_wb": 1,
    },
    "mock": {},
}

PARAMETER_RANGES = {
    **CAPTURE_PARAM_RANGES,
    **FILTER_AXES,
}


def _get_path(d: dict, path: str):
    cur = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None, False
        cur = cur[key]
    return cur, True


def _set_path(d: dict, path: str, value) -> None:
    cur = d
    keys = path.split(".")
    for key in keys[:-1]:
        cur = cur.setdefault(key, {})
    cur[keys[-1]] = value


def clip_parameter_value(value, spec: tuple[str, float, float]):
    """Clip a numeric camera/filter parameter to its configured safe range."""
    if value is None:
        return None

    kind, lo, hi = spec
    clipped = min(max(float(value), float(lo)), float(hi))
    if kind == "int":
        return int(round(clipped))
    return round(clipped, 4)


def clip_nested_params(params: dict, extra_ranges: dict | None = None) -> dict:
    ranges = {**PARAMETER_RANGES, **(extra_ranges or {})}
    clipped = copy.deepcopy(params)
    for path, spec in ranges.items():
        value, exists = _get_path(clipped, path)
        if exists and value is not None:
            _set_path(clipped, path, clip_parameter_value(value, spec))
    _normalize_capture_mode(clipped.get("capture", {}))
    return clipped


def _normalize_capture_mode(capture: dict) -> None:
    if capture.get("exposure") is not None:
        capture["auto_exposure"] = False
    if capture.get("white_balance") is not None:
        capture["auto_wb"] = False


def clip_capture_params(params: dict, camera_axes: dict | None = None) -> dict:
    ranges = {}
    for path, spec in {**CAPTURE_PARAM_RANGES, **(camera_axes or {})}.items():
        if path.startswith("capture."):
            ranges[path.split(".", 1)[1]] = spec

    clipped = dict(params or {})
    for key, spec in ranges.items():
        if clipped.get(key) is not None:
            clipped[key] = clip_parameter_value(clipped[key], spec)
    _normalize_capture_mode(clipped)
    return clipped


def clip_filter_params(params: dict) -> dict:
    ranges = {
        path.split(".", 1)[1]: spec
        for path, spec in FILTER_AXES.items()
        if path.startswith("filters.")
    }
    clipped = dict(params or {})
    for key, spec in ranges.items():
        if clipped.get(key) is not None:
            clipped[key] = clip_parameter_value(clipped[key], spec)
    return clipped

# ── Optuna（TPE）設定 ────────────────────────────────────────────────
OPTUNA_N_STARTUP_TRIALS = 3     # 前幾張用隨機取樣探索，之後才交給 TPE 代理模型決定
OPTUNA_SEED = 0

# ── 評分設定 ─────────────────────────────────────────────────────────
# il_niqe 一張要 ~155 秒，不適合放進「拍一張等一張」的即時流程，預設跳過。
SCORE_METRICS = ("niqe", "brisque", "nima", "musiq")

# ── 相機後端 ─────────────────────────────────────────────────────────
CAMERA_INDEX = 0
CAMERA_BACKEND = "auto"   # auto｜camerakit｜opencv｜mock（mock 不需要真相機，方便先跑通流程）
