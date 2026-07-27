# config.py
"""
全域設定。這個模組跟 take_pic_benchmark_tainan（正式系統）完全分開、不共用任何東西：
CameraKit.dll 的資產（IPEVOCameraKit/）跟評分模型（scoring_system/）都直接複製了一份
放在本模組底下，不讀、不 import、不修改正式系統的任何檔案。
"""

from __future__ import annotations

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

# 後製（濾鏡）搜尋軸，與相機後端無關
FILTER_AXES = {
    "filters.saturation":  ("float", 0.5, 2.0),
    "filters.gamma":       ("float", 0.5, 2.5),
    "filters.brightness":  ("float", -30.0, 30.0),
    "filters.contrast":    ("float", 0.3, 2.0),
    "filters.temperature": ("float", -20.0, 20.0),
}

# ── Optuna（TPE）設定 ────────────────────────────────────────────────
OPTUNA_N_STARTUP_TRIALS = 3     # 前幾張用隨機取樣探索，之後才交給 TPE 代理模型決定
OPTUNA_SEED = 0

# ── 評分設定 ─────────────────────────────────────────────────────────
# il_niqe 一張要 ~155 秒，不適合放進「拍一張等一張」的即時流程，預設跳過。
SCORE_METRICS = ("niqe", "brisque", "nima", "musiq")

# ── 相機後端 ─────────────────────────────────────────────────────────
CAMERA_INDEX = 0
CAMERA_BACKEND = "auto"   # auto｜camerakit｜opencv｜mock（mock 不需要真相機，方便先跑通流程）
