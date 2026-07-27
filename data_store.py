# data_store.py
"""
資料落地：每個 user、每個 session 都有自己的資料夾，raw 圖、處理後的圖、每一拍的參數
與分數（history.jsonl）、最後的最佳參數摘要（summary.json）全部留著，方便事後拿去分析。

資料夾結構：
  data/<user_id>/<session_timestamp>/
    raw/<NN>_raw.png            拍到的原圖（沒套濾鏡）
    processed/<NN>_processed.png 套用當次候選濾鏡後、拿去評分的圖
    history.jsonl                每一拍一行 JSON：params / scores / objective_score / 時間
    summary.json                這個 session 跑完的最佳參數與統計
"""

from __future__ import annotations

import os
import json
from datetime import datetime

import cv2
import numpy as np

import config


class SessionStore:
    def __init__(self, user_id: str):
        self.user_id = user_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(config.DATA_DIR, user_id, timestamp)
        self.raw_dir = os.path.join(self.session_dir, "raw")
        self.processed_dir = os.path.join(self.session_dir, "processed")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        self.history_path = os.path.join(self.session_dir, "history.jsonl")
        self.summary_path = os.path.join(self.session_dir, "summary.json")

    def save_raw(self, shot_index: int, rgba: np.ndarray) -> str:
        path = os.path.join(self.raw_dir, f"{shot_index:02d}_raw.png")
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(path, bgr)
        return path

    def save_processed(self, shot_index: int, rgba: np.ndarray) -> str:
        path = os.path.join(self.processed_dir, f"{shot_index:02d}_processed.png")
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(path, bgr)
        return path

    def append_history(self, record: dict) -> None:
        record = dict(record)
        record.setdefault("recorded_at", datetime.now().isoformat(timespec="seconds"))
        with open(self.history_path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_summary(self, summary: dict) -> str:
        with open(self.summary_path, "w", encoding="utf-8") as fp:
            json.dump(summary, fp, ensure_ascii=False, indent=2)
        return self.summary_path
