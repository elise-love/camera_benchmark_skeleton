# main.py
"""
拍照 benchmark 骨架模組（獨立於正式系統 take_pic_benchmark_tainan，不會動到它）。

流程（對應 status_display 印出的大字看板）：
  輸入 User 名稱、要拍幾張
    → 每一張：套用 Optuna(TPE) 建議的候選參數 → 倒數 10 秒 → 拍照
      → 評分（NIQE/BRISQUE/NIMA/MUSIQ）→ 回報給 Optuna(TPE) → 建議下一組參數
    → 拍完這個 user 的張數 → 寫出這個 user 的最佳參數摘要 → 回到輸入下一個 user

拍照間隔規則：每張之間至少 config.MIN_INTERVAL_SECONDS 秒，若上一張的評分/Optuna
處理花得比這個久，就用處理花的時間（取兩者較長）。因為整個迴圈是完全同步、一步一步
做完才做下一步（沒有「邊拍下一張邊算上一張分數」的平行處理），所以「等處理跑完」
本來就是自動滿足的；下面的 sleep 只是保險，避免以後有人把倒數秒數調得比間隔秒數短。
"""

from __future__ import annotations

import os
import re
import sys
import time
import traceback

import cv2
import numpy as np

import config
import status_display as sd
from camera_backend import open_backend
from data_store import SessionStore
from filters import FilterParams
from optimizer_session import OptunaSession
from preview_window import FrameHub, PreviewWindow
from scoring_client import ScoringClient, build_scorer

# Windows 的舊版 cmd.exe 預設 codepage 常常不是 UTF-8，中文狀態文字會變亂碼；
# 這裡盡量把 stdout 轉成 UTF-8，轉不了（極少數環境）就算了，不影響程式運作。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _bgr_to_rgba(bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.concatenate([rgb, np.full((*rgb.shape[:2], 1), 255, np.uint8)], axis=2)


def _filter_params_from(candidate: dict) -> FilterParams:
    f = config.clip_filter_params(candidate.get("filters", {}))
    return FilterParams(
        brightness=float(f.get("brightness", 0.0)),
        contrast=float(f.get("contrast", 1.0)),
        saturation=float(f.get("saturation", 1.0)),
        hue_shift=float(f.get("hue_shift", 0.0)),
        gamma=float(f.get("gamma", 1.0)),
        temperature=float(f.get("temperature", 0.0)),
        enum=str(f.get("enum", "none")),
    )


def _sanitize_user_id(raw: str) -> str:
    """User 名稱會直接拿去當資料夾名稱，擋掉 Windows 路徑不允許的字元。"""
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", raw).strip()
    return cleaned or "user"


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "(Y/n)" if default else "(y/N)"
    raw = input(f"{prompt} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def _ask_shot_count() -> int:
    while True:
        raw = input("這位 user 要拍幾張？（例如 8）: ").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        sd.line("請輸入一個正整數。", "warn")


def preflight_check(scorer: ScoringClient, backend) -> None:
    """開跑前先確認評分系統至少能回傳一個指標，避免拍到一半才發現評分系統壞掉。"""
    sd.line("評分系統預檢中…", "info")
    for _ in range(6):
        backend.read()
    ok, bgr = backend.read()
    if not ok or bgr is None:
        raise RuntimeError("相機讀不到畫面，無法預檢評分系統。")
    tmp_dir = os.path.join(config.DATA_DIR, "_preflight")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, "preflight.png")
    cv2.imwrite(tmp_path, bgr)
    scored = scorer.score_one(tmp_path)
    sd.line(f"評分系統 OK：{scored['scores']}", "good")


def run_shot(shot_index: int, total: int, session: SessionStore,
            optuna_session: OptunaSession, backend, hub: FrameHub,
            preview: PreviewWindow, scorer: ScoringClient) -> dict:
    sd.section(f"第 {shot_index}/{total} 張")

    # ── 套用新參數 ──────────────────────────────────────────────
    sd.banner("APPLY PARAMS", "套用新參數中", "busy")
    candidate = optuna_session.suggest_next()
    capture_cfg = OptunaSession.split_capture(candidate)
    if capture_cfg:
        backend.set_capture(capture_cfg)
    filt = _filter_params_from(candidate)
    preview.set_filter_params(filt)
    preview.set_caption(f"Shot {shot_index}/{total} - Preparing")

    # ── 倒數 ────────────────────────────────────────────────────
    for n in range(config.COUNTDOWN_SECONDS, 0, -1):
        preview.set_countdown(n)
        preview.set_caption(f"Shot {shot_index}/{total} - Countdown")
        sd.countdown_tick(n)
        time.sleep(1)
    preview.set_countdown(None)

    # ── 拍照 ────────────────────────────────────────────────────
    sd.banner("CAPTURING", "拍照中", "busy")
    preview.set_caption(f"Shot {shot_index}/{total} - Capturing")
    bgr = hub.get_latest_bgr()
    if bgr is None:
        raise RuntimeError("拍照失敗：目前沒有可用畫面。")
    raw_rgba = _bgr_to_rgba(bgr)
    raw_path = session.save_raw(shot_index, raw_rgba)

    from filters import apply_filters_rgba
    processed_rgba = apply_filters_rgba(raw_rgba, filt)
    processed_path = session.save_processed(shot_index, processed_rgba)

    # ── 評分 ────────────────────────────────────────────────────
    sd.banner("SCORING", "計算 NIMA 等分數中", "busy")
    preview.set_caption(f"Shot {shot_index}/{total} - Scoring (NIQE/BRISQUE/NIMA/MUSIQ)")
    scored = scorer.score_one(processed_path)
    sd.line(f"  分數：{scored['scores']}", "info")
    sd.line(f"  objective_score = {scored['objective_score']:.4f}", "info")

    # ── 回報給 Optuna(TPE)，取得下一輪基準 ─────────────────────
    sd.banner("OPTUNA TPE", "計算 OPTUNA(TPE) 中", "busy")
    preview.set_caption(f"Shot {shot_index}/{total} - Optuna(TPE) updating")
    optuna_session.report(scored["objective_score"])

    session.append_history({
        "shot_index": shot_index,
        "params": candidate,
        "scores": scored["scores"],
        "objective_score": scored["objective_score"],
        "raw_path": os.path.relpath(raw_path, session.session_dir),
        "processed_path": os.path.relpath(processed_path, session.session_dir),
    })
    return scored


def run_user_session(user_id: str, backend, hub: FrameHub, preview: PreviewWindow,
                     scorer: ScoringClient) -> None:
    total = _ask_shot_count()
    session = SessionStore(_sanitize_user_id(user_id))
    optuna_session = OptunaSession(camera_axes=backend.camera_axes())

    sd.banner("USER SESSION START", f"{user_id} 開始", "good")
    sd.line(f"資料會存在：{session.session_dir}", "info")

    last_capture_time = None
    for shot_index in range(1, total + 1):
        if preview.is_quit_requested():
            sd.line("偵測到 ESC，中止這個 user 的拍攝。", "warn")
            break

        if last_capture_time is not None:
            elapsed = time.time() - last_capture_time
            if elapsed < config.MIN_INTERVAL_SECONDS:
                remaining = config.MIN_INTERVAL_SECONDS - elapsed
                sd.line(f"距離上一張還不到 {config.MIN_INTERVAL_SECONDS} 秒，補等 {remaining:.1f} 秒…", "info")
                time.sleep(remaining)

        run_shot(shot_index, total, session, optuna_session, backend, hub, preview, scorer)
        last_capture_time = time.time()

    best = optuna_session.best()
    session.write_summary({
        "user_id": user_id,
        "shots_taken": total,
        "best_params": best["best_params"],
        "best_score": best["best_score"],
        "n_trials": best["n_trials"],
    })

    sd.banner("USER SESSION DONE", f"{user_id} 完成", "good")
    sd.line(f"最佳 objective_score = {best['best_score']}", "good")
    sd.line(f"摘要已寫到：{session.summary_path}", "good")


def main() -> None:
    sd.banner("BENCHMARK SKELETON", "拍照 Benchmark 骨架", "info")
    sd.line(f"（獨立模組，評分模型/CameraKit 都已內附在 {config.MODULE_ROOT}）", "info")

    use_mock = _ask_yes_no("是否使用模擬相機/評分（mock，沒接相機或評分系統時先測流程）？", default=False)

    backend_name = "mock" if use_mock else config.CAMERA_BACKEND
    sd.banner("CAMERA INIT", "相機初始化中", "busy")
    backend = open_backend(backend_name)

    hub = FrameHub(backend)
    hub.start()
    preview = PreviewWindow(hub)
    preview.start()

    scorer = build_scorer(use_mock)

    time.sleep(1.0)  # 讓 FrameHub 先抓到第一張畫面
    try:
        if not use_mock:
            preflight_check(scorer, backend)
    except Exception as e:
        sd.banner("PREFLIGHT FAILED", "評分系統預檢失敗", "error")
        sd.line(f"{type(e).__name__}: {e}", "error")
        sd.line(f"請確認 {config.SCORING_SYSTEM_DIR} 底下的評分環境（tensorflow/torch/scipy 等）"
               "已安裝好，或重新啟動後選擇 mock 模式先測流程。", "warn")
        preview.stop()
        hub.stop()
        backend.release()
        sys.exit(1)

    try:
        while True:
            sd.section("等待輸入")
            user_id = input("請輸入 User 名稱（例如 User 1；輸入 exit 結束程式）: ").strip()
            if not user_id:
                continue
            if user_id.lower() in ("exit", "quit", "q"):
                break
            if preview.is_quit_requested():
                sd.line("偵測到 ESC，結束程式。", "warn")
                break

            try:
                run_user_session(user_id, backend, hub, preview, scorer)
            except Exception:
                sd.banner("USER SESSION ERROR", "這位 user 發生錯誤", "error")
                traceback.print_exc()
                sd.line("已略過，回到輸入畫面。", "warn")

            if preview.is_quit_requested():
                sd.line("偵測到 ESC，結束程式。", "warn")
                break
    except KeyboardInterrupt:
        sd.line("收到 Ctrl+C，結束程式。", "warn")
    finally:
        sd.banner("SHUTTING DOWN", "結束中", "info")
        preview.stop()
        hub.stop()
        backend.release()


if __name__ == "__main__":
    main()
