# -*- coding: utf-8 -*-
"""
全自動多腳本觸發器 (Multi-Script Trigger) — 美式漫畫風
======================================================
每個「觸發鍵」綁定一段獨立的連點腳本：
  - 啟用後，按下某個觸發鍵 → 該腳本開始循環；再按一次 → 停止（切換模式）。
  - 不同腳本可「同時」執行（各自獨立執行緒）。
  - 每個腳本可錄製 / 手動編輯步驟，並各自設定按住時間、延遲、循環次數。
  - 正確支援右側數字鍵盤(numpad / vk)。
  - 內建自我觸發防護：腳本送出的按鍵不會誤觸其他腳本的觸發鍵。

技術：tkinter + pynput      相依套件：pip install pynput
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput.keyboard import Controller as KbController, Key, KeyCode, Listener as KbListener
from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener


# ============================================================
# 主題系統（多套配色，可即時切換）
# ------------------------------------------------------------
# 設計說明：每個色彩「角色」在不同主題代表同一語意，UI 只認角色名：
#   BG     視窗底色            PANEL  面板底色
#   INK    外框墨線 / 高亮時的反色文字（需與 YELLOW 對比）
#   WHITE  疊在彩色按鈕上的文字色（淺色主題用白、亮色主題改用深色）
#   TEXT   面板上的主要文字     SUB    次要說明文字
#   PAPER  輸入框 / 標籤底色
#   RED 危險  YELLOW 高亮/警示  CYAN 主色  GREEN 確定  PURPLE 次要
#   FONT 內文字體  TITLE_FONT 標題字體
# ============================================================
THEMES = {
    "美漫經典": {
        "BG": "#ffd21e", "PANEL": "#fffaf0", "INK": "#0b0b0b", "WHITE": "#ffffff",
        "TEXT": "#161616", "SUB": "#6b6457", "PAPER": "#fff7e6",
        "RED": "#e8392b", "YELLOW": "#ffd21e", "CYAN": "#2b6fe8",
        "GREEN": "#2aa84a", "PURPLE": "#8e44ad",
        "FONT": "Comic Sans MS", "TITLE_FONT": "Impact",
    },
    "暗夜霓虹": {
        "BG": "#12121c", "PANEL": "#1c1c2b", "INK": "#000000", "WHITE": "#101018",
        "TEXT": "#e8e8f5", "SUB": "#8a8aa8", "PAPER": "#0e0e18",
        "RED": "#ff4d6d", "YELLOW": "#ffe14d", "CYAN": "#43d9ff",
        "GREEN": "#3ef0a0", "PURPLE": "#c08bff",
        "FONT": "Segoe UI", "TITLE_FONT": "Segoe UI Black",
    },
    "極簡淺灰": {
        "BG": "#eef1f5", "PANEL": "#ffffff", "INK": "#334155", "WHITE": "#ffffff",
        "TEXT": "#1f2937", "SUB": "#6b7280", "PAPER": "#f8fafc",
        "RED": "#ef4444", "YELLOW": "#f59e0b", "CYAN": "#3b82f6",
        "GREEN": "#22c55e", "PURPLE": "#8b5cf6",
        "FONT": "Segoe UI", "TITLE_FONT": "Segoe UI Semibold",
    },
    "德古拉暗黑": {
        "BG": "#282a36", "PANEL": "#21222c", "INK": "#14151c", "WHITE": "#21222c",
        "TEXT": "#f8f8f2", "SUB": "#6272a4", "PAPER": "#191a21",
        "RED": "#ff5555", "YELLOW": "#f1fa8c", "CYAN": "#8be9fd",
        "GREEN": "#50fa7b", "PURPLE": "#bd93f9",
        "FONT": "Consolas", "TITLE_FONT": "Consolas",
    },
    "日式動漫": {
        "BG": "#aee3ff", "PANEL": "#ffffff", "INK": "#2b3a55", "WHITE": "#ffffff",
        "TEXT": "#2b3a55", "SUB": "#7a8aa5", "PAPER": "#f4fbff",
        "RED": "#ff5d8f", "YELLOW": "#ffd83d", "CYAN": "#38b6ff",
        "GREEN": "#57d9a3", "PURPLE": "#b06ef0",
        "FONT": "Microsoft JhengHei", "TITLE_FONT": "Microsoft JhengHei",
    },
    "賽博龐克": {
        "BG": "#0d0221", "PANEL": "#1a0b2e", "INK": "#05010d", "WHITE": "#0a0118",
        "TEXT": "#f0e9ff", "SUB": "#8f7fb0", "PAPER": "#120726",
        "RED": "#ff2d6f", "YELLOW": "#f9f002", "CYAN": "#00e5ff",
        "GREEN": "#2bff88", "PURPLE": "#c84bff",
        "FONT": "Consolas", "TITLE_FONT": "Consolas",
    },
    "馬卡龍粉彩": {
        "BG": "#fde2e4", "PANEL": "#fff7f9", "INK": "#6d5d6e", "WHITE": "#5a4a5a",
        "TEXT": "#5a4a5a", "SUB": "#9a8a9a", "PAPER": "#fffafc",
        "RED": "#f48fa0", "YELLOW": "#ffe08a", "CYAN": "#9ec5f0",
        "GREEN": "#a7d9b9", "PURPLE": "#c9a8e0",
        "FONT": "Microsoft JhengHei", "TITLE_FONT": "Microsoft JhengHei",
    },
}

DEFAULT_THEME = "美漫經典"
CURRENT_THEME = DEFAULT_THEME


def apply_theme(name):
    """把指定主題的色彩 / 字體寫進全域變數，供所有 UI 元件即時取用。"""
    global CURRENT_THEME, BG, PANEL, INK, WHITE, TEXT, SUB, PAPER
    global RED, YELLOW, CYAN, GREEN, PURPLE
    global FONT, TITLE_FONT, F_TITLE, F_H, F_N, F_B
    if name not in THEMES:
        name = DEFAULT_THEME
    CURRENT_THEME = name
    t = THEMES[name]
    BG, PANEL, INK, WHITE = t["BG"], t["PANEL"], t["INK"], t["WHITE"]
    TEXT, SUB, PAPER = t["TEXT"], t["SUB"], t["PAPER"]
    RED, YELLOW, CYAN = t["RED"], t["YELLOW"], t["CYAN"]
    GREEN, PURPLE = t["GREEN"], t["PURPLE"]
    FONT, TITLE_FONT = t["FONT"], t["TITLE_FONT"]
    # 字體 tuple 依當前字體重建（換主題若改字體，這些也要跟著更新）
    F_TITLE = (TITLE_FONT, 20, "bold")
    F_H = (FONT, 11, "bold")
    F_N = (FONT, 10)
    F_B = (FONT, 10, "bold")


# 模組載入時先套用預設主題，建立全域變數
apply_theme(DEFAULT_THEME)

PANIC_DEFAULT = {"type": "key", "key_kind": "special", "key_value": "f12"}
ARM_DEFAULT = {"type": "key", "key_kind": "special", "key_value": "f9"}
STARTALL_DEFAULT = {"type": "key", "key_kind": "special", "key_value": "f8"}   # 一鍵全部啟動快捷鍵（預設 F8）


def settings_path():
    """自動存檔位置：打包成 exe 時取 exe 同目錄，否則取原始碼同目錄。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "settings.json")


MOUSE_MAP = {"left": Button.left, "middle": Button.middle, "right": Button.right}
# 滑鼠側邊鍵（x1=後退 / x2=前進）：部分 pynput 版本/平台才有，存在才加入避免 AttributeError
for _side in ("x1", "x2"):
    _btn = getattr(Button, _side, None)
    if _btn is not None:
        MOUSE_MAP[_side] = _btn

MOUSE_LABEL = {"left": "滑鼠左鍵", "middle": "滑鼠中鍵", "right": "滑鼠右鍵",
               "x1": "滑鼠側鍵1", "x2": "滑鼠側鍵2"}

# 可被「偵測」的滑鼠鍵名（用於捕捉觸發鍵 / 錄製 / 比對）。
# 注意：與 MOUSE_MAP 分離——MOUSE_MAP 用於「輸出」需真正的 Button 物件，
# 而偵測時 pynput 已直接給我們 button 物件，只需比對名稱，故側鍵一律納入，
# 避免某些 pynput 版本未把 x1/x2 放進 MOUSE_MAP 導致側鍵被擋掉。
DETECT_BUTTONS = {"left", "middle", "right", "x1", "x2"}

VK_NAMES = {
    96: "數字鍵盤0", 97: "數字鍵盤1", 98: "數字鍵盤2", 99: "數字鍵盤3",
    100: "數字鍵盤4", 101: "數字鍵盤5", 102: "數字鍵盤6", 103: "數字鍵盤7",
    104: "數字鍵盤8", 105: "數字鍵盤9",
    106: "數字鍵盤*", 107: "數字鍵盤+", 109: "數字鍵盤-",
    110: "數字鍵盤.", 111: "數字鍵盤/",
}


# ===== 按鍵 <-> 欄位 <-> 文字 =====
def key_to_fields(key):
    if isinstance(key, Key):
        return ("special", key.name)
    if isinstance(key, KeyCode):
        if key.char is not None:
            return ("char", key.char)
        if key.vk is not None:
            return ("vk", key.vk)
    return (None, None)


def fields_display(kind, value):
    if kind == "special":
        return value.upper()
    if kind == "char":
        return value.upper()
    if kind == "vk":
        return VK_NAMES.get(value, f"VK{value}")
    return "?"


def reconstruct_key_fields(kind, value):
    if kind == "special":
        return getattr(Key, value)
    if kind == "char":
        return KeyCode.from_char(value)
    if kind == "vk":
        return KeyCode.from_vk(value)
    raise ValueError(f"unknown kind {kind}")


def step_action_text(step):
    if step["type"] == "mouse":
        return MOUSE_LABEL.get(step["button"], "滑鼠鍵")
    return fields_display(step["key_kind"], step["key_value"])


def trigger_display(trigger):
    if not trigger:
        return "（未設定）"
    if trigger["type"] == "mouse":
        return MOUSE_LABEL.get(trigger["button"], "滑鼠鍵")
    return fields_display(trigger["key_kind"], trigger["key_value"])


# ===== 漫畫風小工具 =====
def comic_button(parent, text, cmd, bg=None, fg=None, width=None, font=None):
    # 預設值在函式體內解析，確保「即時換主題」後取到當前色彩，而非定義時凍結的舊值
    bg = CYAN if bg is None else bg
    fg = WHITE if fg is None else fg
    font = F_B if font is None else font
    hover_bg, hover_fg = YELLOW, INK   # 滑入時的高亮色（先快取，閉包才不會抓到後續變動）
    # 粗黑外框 + 滑入變亮，模擬美漫按鈕貼紙感
    btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                    activebackground=hover_bg, activeforeground=hover_fg,
                    font=font, relief="raised", bd=4, cursor="hand2",
                    highlightbackground=INK, highlightcolor=INK, highlightthickness=2)
    if width:
        btn.config(width=width)
    btn.bind("<Enter>", lambda e: btn["state"] == "normal" and btn.config(bg=hover_bg, fg=hover_fg))
    btn.bind("<Leave>", lambda e: btn["state"] == "normal" and btn.config(bg=bg, fg=fg))
    btn._base_bg = bg
    return btn


def panel(parent):
    # 紙白面板 + 粗黑墨線外框
    return tk.Frame(parent, bg=PANEL, bd=4, relief="ridge",
                    highlightbackground=INK, highlightthickness=3)


def dark_label(parent, text, fg=None, font=None, bg=None):
    # 同理：預設值在體內解析，換主題後才會套到當前色彩
    fg = TEXT if fg is None else fg
    font = F_N if font is None else font
    bg = PANEL if bg is None else bg
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=font)


def dark_entry(parent, textvariable, width=10):
    # 紙色輸入框 + 黑字 + 粗黑外框
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=PAPER, fg=TEXT, insertbackground=RED,
                    relief="solid", bd=2, font=F_B, justify="center",
                    highlightbackground=INK, highlightcolor=CYAN, highlightthickness=1)


# ===== 新增 / 編輯步驟對話框 =====
class StepDialog(tk.Toplevel):
    def __init__(self, parent, init=None):
        super().__init__(parent)
        self.result = None
        self.captured = (None, None)
        self.capture_listener = None
        self.title("步驟設定")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        pad = {"padx": 8, "pady": 6}
        frm = tk.Frame(self, bg=PANEL, padx=16, pady=16)
        frm.grid(row=0, column=0)
        dark_label(frm, "動作類型", fg=RED, font=F_H).grid(row=0, column=0, sticky="w", **pad)
        self.var_type = tk.StringVar(value="key")
        type_frm = tk.Frame(frm, bg=PANEL)
        type_frm.grid(row=0, column=1, columnspan=2, sticky="w")
        # 含側鍵（前進/後退鍵），讓錄製到的側鍵步驟也能正確顯示與編輯
        for text, val in (("鍵盤按鍵", "key"), ("左鍵", "left"),
                          ("中鍵", "middle"), ("右鍵", "right"),
                          ("側鍵1", "x1"), ("側鍵2", "x2")):
            tk.Radiobutton(type_frm, text=text, value=val, variable=self.var_type,
                           command=self._refresh, bg=PANEL, fg=TEXT, selectcolor=YELLOW,
                           activebackground=PANEL, activeforeground=RED,
                           font=F_N).pack(side="left", padx=2)
        self.key_row = tk.Frame(frm, bg=PANEL)
        self.key_row.grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        dark_label(self.key_row, "鍵盤按鍵：").pack(side="left")
        self.lbl_key = tk.Label(self.key_row, text="（未設定）", width=12, bg=PAPER,
                                fg=CYAN, font=F_B, relief="solid", bd=2)
        self.lbl_key.pack(side="left", padx=6)
        self.btn_capture = comic_button(self.key_row, "捕捉按鍵", self._start_capture, bg=YELLOW, fg=INK)
        self.btn_capture.pack(side="left")
        tk.Frame(frm, bg=INK, height=2).grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)
        dark_label(frm, "按住時間 (秒)：").grid(row=3, column=0, sticky="w", **pad)
        self.var_hold = tk.StringVar(value="0.02")
        dark_entry(frm, self.var_hold).grid(row=3, column=1, sticky="w", **pad)
        dark_label(frm, "按下後多久彈起", fg=SUB).grid(row=3, column=2, sticky="w")
        dark_label(frm, "之後延遲 (秒)：").grid(row=4, column=0, sticky="w", **pad)
        self.var_delay = tk.StringVar(value="0.02")
        dark_entry(frm, self.var_delay).grid(row=4, column=1, sticky="w", **pad)
        dark_label(frm, "多久後做下一步", fg=SUB).grid(row=4, column=2, sticky="w")
        btn_frm = tk.Frame(frm, bg=PANEL)
        btn_frm.grid(row=5, column=0, columnspan=3, pady=(14, 0))
        comic_button(btn_frm, "確定", self._on_ok, bg=GREEN).pack(side="left", padx=8)
        comic_button(btn_frm, "取消", self._on_cancel, bg=RED, fg=WHITE).pack(side="left", padx=8)
        if init:
            self._load(init)
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _load(self, step):
        if step["type"] == "mouse":
            self.var_type.set(step["button"])
        else:
            self.var_type.set("key")
            self.captured = (step["key_kind"], step["key_value"])
            self.lbl_key.config(text=step_action_text(step))
        self.var_hold.set(str(step["hold"]))
        self.var_delay.set(str(step["delay"]))

    def _refresh(self):
        self.btn_capture.config(state="normal" if self.var_type.get() == "key" else "disabled")

    def _start_capture(self):
        self.lbl_key.config(text="請按鍵…")
        self.capture_listener = KbListener(on_press=self._on_capture)
        self.capture_listener.daemon = True
        self.capture_listener.start()

    def _on_capture(self, key):
        kind, value = key_to_fields(key)
        if kind is None:
            self.after(0, lambda: self.lbl_key.config(text="此鍵無法辨識"))
        else:
            self.captured = (kind, value)
            self.after(0, lambda: self.lbl_key.config(text=fields_display(kind, value)))
        if self.capture_listener:
            self.capture_listener.stop()
            self.capture_listener = None
        return False

    def _on_ok(self):
        try:
            hold = float(self.var_hold.get())
            delay = float(self.var_delay.get())
            if hold < 0 or delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("設定錯誤", "按住時間與延遲必須是 0 或正數。", parent=self)
            return
        t = self.var_type.get()
        if t == "key":
            kind, value = self.captured
            if kind is None:
                messagebox.showerror("設定錯誤", "請先捕捉一個鍵盤按鍵。", parent=self)
                return
            step = {"type": "key", "key_kind": kind, "key_value": value}
        else:
            step = {"type": "mouse", "button": t}
        step["hold"] = hold
        step["delay"] = delay
        self.result = step
        self._cleanup()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self._cleanup()
        self.destroy()

    def _cleanup(self):
        if self.capture_listener:
            self.capture_listener.stop()
            self.capture_listener = None


# ===== 主視窗 =====
class TriggerApp:
    DEFAULT_HOLD = 0.02
    DEFAULT_DELAY = 0.02

    def __init__(self, root):
        self.root = root
        self.root.title("全自動多腳本觸發器")
        self._preload_theme()               # 開窗前先讀回上次選的主題，避免閃一下舊配色
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.kb = KbController()
        self.mouse = MouseController()

        self.scripts = []          # [{id,name,trigger,loop,steps}]
        self.runtime = {}          # id -> {"running":bool,"thread":..,"loop_limit":int}
        self.current = None        # 目前編輯中的腳本 dict
        self._next_id = 1
        self.armed = False         # 是否啟用觸發
        self.recording = False
        self.rec_kb = None
        self.rec_mouse = None
        self.capturing_trigger = False
        self.capturing_panic = False
        self.capturing_arm = False
        self.capturing_startall = False
        self.panic = dict(PANIC_DEFAULT)   # 全域緊急停止鍵（預設 F12）
        self.arm_key = dict(ARM_DEFAULT)   # 全域啟用/停用快捷鍵（預設 F9）
        self.startall_key = dict(STARTALL_DEFAULT)   # 全域一鍵全部啟動快捷鍵（預設 F8）

        # 自我觸發防護：最近送出的按鍵簽章
        self._emit_lock = threading.Lock()
        self._recent_emits = []    # [(sig, timestamp)]

        # 全域監聽（一直執行，靠 self.armed 控制是否生效）
        self.g_kb = KbListener(on_press=self._on_global_key)
        self.g_kb.daemon = True
        self.g_kb.start()
        self.g_mouse = MouseListener(on_click=self._on_global_click)
        self.g_mouse.daemon = True
        self.g_mouse.start()

        self._setup_style()
        self._build_ui()
        if not self._autoload():   # 啟動時自動載入上次設定
            self._add_script()     # 沒有設定檔才給一個預設空腳本
        self._refresh_panic_label()
        self._refresh_arm_label()
        self._refresh_startall_label()
        self._mini_on = False
        self._build_mini()         # 最小化時的浮動小視窗
        self.root.bind("<Unmap>", self._on_minimize)
        self.root.bind("<Map>", self._on_restore)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        for name in ("Manga.Treeview", "Script.Treeview"):
            style.configure(name, background=PANEL, fieldbackground=PANEL,
                            foreground=TEXT, rowheight=26, font=F_N, borderwidth=0)
        style.configure("Manga.Treeview.Heading", background=RED, foreground=WHITE,
                        font=F_B, relief="raised", borderwidth=2)
        style.configure("Script.Treeview.Heading", background=PURPLE, foreground=WHITE,
                        font=F_B, relief="raised", borderwidth=2)
        style.map("Manga.Treeview", background=[("selected", YELLOW)], foreground=[("selected", INK)])
        style.map("Script.Treeview", background=[("selected", CYAN)], foreground=[("selected", INK)])

    # ============================================================
    # 主題切換
    # ============================================================
    def _preload_theme(self):
        """開窗前，從設定檔讀回上次選的主題並套用（讀檔失敗就用預設）。"""
        try:
            path = settings_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("theme")
                if name in THEMES:
                    apply_theme(name)
        except Exception:
            pass   # 任何讀檔錯誤都不影響啟動，照預設主題開窗

    def _change_theme(self, name):
        """下拉選單切換主題：套色 → 重設 ttk 樣式 → 重建 UI 與浮窗 → 還原狀態 → 存檔。"""
        if name not in THEMES or name == CURRENT_THEME:
            return
        # 記住目前選取的腳本，重建後要還原
        keep_id = self.current["id"] if self.current else None

        apply_theme(name)
        self.root.configure(bg=BG)
        self._setup_style()          # ttk Treeview 樣式需用新色重新設定
        self._build_ui()             # 銷毀舊框架、用新色重建

        # 重建浮窗（避免殘留舊色）
        try:
            if getattr(self, "mini", None) is not None:
                self.mini.destroy()
        except Exception:
            pass
        self._build_mini()

        # 還原清單 / 編輯器 / 狀態列
        self._refresh_script_list(select_id=keep_id)
        if self.current:
            self._load_editor(self.current)
        self._refresh_panic_label()
        self._refresh_arm_label()
        self._sync_status_label()

        self.var_theme.set(name)
        self._autosave()             # 立即把主題選擇寫回設定檔

    def _sync_status_label(self):
        """依目前狀態刷新狀態列文字與顏色（重建 UI 後呼叫）。"""
        if self.armed:
            running = sum(1 for rt in self.runtime.values() if rt.get("running"))
            if running:
                self.lbl_status.config(text="● 已啟用！按各腳本觸發鍵開始/停止", fg=GREEN)
            else:
                self.lbl_status.config(text="● 已啟用 · 待命", fg=CYAN)
        else:
            self.lbl_status.config(text="● 未啟用（編輯模式）", fg=SUB)

    # ============================================================
    # 介面
    # ============================================================
    def _build_ui(self):
        # 可重複呼叫：換主題時先銷毀舊框架再重建，達成即時切換
        if getattr(self, "_main", None) is not None:
            self._main.destroy()
        root = tk.Frame(self.root, bg=BG, padx=14, pady=12)
        root.grid(row=0, column=0)
        self._main = root

        # 頂部列：左邊封面標題、右邊主題下拉選單
        top = tk.Frame(root, bg=BG)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top.columnconfigure(0, weight=1)

        # 美漫封面式標題條：彩底反色字 + 粗黑外框
        banner = tk.Label(top, text="★  多腳本觸發器  ★", bg=RED, fg=WHITE,
                          font=F_TITLE, bd=4, relief="raised", padx=14, pady=4,
                          highlightbackground=INK, highlightthickness=3)
        banner.grid(row=0, column=0, sticky="ew")

        # 主題切換區
        theme_box = tk.Frame(top, bg=BG)
        theme_box.grid(row=0, column=1, sticky="e", padx=(10, 0))
        dark_label(theme_box, "🎨 風格", fg=INK, font=F_B, bg=BG).pack(side="left", padx=(0, 4))
        self.var_theme = tk.StringVar(value=CURRENT_THEME)
        om = tk.OptionMenu(theme_box, self.var_theme, *THEMES.keys(),
                           command=self._change_theme)
        om.config(bg=PANEL, fg=TEXT, activebackground=YELLOW, activeforeground=INK,
                  font=F_B, relief="raised", bd=3, cursor="hand2",
                  highlightbackground=INK, highlightthickness=2, width=8)
        om["menu"].config(bg=PANEL, fg=TEXT, font=F_N,
                          activebackground=CYAN, activeforeground=WHITE)
        om.pack(side="left")

        # ---- 左欄：腳本清單 ----
        left = panel(root)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        dark_label(left, "腳本清單", fg=RED, font=F_H).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        self.slist = ttk.Treeview(left, columns=("name", "trig", "n", "st"), show="headings",
                                  height=11, style="Script.Treeview")
        for c, txt, w in (("name", "名稱", 90), ("trig", "觸發鍵", 90),
                          ("n", "步驟", 44), ("st", "狀態", 60)):
            self.slist.heading(c, text=txt)
            self.slist.column(c, width=w, anchor="center")
        self.slist.grid(row=1, column=0, columnspan=3, padx=8, pady=(0, 6))
        self.slist.bind("<<TreeviewSelect>>", self._on_select_script)
        comic_button(left, "✚ 新增腳本", self._add_script, bg=GREEN, width=10).grid(row=2, column=0, padx=4, pady=(0, 8))
        comic_button(left, "⧉ 複製", self._dup_script, bg=PURPLE, width=7).grid(row=2, column=1, padx=4, pady=(0, 8))
        comic_button(left, "✖ 刪除", self._del_script, bg=RED, fg=WHITE, width=7).grid(row=2, column=2, padx=4, pady=(0, 8))

        # ---- 右欄：腳本編輯器 ----
        right = panel(root)
        right.grid(row=1, column=1, sticky="nsew")
        self.editor = right

        er = tk.Frame(right, bg=PANEL)
        er.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        dark_label(er, "腳本名稱：", font=F_B).pack(side="left")
        self.var_name = tk.StringVar()
        self.var_name.trace_add("write", lambda *a: self._sync_name())
        dark_entry(er, self.var_name, width=14).pack(side="left", padx=4)

        tr = tk.Frame(right, bg=PANEL)
        tr.grid(row=1, column=0, sticky="w", padx=10, pady=2)
        dark_label(tr, "觸發鍵：", font=F_B).pack(side="left")
        self.lbl_trigger = tk.Label(tr, text="（未設定）", width=12, bg=PAPER,
                                    fg=CYAN, font=F_B, relief="solid", bd=2)
        self.lbl_trigger.pack(side="left", padx=6)
        self.btn_trig = comic_button(tr, "捕捉觸發鍵", self._capture_trigger, bg=YELLOW, fg=INK)
        self.btn_trig.pack(side="left")

        lr = tk.Frame(right, bg=PANEL)
        lr.grid(row=2, column=0, sticky="w", padx=10, pady=2)
        dark_label(lr, "循環次數：", font=F_B).pack(side="left")
        self.var_loop = tk.StringVar(value="0")
        self.var_loop.trace_add("write", lambda *a: self._sync_loop())
        dark_entry(lr, self.var_loop, width=6).pack(side="left", padx=4)
        dark_label(lr, "(0 = 無限)", fg=SUB).pack(side="left", padx=4)

        self.btn_record = comic_button(right, "●  錄製步驟  (Esc 結束)", self._toggle_record,
                                       bg=RED, fg=WHITE, font=(FONT, 11, "bold"))
        self.btn_record.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 4))

        steps_wrap = tk.Frame(right, bg=PANEL)
        steps_wrap.grid(row=4, column=0, padx=10, pady=(0, 8), sticky="w")
        self.tree = ttk.Treeview(steps_wrap, columns=("idx", "action", "hold", "delay"),
                                 show="headings", height=7, style="Manga.Treeview")
        for c, txt, w in (("idx", "#", 34), ("action", "動作", 130),
                          ("hold", "按住", 60), ("delay", "延遲", 60)):
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="center")
        self.tree.grid(row=0, column=0, rowspan=6)
        self.tree.bind("<Double-1>", lambda e: self._edit_step())
        for i, (txt, cmd, color) in enumerate([
            ("✚ 新增", self._add_step, CYAN), ("✎ 編輯", self._edit_step, CYAN),
            ("✖ 刪除", self._del_step, RED), ("▲ 上移", lambda: self._move(-1), PURPLE),
            ("▼ 下移", lambda: self._move(1), PURPLE), ("✦ 清空", self._clear_steps, RED),
        ]):
            comic_button(steps_wrap, txt, cmd, bg=color, fg=WHITE, width=7) \
                .grid(row=i, column=1, padx=(8, 0), pady=1, sticky="ew")

        sr = tk.Frame(right, bg=PANEL)
        sr.grid(row=5, column=0, sticky="w", padx=10, pady=(0, 8))
        comic_button(sr, "儲存全部", self._save, bg=CYAN).pack(side="left", padx=4)
        comic_button(sr, "讀取", self._load_file, bg=CYAN).pack(side="left", padx=4)

        # ---- 底部：緊急停止鍵 ----
        pr = tk.Frame(root, bg=BG)
        pr.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        dark_label(pr, "🛑 緊急停止鍵：", fg=RED, font=F_B, bg=BG).pack(side="left")
        self.lbl_panic = tk.Label(pr, text="F12", width=10, bg=PAPER,
                                   fg=RED, font=F_B, relief="solid", bd=2)
        self.lbl_panic.pack(side="left", padx=6)
        self.btn_panic = comic_button(pr, "捕捉", self._capture_panic, bg=YELLOW, fg=INK, width=6)
        self.btn_panic.pack(side="left")
        dark_label(pr, "（任何時候按下，立刻全部停止）", fg=SUB, bg=BG).pack(side="left", padx=8)

        # ---- 底部：啟用/停用 快捷鍵 ----
        ar = tk.Frame(root, bg=BG)
        ar.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        dark_label(ar, "⚡ 啟用/停用快捷鍵：", fg=GREEN, font=F_B, bg=BG).pack(side="left")
        self.lbl_armkey = tk.Label(ar, text="F9", width=10, bg=PAPER,
                                   fg=CYAN, font=F_B, relief="solid", bd=2)
        self.lbl_armkey.pack(side="left", padx=6)
        self.btn_armkey = comic_button(ar, "捕捉", self._capture_arm, bg=YELLOW, fg=INK, width=6)
        self.btn_armkey.pack(side="left")
        dark_label(ar, "（按一下=啟用，再按=停用）", fg=SUB, bg=BG).pack(side="left", padx=8)

        # ---- 底部：一鍵全部啟動 快捷鍵 ----
        sar = tk.Frame(root, bg=BG)
        sar.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        dark_label(sar, "🚀 一鍵全部啟動快捷鍵：", fg=CYAN, font=F_B, bg=BG).pack(side="left")
        self.lbl_startallkey = tk.Label(sar, text="F8", width=10, bg=PAPER,
                                        fg=CYAN, font=F_B, relief="solid", bd=2)
        self.lbl_startallkey.pack(side="left", padx=6)
        self.btn_startallkey = comic_button(sar, "捕捉", self._capture_startall, bg=YELLOW, fg=INK, width=6)
        self.btn_startallkey.pack(side="left")
        dark_label(sar, "（任何時候按下，立刻同時跑所有腳本）", fg=SUB, bg=BG).pack(side="left", padx=8)

        # ---- 底部：一鍵全部啟動 + 啟用 / 狀態 ----
        runrow = tk.Frame(root, bg=BG)
        runrow.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        runrow.columnconfigure(0, weight=1)
        runrow.columnconfigure(1, weight=1)
        # 一鍵啟動：同時跑所有有步驟的腳本；停止沿用緊急停止鍵 / 浮窗停止鈕
        self.btn_startall = comic_button(runrow, "🚀 一鍵全部啟動", self._start_all,
                                         bg=CYAN, font=(FONT, 12, "bold"))
        self.btn_startall.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_arm = comic_button(runrow, "🔴 啟用觸發 (Arm)", self._toggle_arm, bg=GREEN,
                                    font=(FONT, 12, "bold"))
        self.btn_arm.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.lbl_status = tk.Label(root, text="● 未啟用（編輯模式）", bg=BG, fg=SUB, font=(FONT, 11, "bold"))
        self.lbl_status.grid(row=6, column=0, columnspan=2)
        dark_label(root, "🚀 一鍵全部啟動＝同時跑所有腳本（按鈕或 F8 快捷鍵皆可，用緊急停止鍵全部停下）；Arm 啟用後可用各觸發鍵單獨開始/停止。編輯前請先停用。",
                   fg=SUB, bg=BG).grid(row=7, column=0, columnspan=2)

    # ============================================================
    # 腳本清單管理
    # ============================================================
    def _new_script_obj(self, name=None):
        sid = self._next_id
        self._next_id += 1
        return {"id": sid, "name": name or f"腳本{sid}", "trigger": None, "loop": "0", "steps": []}

    def _add_script(self):
        s = self._new_script_obj()
        self.scripts.append(s)
        self.runtime[s["id"]] = {"running": False, "thread": None, "loop_limit": 0, "loops_done": 0, "_last_ui": 0.0}
        self._refresh_script_list(select_id=s["id"])

    def _dup_script(self):
        if not self.current:
            return
        s = self._new_script_obj(name=self.current["name"] + "_複製")
        s["trigger"] = None     # 觸發鍵需重設，避免衝突
        s["loop"] = self.current["loop"]
        s["steps"] = [dict(st) for st in self.current["steps"]]
        self.scripts.append(s)
        self.runtime[s["id"]] = {"running": False, "thread": None, "loop_limit": 0, "loops_done": 0, "_last_ui": 0.0}
        self._refresh_script_list(select_id=s["id"])

    def _del_script(self):
        if not self.current:
            return
        sid = self.current["id"]
        if self.runtime.get(sid, {}).get("running"):
            self.runtime[sid]["running"] = False
        if not messagebox.askyesno("確認", f"確定刪除腳本「{self.current['name']}」？"):
            return
        self.scripts = [s for s in self.scripts if s["id"] != sid]
        self.runtime.pop(sid, None)
        self.current = None
        self._refresh_script_list()

    def _refresh_script_list(self, select_id=None):
        self.slist.delete(*self.slist.get_children())
        for s in self.scripts:
            rt = self.runtime.get(s["id"], {})
            st = f"● 執行中 ×{rt.get('loops_done', 0)}" if rt.get("running") else "○ 停止"
            self.slist.insert("", "end", iid=str(s["id"]),
                              values=(s["name"], trigger_display(s["trigger"]), len(s["steps"]), st))
        target = select_id if select_id is not None else (self.current["id"] if self.current else None)
        if target is not None and self.slist.exists(str(target)):
            self.slist.selection_set(str(target))
            self.slist.focus(str(target))
        elif self.scripts:
            first = str(self.scripts[0]["id"])
            self.slist.selection_set(first)
        else:
            self.current = None
            self._load_editor(None)

    def _script_by_id(self, sid):
        for s in self.scripts:
            if s["id"] == sid:
                return s
        return None

    def _on_select_script(self, event=None):
        sel = self.slist.selection()
        if not sel:
            return
        s = self._script_by_id(int(sel[0]))
        if s:
            self.current = s
            self._load_editor(s)

    # ============================================================
    # 編輯器
    # ============================================================
    def _load_editor(self, s):
        self._loading = True
        if s is None:
            self.var_name.set("")
            self.var_loop.set("0")
            self.lbl_trigger.config(text="（未設定）")
            self.tree.delete(*self.tree.get_children())
            self._loading = False
            return
        self.var_name.set(s["name"])
        self.var_loop.set(str(s.get("loop", "0")))
        self.lbl_trigger.config(text=trigger_display(s["trigger"]))
        self._refresh_steps()
        self._loading = False

    def _sync_name(self):
        if getattr(self, "_loading", False) or not self.current:
            return
        self.current["name"] = self.var_name.get()
        if self.slist.exists(str(self.current["id"])):
            self.slist.set(str(self.current["id"]), "name", self.current["name"])

    def _sync_loop(self):
        if getattr(self, "_loading", False) or not self.current:
            return
        self.current["loop"] = self.var_loop.get()

    def _refresh_steps(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current:
            return
        for i, s in enumerate(self.current["steps"], 1):
            self.tree.insert("", "end", values=(i, step_action_text(s), s["hold"], s["delay"]))
        if self.slist.exists(str(self.current["id"])):
            self.slist.set(str(self.current["id"]), "n", len(self.current["steps"]))

    def _selected_step_index(self):
        sel = self.tree.selection()
        return self.tree.index(sel[0]) if sel else None

    def _add_step(self):
        if not self.current:
            return
        dlg = StepDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result:
            self.current["steps"].append(dlg.result)
            self._refresh_steps()

    def _edit_step(self):
        if not self.current:
            return
        idx = self._selected_step_index()
        if idx is None:
            return
        dlg = StepDialog(self.root, init=self.current["steps"][idx])
        self.root.wait_window(dlg)
        if dlg.result:
            self.current["steps"][idx] = dlg.result
            self._refresh_steps()

    def _del_step(self):
        if not self.current:
            return
        idx = self._selected_step_index()
        if idx is None:
            return
        del self.current["steps"][idx]
        self._refresh_steps()

    def _move(self, direction):
        if not self.current:
            return
        idx = self._selected_step_index()
        if idx is None:
            return
        new = idx + direction
        steps = self.current["steps"]
        if 0 <= new < len(steps):
            steps[idx], steps[new] = steps[new], steps[idx]
            self._refresh_steps()
            self.tree.selection_set(self.tree.get_children()[new])

    def _clear_steps(self):
        if not self.current or not self.current["steps"]:
            return
        if messagebox.askyesno("確認", "清空此腳本的所有步驟？"):
            self.current["steps"] = []
            self._refresh_steps()

    # ============================================================
    # 捕捉觸發鍵（鍵盤或滑鼠）
    # ============================================================
    def _capture_trigger(self):
        if not self.current:
            return
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再設定。")
            return
        self.capturing_trigger = True
        self.lbl_trigger.config(text="請按鍵或點滑鼠…")
        # 暫時用一次性監聽捕捉（鍵盤 + 滑鼠）
        self._cap_kb = KbListener(on_press=self._on_trigger_capture_key)
        self._cap_kb.daemon = True
        self._cap_kb.start()
        self._cap_mouse = MouseListener(on_click=self._on_trigger_capture_click)
        self._cap_mouse.daemon = True
        self._cap_mouse.start()

    def _finish_trigger_capture(self, trigger):
        self.capturing_trigger = False
        for lsn in (getattr(self, "_cap_kb", None), getattr(self, "_cap_mouse", None)):
            try:
                if lsn:
                    lsn.stop()
            except Exception:
                pass
        self._cap_kb = self._cap_mouse = None
        if self.current is not None:
            self.current["trigger"] = trigger
            self.root.after(0, lambda: self.lbl_trigger.config(text=trigger_display(trigger)))
            self.root.after(0, lambda: self.slist.exists(str(self.current["id"])) and
                            self.slist.set(str(self.current["id"]), "trig", trigger_display(trigger)))

    def _on_trigger_capture_key(self, key):
        if not self.capturing_trigger:
            return False
        kind, value = key_to_fields(key)
        if kind is None:
            return False
        self._finish_trigger_capture({"type": "key", "key_kind": kind, "key_value": value})
        return False

    def _on_trigger_capture_click(self, x, y, button, pressed):
        if not self.capturing_trigger or not pressed:
            return
        # 只忽略「視窗內的左鍵」——那通常是點到捕捉鈕本身；
        # 中鍵/右鍵/側鍵則不論游標在哪都接受，側鍵才不會因為游標停在視窗上而抓不到
        if button.name == "left" and self._point_in_window(x, y):
            return
        if button.name not in DETECT_BUTTONS:
            return
        self._finish_trigger_capture({"type": "mouse", "button": button.name})
        return False

    # ============================================================
    # 緊急停止鍵（Panic Key，僅鍵盤）
    # ============================================================
    def _refresh_panic_label(self):
        self.lbl_panic.config(text=trigger_display(self.panic))

    def _capture_panic(self):
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再設定緊急停止鍵。")
            return
        self.capturing_panic = True
        self.lbl_panic.config(text="請按鍵…")
        self._cap_panic = KbListener(on_press=self._on_panic_capture_key)
        self._cap_panic.daemon = True
        self._cap_panic.start()

    def _on_panic_capture_key(self, key):
        if not self.capturing_panic:
            return False
        kind, value = key_to_fields(key)
        if kind is None:
            return False
        self.capturing_panic = False
        try:
            if getattr(self, "_cap_panic", None):
                self._cap_panic.stop()
        except Exception:
            pass
        self._cap_panic = None
        self.panic = {"type": "key", "key_kind": kind, "key_value": value}
        self.root.after(0, self._refresh_panic_label)
        return False

    def _panic_stop(self):
        """立即停止所有腳本並自動停用觸發。"""
        for rt in self.runtime.values():
            rt["running"] = False
        if self.armed:
            self._disarm()
        self.lbl_status.config(text="🛑 緊急停止！已全部停止", fg=RED)
        self.root.after(50, self._refresh_script_list)

    # ============================================================
    # 啟用/停用快捷鍵（Arm Hotkey，僅鍵盤）
    # ============================================================
    def _refresh_arm_label(self):
        self.lbl_armkey.config(text=trigger_display(self.arm_key))

    def _capture_arm(self):
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再設定快捷鍵。")
            return
        self.capturing_arm = True
        self.lbl_armkey.config(text="請按鍵…")
        self._cap_arm = KbListener(on_press=self._on_arm_capture_key)
        self._cap_arm.daemon = True
        self._cap_arm.start()

    def _on_arm_capture_key(self, key):
        if not self.capturing_arm:
            return False
        kind, value = key_to_fields(key)
        if kind is None:
            return False
        self.capturing_arm = False
        try:
            if getattr(self, "_cap_arm", None):
                self._cap_arm.stop()
        except Exception:
            pass
        self._cap_arm = None
        self.arm_key = {"type": "key", "key_kind": kind, "key_value": value}
        self.root.after(0, self._refresh_arm_label)
        return False

    # ============================================================
    # 一鍵全部啟動快捷鍵（Start-All Hotkey，僅鍵盤）
    # ============================================================
    def _refresh_startall_label(self):
        self.lbl_startallkey.config(text=trigger_display(self.startall_key))

    def _capture_startall(self):
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再設定快捷鍵。")
            return
        self.capturing_startall = True
        self.lbl_startallkey.config(text="請按鍵…")
        self._cap_startall = KbListener(on_press=self._on_startall_capture_key)
        self._cap_startall.daemon = True
        self._cap_startall.start()

    def _on_startall_capture_key(self, key):
        if not self.capturing_startall:
            return False
        kind, value = key_to_fields(key)
        if kind is None:
            return False
        self.capturing_startall = False
        try:
            if getattr(self, "_cap_startall", None):
                self._cap_startall.stop()
        except Exception:
            pass
        self._cap_startall = None
        self.startall_key = {"type": "key", "key_kind": kind, "key_value": value}
        self.root.after(0, self._refresh_startall_label)
        return False

    # ============================================================
    # 最小化浮動小視窗（Mini HUD）
    # ============================================================
    def _build_mini(self):
        """建立一個無邊框、永遠置頂的小浮窗：顯示狀態 + 快速停止/開啟。"""
        self.mini = tk.Toplevel(self.root)
        self.mini.withdraw()
        self.mini.overrideredirect(True)          # 無標題列
        self.mini.attributes("-topmost", True)    # 永遠置頂
        self.mini.configure(bg=INK)               # 外層黑邊
        wrap = tk.Frame(self.mini, bg=BG)
        wrap.pack(padx=3, pady=3)
        self.mini_status = tk.Label(wrap, text="○ 未啟用", bg=BG, fg=INK, font=F_B, padx=8)
        self.mini_status.pack(side="left")
        comic_button(wrap, "🛑 停止", self._panic_stop, bg=RED, fg=WHITE, width=7) \
            .pack(side="left", padx=3, pady=3)
        comic_button(wrap, "▣ 開啟", self._restore_main, bg=CYAN, fg=WHITE, width=6) \
            .pack(side="left", padx=(0, 3), pady=3)
        # 拖曳移動（綁在非按鈕區域）
        for w in (self.mini, wrap, self.mini_status):
            w.bind("<Button-1>", self._mini_press)
            w.bind("<B1-Motion>", self._mini_drag)

    def _mini_press(self, e):
        self._mini_dx = e.x_root - self.mini.winfo_x()
        self._mini_dy = e.y_root - self.mini.winfo_y()

    def _mini_drag(self, e):
        self.mini.geometry(f"+{e.x_root - self._mini_dx}+{e.y_root - self._mini_dy}")

    def _update_mini(self):
        running = sum(1 for rt in self.runtime.values() if rt.get("running"))
        if not self.armed:
            txt, fg = "○ 未啟用", SUB
        elif running:
            txt, fg = f"● 執行中 {running} 個", GREEN
        else:
            txt, fg = "● 已啟用 · 待命", CYAN
        self.mini_status.config(text=txt, fg=fg)

    def _on_minimize(self, event):
        # 只理會主視窗本身的最小化事件
        if event.widget is self.root and self.root.state() == "iconic":
            # 完全隱藏主視窗（避免被系統連同小浮窗一起隱藏），改由小浮窗待命
            self.root.withdraw()
            self._show_mini()

    def _on_restore(self, event):
        if event.widget is self.root:
            self._hide_mini()

    def _show_mini(self):
        self._mini_on = True
        self._update_mini()
        self.mini.deiconify()
        self.mini.lift()
        self.mini.attributes("-topmost", True)
        if not getattr(self, "_mini_placed", False):     # 第一次定位到右上角
            self.mini.update_idletasks()
            sw = self.mini.winfo_screenwidth()
            w = self.mini.winfo_width()
            self.mini.geometry(f"+{sw - w - 30}+30")
            self._mini_placed = True
        self._mini_tick()

    def _hide_mini(self):
        self._mini_on = False
        try:
            self.mini.withdraw()
        except Exception:
            pass

    def _mini_tick(self):
        # 顯示期間定時刷新狀態（含迴圈執行中的個數）
        if not self._mini_on:
            return
        self._update_mini()
        self.root.after(300, self._mini_tick)

    def _restore_main(self):
        self._hide_mini()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ============================================================
    # 錄製步驟（針對目前腳本）
    # ============================================================
    def _toggle_record(self):
        if self.recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        if not self.current:
            return
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再錄製。")
            return
        self.recording = True
        self.btn_record.config(text="■  結束錄製  (Esc)")
        self.lbl_status.config(text="● 錄製中… 你按的每個鍵都會被記下", fg=RED)
        self.rec_kb = KbListener(on_press=self._rec_on_key)
        self.rec_kb.daemon = True
        self.rec_kb.start()
        self.rec_mouse = MouseListener(on_click=self._rec_on_click)
        self.rec_mouse.daemon = True
        self.rec_mouse.start()

    def _stop_record(self):
        self.recording = False
        for lsn in (self.rec_kb, self.rec_mouse):
            try:
                if lsn:
                    lsn.stop()
            except Exception:
                pass
        self.rec_kb = self.rec_mouse = None
        self.btn_record.config(text="●  錄製步驟  (Esc 結束)")
        self.lbl_status.config(text="● 未啟用（編輯模式）", fg=SUB)
        self._refresh_steps()

    def _rec_on_key(self, key):
        if not self.recording or not self.current:
            return
        if key == Key.esc:
            self.root.after(0, self._stop_record)
            return
        kind, value = key_to_fields(key)
        if kind is None:
            return
        self.current["steps"].append({"type": "key", "key_kind": kind, "key_value": value,
                                      "hold": self.DEFAULT_HOLD, "delay": self.DEFAULT_DELAY})
        self.root.after(0, self._refresh_steps)

    def _rec_on_click(self, x, y, button, pressed):
        if not self.recording or not pressed or not self.current:
            return
        # 同捕捉邏輯：只擋視窗內的左鍵，側鍵/中右鍵一律記錄
        if button.name == "left" and self._point_in_window(x, y):
            return
        if button.name not in DETECT_BUTTONS:
            return
        self.current["steps"].append({"type": "mouse", "button": button.name,
                                      "hold": self.DEFAULT_HOLD, "delay": self.DEFAULT_DELAY})
        self.root.after(0, self._refresh_steps)

    def _point_in_window(self, x, y):
        try:
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            return rx <= x <= rx + w and ry <= y <= ry + h
        except Exception:
            return False

    # ============================================================
    # 啟用 / 停用觸發
    # ============================================================
    def _toggle_arm(self):
        if self.armed:
            self._disarm()
        else:
            self._arm()

    def _arm(self):
        # 檢查：至少要有一個腳本設定觸發鍵且有步驟
        usable = [s for s in self.scripts if s["trigger"] and s["steps"]]
        if not usable:
            messagebox.showinfo("提示", "至少需要一個腳本有設定觸發鍵且有步驟。")
            return
        # 檢查觸發鍵是否重複
        seen = {}
        for s in usable:
            key = json.dumps(s["trigger"], sort_keys=True)
            if key in seen:
                messagebox.showerror("觸發鍵重複",
                                     f"「{seen[key]}」與「{s['name']}」使用了相同的觸發鍵，請改掉其中一個。")
                return
            seen[key] = s["name"]
        # 檢查觸發鍵是否與緊急停止鍵衝突
        panic_key = json.dumps(self.panic, sort_keys=True)
        if panic_key in seen:
            messagebox.showerror("與緊急停止鍵衝突",
                                 f"腳本「{seen[panic_key]}」的觸發鍵與緊急停止鍵相同，請改掉其中一個。")
            return
        # 檢查觸發鍵 / 緊急鍵是否與啟用快捷鍵衝突
        arm_key = json.dumps(self.arm_key, sort_keys=True)
        if arm_key in seen:
            messagebox.showerror("與啟用快捷鍵衝突",
                                 f"腳本「{seen[arm_key]}」的觸發鍵與啟用/停用快捷鍵相同，請改掉其中一個。")
            return
        if arm_key == panic_key:
            messagebox.showerror("快捷鍵衝突",
                                 "啟用/停用快捷鍵與緊急停止鍵相同，請改掉其中一個。")
            return
        # 檢查一鍵全部啟動快捷鍵是否與其它鍵衝突
        startall_key = json.dumps(self.startall_key, sort_keys=True)
        if startall_key in seen:
            messagebox.showerror("與一鍵全部啟動快捷鍵衝突",
                                 f"腳本「{seen[startall_key]}」的觸發鍵與一鍵全部啟動快捷鍵相同，請改掉其中一個。")
            return
        if startall_key == panic_key:
            messagebox.showerror("快捷鍵衝突",
                                 "一鍵全部啟動快捷鍵與緊急停止鍵相同，請改掉其中一個。")
            return
        if startall_key == arm_key:
            messagebox.showerror("快捷鍵衝突",
                                 "一鍵全部啟動快捷鍵與啟用/停用快捷鍵相同，請改掉其中一個。")
            return
        if self.recording:
            self._stop_record()
        self.armed = True
        self.btn_arm.config(text="■ 停用觸發 (Disarm)", bg=RED, fg=WHITE)
        self.btn_arm._base_bg = RED
        self.lbl_status.config(text="● 已啟用！按各腳本觸發鍵開始/停止", fg=GREEN)

    def _disarm(self):
        self.armed = False
        for sid, rt in self.runtime.items():
            rt["running"] = False
        self.btn_arm.config(text="🔴 啟用觸發 (Arm)", bg=GREEN, fg=INK)
        self.btn_arm._base_bg = GREEN
        self.lbl_status.config(text="● 未啟用（編輯模式）", fg=SUB)
        self.root.after(50, self._refresh_script_list)

    # ============================================================
    # 全域觸發監聽
    # ============================================================
    def _on_global_key(self, key):
        # 捕捉中（觸發鍵 / 緊急鍵 / 快捷鍵）或錄製中交給各自流程處理
        if (self.capturing_trigger or self.capturing_panic or self.capturing_arm
                or self.capturing_startall or self.recording):
            return
        kind, value = key_to_fields(key)
        if kind is None:
            return
        # 緊急停止鍵：最高優先，且不受 armed 限制
        p = self.panic
        if p and p.get("type") == "key" and p["key_kind"] == kind and p["key_value"] == value:
            self.root.after(0, self._panic_stop)
            return
        # 啟用/停用快捷鍵：切換 Arm，不受 armed 限制
        a = self.arm_key
        if a and a.get("type") == "key" and a["key_kind"] == kind and a["key_value"] == value:
            self.root.after(0, self._toggle_arm)
            return
        # 一鍵全部啟動快捷鍵：同時跑所有腳本，不受 armed 限制
        sa = self.startall_key
        if sa and sa.get("type") == "key" and sa["key_kind"] == kind and sa["key_value"] == value:
            self.root.after(0, self._start_all)
            return
        if not self.armed:
            return
        if self._is_recent_emit(("key", kind, value)):
            return     # 自我觸發防護
        for s in self.scripts:
            tr = s.get("trigger")
            if tr and tr["type"] == "key" and tr["key_kind"] == kind and tr["key_value"] == value:
                self.root.after(0, lambda sid=s["id"]: self._toggle_script(sid))
                break

    def _on_global_click(self, x, y, button, pressed):
        if self.capturing_trigger or self.recording:
            return
        if not self.armed or not pressed:
            return
        if button.name not in DETECT_BUTTONS:
            return
        if self._is_recent_emit(("mouse", button.name)):
            return
        for s in self.scripts:
            tr = s.get("trigger")
            if tr and tr["type"] == "mouse" and tr["button"] == button.name:
                self.root.after(0, lambda sid=s["id"]: self._toggle_script(sid))
                break

    # ============================================================
    # 自我觸發防護
    # ============================================================
    def _note_emit(self, sig):
        with self._emit_lock:
            self._recent_emits.append((sig, time.time()))

    def _is_recent_emit(self, sig, window=0.08):
        now = time.time()
        with self._emit_lock:
            self._recent_emits = [(s, t) for (s, t) in self._recent_emits if now - t < 0.5]
            for (s, t) in self._recent_emits:
                if s == sig and now - t < window:
                    return True
        return False

    # ============================================================
    # 執行單一腳本（獨立執行緒）
    # ============================================================
    def _begin_script(self, sid):
        """啟動單一腳本（已在執行 / 無步驟則略過）；回傳是否真的有啟動。"""
        rt = self.runtime.get(sid)
        s = self._script_by_id(sid)
        if rt is None or s is None or rt["running"] or not s["steps"]:
            return False
        try:
            loop = int(str(s.get("loop", "0")))
            if loop < 0:
                loop = 0
        except ValueError:
            loop = 0
        rt["loop_limit"] = loop
        rt["loops_done"] = 0
        rt["_last_ui"] = 0.0
        rt["running"] = True
        rt["thread"] = threading.Thread(target=self._run_script, args=(sid,), daemon=True)
        rt["thread"].start()
        return True

    def _toggle_script(self, sid):
        rt = self.runtime.get(sid)
        s = self._script_by_id(sid)
        if rt is None or s is None:
            return
        if rt["running"]:
            rt["running"] = False
        else:
            self._begin_script(sid)
        self._refresh_script_list()

    def _start_all(self):
        """一鍵同時啟動所有「有步驟」的腳本（不需逐一按觸發鍵）。"""
        if self.recording or self.capturing_trigger:
            messagebox.showinfo("提示", "請先結束錄製 / 捕捉再啟動。")
            return
        started = sum(1 for s in self.scripts if self._begin_script(s["id"]))
        if started == 0:
            messagebox.showinfo("提示", "沒有可啟動的腳本（請確認腳本有步驟，或它們已在執行中）。")
            return
        self._refresh_script_list()
        self.lbl_status.config(text=f"🚀 一鍵啟動！同時執行 {started} 個腳本", fg=GREEN)

    def _update_run_count(self, sid):
        """節流更新清單狀態欄的迴圈計數，避免高頻刷新卡頓。"""
        rt = self.runtime.get(sid)
        if not rt or not rt.get("running"):
            return
        if self.slist.exists(str(sid)):
            self.slist.set(str(sid), "st", f"● 執行中 ×{rt['loops_done']}")

    def _run_script(self, sid):
        rt = self.runtime[sid]
        s = self._script_by_id(sid)
        loops = 0
        try:
            while rt["running"] and s is not None:
                for step in list(s["steps"]):
                    if not rt["running"]:
                        break
                    self._do_step(step, rt)
                loops += 1
                rt["loops_done"] = loops
                now = time.time()
                if now - rt.get("_last_ui", 0.0) >= 0.15:   # 節流：最快每 0.15 秒更新一次
                    rt["_last_ui"] = now
                    self.root.after(0, lambda sid=sid: self._update_run_count(sid))
                if rt["loop_limit"] > 0 and loops >= rt["loop_limit"]:
                    break
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("執行錯誤", f"腳本執行錯誤：\n{msg}"))
        finally:
            rt["running"] = False
            self.root.after(0, self._refresh_script_list)

    def _do_step(self, step, rt):
        if step["type"] == "mouse":
            btn = MOUSE_MAP.get(step["button"])
            if btn is None:
                # 此 pynput 版本不支援輸出該滑鼠鍵（通常是側鍵），略過避免整段崩潰
                self._sleep(step["delay"], rt)
                return
            self._note_emit(("mouse", step["button"]))
            self.mouse.press(btn)
            self._sleep(step["hold"], rt)
            self.mouse.release(btn)
        else:
            self._note_emit(("key", step["key_kind"], step["key_value"]))
            k = reconstruct_key_fields(step["key_kind"], step["key_value"])
            self.kb.press(k)
            self._sleep(step["hold"], rt)
            self.kb.release(k)
        self._sleep(step["delay"], rt)

    def _sleep(self, seconds, rt):
        end = time.time() + seconds
        while rt["running"]:
            remain = end - time.time()
            if remain <= 0:
                break
            time.sleep(min(0.02, remain))

    # ============================================================
    # 存 / 讀檔（全部腳本）+ 自動持久化
    # ============================================================
    def _serialize(self):
        """把目前所有腳本與緊急停止鍵打包成可存檔的 dict。"""
        return {
            "theme": CURRENT_THEME,        # 記住目前風格，下次啟動自動套用
            "panic": self.panic,
            "arm_key": self.arm_key,
            "startall_key": self.startall_key,
            "scripts": [{"name": s["name"], "trigger": s["trigger"],
                         "loop": s["loop"], "steps": s["steps"]} for s in self.scripts],
        }

    def _deserialize(self, data):
        """從 dict 還原腳本與緊急停止鍵；回傳是否有載入到任何腳本。"""
        self.scripts = []
        self.runtime = {}
        self._next_id = 1
        if isinstance(data.get("panic"), dict):
            self.panic = data["panic"]
        if isinstance(data.get("arm_key"), dict):
            self.arm_key = data["arm_key"]
        if isinstance(data.get("startall_key"), dict):
            self.startall_key = data["startall_key"]
        for item in data.get("scripts", []):
            s = self._new_script_obj(name=item.get("name"))
            s["trigger"] = item.get("trigger")
            s["loop"] = str(item.get("loop", "0"))
            s["steps"] = item.get("steps", [])
            self.scripts.append(s)
            self.runtime[s["id"]] = {"running": False, "thread": None, "loop_limit": 0,
                                     "loops_done": 0, "_last_ui": 0.0}
        self.current = None
        return bool(self.scripts)

    def _save(self):
        if not self.scripts:
            messagebox.showinfo("提示", "沒有腳本可儲存。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("觸發器設定", "*.json")], title="匯出全部腳本")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._serialize(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完成", "已匯出全部腳本。")
        except Exception as e:
            messagebox.showerror("儲存失敗", str(e))

    def _load_file(self):
        if self.armed:
            messagebox.showinfo("提示", "請先停用觸發再讀取。")
            return
        path = filedialog.askopenfilename(filetypes=[("觸發器設定", "*.json")], title="匯入腳本")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not self._deserialize(data):
                self._add_script()
            else:
                self._refresh_script_list(select_id=self.scripts[0]["id"])
            self._refresh_panic_label()
            self._refresh_arm_label()
            self._refresh_startall_label()
            messagebox.showinfo("完成", "已匯入腳本。")
        except Exception as e:
            messagebox.showerror("讀取失敗", str(e))

    def _autosave(self):
        """安靜地把目前設定寫入固定位置（關閉時呼叫）。"""
        try:
            with open(settings_path(), "w", encoding="utf-8") as f:
                json.dump(self._serialize(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass     # 自動存檔失敗不打擾使用者

    def _autoload(self):
        """啟動時嘗試載入上次設定；回傳是否成功載入到腳本。"""
        path = settings_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if self._deserialize(data):
                self._refresh_script_list(select_id=self.scripts[0]["id"])
                return True
        except Exception:
            pass
        return False

    # ============================================================
    def _on_close(self):
        self.armed = False
        for rt in self.runtime.values():
            rt["running"] = False
        self._autosave()           # 關閉前自動保存設定
        for lsn in (self.g_kb, self.g_mouse, self.rec_kb, self.rec_mouse):
            try:
                if lsn:
                    lsn.stop()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    TriggerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
# 多主題版本（含風格下拉選單，可即時切換並記住上次選擇）
# 已新增：一鍵全部啟動全域快捷鍵（預設 F8，可自訂）
