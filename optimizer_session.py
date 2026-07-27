# optimizer_session.py
"""
每個 user session 一個獨立的 Optuna（TPE）study：從 config.DEFAULT_CAMERA_PROFILE 這組
「預設值」開始，每拍一張＝一個 trial，把該張的 objective_score 回報給 TPE，讓它建議下一組
候選參數（相機曝光/白平衡 + 後製濾鏡一起搜）。

簡化說明（這是骨架，不是正式系統的完整版）：
  正式系統的 online_optuna.py 用「候選 vs. 固定參考」的配對差值來抵消現場光線雜訊，
  一個 trial 要拍 2×N 張。這裡為了讓「輸入拍幾張、系統就拍幾張」的流程單純好懂，
  改成一個 trial 只拍 1 張、直接把 objective_score 回報給 TPE。
  如果之後要更精準抗雜訊，可以參考正式系統的作法把這裡換成配對比較。
"""

from __future__ import annotations

import copy

import optuna

import config


def _get(d: dict, path: str):
    cur = d
    for k in path.split("."):
        cur = cur[k]
    return cur


def _set(d: dict, path: str, val) -> None:
    keys = path.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = val


class OptunaSession:
    def __init__(self, camera_axes: dict, base_params: dict | None = None,
                 seed: int = config.OPTUNA_SEED):
        self.axes_def = {**camera_axes, **config.FILTER_AXES}
        self.axes = list(self.axes_def.keys())
        self.base = copy.deepcopy(base_params or config.DEFAULT_CAMERA_PROFILE)

        sampler = optuna.samplers.TPESampler(
            seed=seed, n_startup_trials=config.OPTUNA_N_STARTUP_TRIALS)
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        self.study = optuna.create_study(direction="maximize", sampler=sampler)
        self._pending_trial = None

    def suggest_next(self) -> dict:
        """回傳下一組要試的候選參數（nested dict，跟 camera_config 同形狀）。"""
        trial = self.study.ask()
        self._pending_trial = trial
        params = copy.deepcopy(self.base)
        for path in self.axes:
            kind, lo, hi = self.axes_def[path]
            if kind == "int":
                val = trial.suggest_int(path, int(lo), int(hi))
            else:
                val = round(float(trial.suggest_float(path, lo, hi)), 4)
            _set(params, path, val)
        return params

    def report(self, objective_score: float) -> None:
        if self._pending_trial is None:
            raise RuntimeError("要先呼叫 suggest_next() 才能 report()")
        self.study.tell(self._pending_trial, objective_score)
        self._pending_trial = None

    def best(self) -> dict:
        # study.best_trial 在「一個 trial 都還沒 tell() 完成」時會丟 ValueError
        # （不是回傳 None），所以用 try/except 判斷，不能只檢查 trials 是否為空。
        try:
            best_trial = self.study.best_trial
        except ValueError:
            return {"best_params": self.base, "best_score": None,
                    "n_trials": len(self.study.trials)}
        best = copy.deepcopy(self.base)
        for path, value in best_trial.params.items():
            _set(best, path, value)
        return {
            "best_params": best,
            "best_score": self.study.best_value,
            "n_trials": len(self.study.trials),
        }

    @staticmethod
    def split_capture(params: dict) -> dict:
        cap = params.get("capture", {}) or {}
        keys = ("exposure", "white_balance", "auto_exposure", "auto_wb")
        return {k: cap[k] for k in keys if cap.get(k) is not None}

    @staticmethod
    def split_filters(params: dict) -> dict:
        return params.get("filters", {})
