# scoring_client.py
"""
呼叫本模組自帶的 scoring_system/main.py（NIQE/BRISQUE/NIMA/MUSIQ，複製自正式系統，
獨立維護）拿分數，並把方向不一致的原始分數正規化成單一「越高越好」的 objective_score，
餵給 Optuna 當目標值。

用 subprocess 呼叫而不是 import：scoring_system 依賴 TensorFlow/PyTorch 這類重量級套件，
獨立用一個 CLI 呼叫，跟本模組其他部分的 import 邊界切乾淨。
"""

from __future__ import annotations

import os
import json
import glob
import tempfile
import subprocess

import numpy as np

import config

CANON2SYS = {"niqe": "niqe", "il_niqe": "ilniqe", "brisque": "brisque",
             "nima": "nima", "musiq": "musiq"}

LOWER_BETTER = {
    "niqe":    (2.0,  15.0),
    "il_niqe": (10.0, 45.0),
    "brisque": (10.0, 80.0),
}
HIGHER_BETTER = {
    "nima":  (3.0,  8.0),
    "musiq": (30.0, 80.0),
}
DEFAULT_WEIGHTS = {"niqe": 1.0, "il_niqe": 1.0, "brisque": 1.0, "nima": 1.0, "musiq": 1.0}


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def normalize_scores(scores: dict, weights: dict | None = None) -> float:
    """原始分數 dict → 單一 objective_score（0~1，越高越好）。缺的指標自動略過。"""
    w = dict(DEFAULT_WEIGHTS if weights is None else weights)
    norms: dict[str, float] = {}
    for name, (lo, hi) in LOWER_BETTER.items():
        if scores.get(name) is not None:
            norms[name] = _clip01((hi - float(scores[name])) / (hi - lo))
    for name, (lo, hi) in HIGHER_BETTER.items():
        if scores.get(name) is not None:
            norms[name] = _clip01((float(scores[name]) - lo) / (hi - lo))
    if not norms:
        raise ValueError("scores 裡沒有任何可辨識的指標")
    total_w = sum(w.get(k, 0.0) for k in norms) or 1.0
    return round(sum(norms[k] * w.get(k, 0.0) for k in norms) / total_w, 4)


class ScoringSystemBackend:
    """包住本模組自帶 scoring_system/main.py 的 CLI。"""

    def __init__(self, scoring_dir: str | None = None, python_exe: str | None = None,
                 metrics=config.SCORE_METRICS, timeout: int | None = None):
        self.scoring_dir = scoring_dir or config.SCORING_SYSTEM_DIR
        if not os.path.isdir(self.scoring_dir):
            raise FileNotFoundError(
                f"找不到 scoring_system 資料夾：{self.scoring_dir}。"
                "請確認本模組底下有完整的 scoring_system/ 資料夾。")
        self.python_exe = python_exe or "python"
        self.metrics = tuple(metrics)
        self.timeout = timeout

    def run_folder(self, input_path: str) -> dict:
        sys_metrics = ",".join(CANON2SYS[m] for m in self.metrics)
        with tempfile.TemporaryDirectory() as tmp:
            json_out = os.path.join(tmp, "scores.json")
            cmd = [
                self.python_exe, "main.py",
                "--input", os.path.abspath(input_path),
                "--metrics", sys_metrics,
                "--json", json_out,
                "--output-dir", tmp,
            ]
            subprocess.run(cmd, cwd=self.scoring_dir, check=True, timeout=self.timeout)
            with open(json_out, "r", encoding="utf-8") as fp:
                payload = json.load(fp)

        out: dict[str, dict] = {}
        for row in payload.get("results", []):
            name = row.get("image")
            scores: dict[str, float] = {}
            for canon, sysname in CANON2SYS.items():
                if canon not in self.metrics:
                    continue
                val = row.get(f"{sysname}_score")
                err = row.get(f"{sysname}_error")
                if val is not None and not err:
                    scores[canon] = float(val)
            out[name] = scores
        return out


class MockScorer:
    """--mock 用：從畫面亮度/對比瞎編分數，不需要真的評分系統，先測通流程用。"""

    def __init__(self, metrics=config.SCORE_METRICS):
        self.metrics = tuple(metrics)

    def run_folder(self, input_path: str) -> dict:
        paths = ([input_path] if os.path.isfile(input_path)
                 else sorted(glob.glob(os.path.join(input_path, "*.png")) +
                             glob.glob(os.path.join(input_path, "*.jpg"))))
        out = {}
        for p in paths:
            import cv2
            img = cv2.imread(p).astype(np.float32)
            mean, std = float(img.mean()), float(img.std())
            rng = np.random.default_rng(int(mean * 1000) % (2**32))
            j = lambda s: float(rng.normal(0, s))
            full = {
                "niqe":    11.0 - std / 40 + j(0.15),
                "il_niqe": 35.0 - std / 20 + j(0.5),
                "brisque": 55.0 - std / 15 + j(0.8),
                "nima":    5.8 + std / 120 + j(0.1),
                "musiq":   48.0 + std / 6 - abs(mean - 128) / 12 + j(1.0),
            }
            out[os.path.basename(p)] = {m: full[m] for m in self.metrics}
        return out


class ScoringClient:
    def __init__(self, backend, weights: dict | None = None):
        self.backend = backend
        self.weights = weights or dict(DEFAULT_WEIGHTS)

    def score_folder(self, folder: str) -> dict:
        raw = self.backend.run_folder(folder)
        result = {}
        for fname, scores in raw.items():
            result[fname] = {"scores": scores,
                             "objective_score": normalize_scores(scores, self.weights)}
        return result

    def score_one(self, path: str) -> dict:
        """對單一檔案評分（每拍一張就評一次，不用每次重新掃整個資料夾）。"""
        raw = self.backend.run_folder(path)
        if not raw:
            raise RuntimeError(f"評分系統沒有回傳任何結果：{path}")
        scores = next(iter(raw.values()))
        return {"scores": scores, "objective_score": normalize_scores(scores, self.weights)}


def build_scorer(use_mock: bool) -> ScoringClient:
    if use_mock:
        return ScoringClient(backend=MockScorer())
    return ScoringClient(backend=ScoringSystemBackend())
