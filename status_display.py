# status_display.py
"""
Terminal 狀態看板：用 pyfiglet 把「現在進行到哪個步驟」印成放大的 ASCII 字，
搭配 colorama 上色，讓人在拍照機前遠遠一眼就看得到現在是「拍照中」還是「計算中」。
"""

from __future__ import annotations

import shutil

import pyfiglet
from colorama import Fore, Style, init as _colorama_init

_colorama_init(autoreset=True)

_COLOR_BY_KIND = {
    "info":  Fore.CYAN,
    "busy":  Fore.YELLOW,
    "good":  Fore.GREEN,
    "warn":  Fore.MAGENTA,
    "error": Fore.RED,
}


def _term_width() -> int:
    return shutil.get_terminal_size(fallback=(100, 30)).columns


def _pick_font(text: str) -> str:
    # 字太多的時候用窄一點的字型，避免每個字都被迫換行變得難讀。
    return "small" if len(text) > 10 else "standard"


def banner(label_en: str, label_zh: str = "", kind: str = "info") -> None:
    """印出一個放大的 ASCII 狀態看板，作為「現在進行到哪一步」的主要提示。

    pyfiglet 的字型只有 Latin 字母/數字的 ASCII-art 對照表，沒有中文字型可用，
    直接丟中文字串進去會找不到對應字形而出錯。所以放大的 ASCII 看板一律用英文
    關鍵字（label_en），中文說明（label_zh）用大寫、加框、上色的方式緊接著印在
    下面，兩個一起看才不會有語言隔閡。
    """
    color = _COLOR_BY_KIND.get(kind, Fore.WHITE)
    try:
        art = pyfiglet.figlet_format(label_en, font=_pick_font(label_en), width=max(80, _term_width()))
    except Exception:
        # 保底：萬一 label_en 混進 pyfiglet 字型畫不出來的字元，退回普通大寫文字，
        # 不要讓一個看板印失敗就把整個拍照流程炸掉。
        art = f"[[ {label_en.upper()} ]]\n"
    print()
    print(color + art + Style.RESET_ALL)
    if label_zh:
        print(color + Style.BRIGHT + f">>> {label_zh} <<<" + Style.RESET_ALL)


def line(text: str, kind: str = "info") -> None:
    """次要訊息，一般大小就好（進度細節、數值、錯誤堆疊等）。"""
    color = _COLOR_BY_KIND.get(kind, Fore.WHITE)
    print(color + text + Style.RESET_ALL)


def countdown_tick(n: int) -> None:
    """倒數用：每一秒印一個大大的數字。"""
    art = pyfiglet.figlet_format(str(n), font="big")
    print(Fore.RED + art + Style.RESET_ALL)


def section(title: str) -> None:
    width = min(100, _term_width())
    print()
    print(Fore.BLUE + "=" * width)
    print(Fore.BLUE + Style.BRIGHT + f" {title}")
    print(Fore.BLUE + "=" * width + Style.RESET_ALL)
