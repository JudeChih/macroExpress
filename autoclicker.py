# -*- coding: utf-8 -*-
"""
全自動按鍵連點工具 (Auto Clicker)
--------------------------------------------------
功能：
  - 可指定要連點的「鍵盤按鍵」或「滑鼠按鍵（左/中/右）」
  - 可自訂連點間隔（毫秒）
  - 可自訂「啟動/停止」熱鍵，隨時開關不必回到視窗
  - 可設定點擊次數上限（0 = 無限）

技術：Python 標準庫 tkinter（GUI） + pynput（全域輸入監聽與模擬）
相依套件：pip install pynput
"""

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode, Listener as KeyboardListener
from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener


# ============================================================
# 工具函式：把 pynput 的按鍵物件轉成可顯示的文字
# ============================================================
def key_to_text(key) -> str:
    """將 pynput 按鍵物件轉為易讀字串。"""
    if key is None:
        return "（未設定）"
    if isinstance(key, Button):
        return {"left": "滑鼠左鍵", "middle": "滑鼠中鍵", "right": "滑鼠右鍵"}.get(key.name, f"滑鼠{key.name}")
    if isinstance(key, Key):
        return key.name.upper()                      # 特殊鍵，如 SPACE、F6
    if isinstance(key, KeyCode):
        return (key.char or f"<{key.vk}>").upper()   # 一般字元鍵
    return str(key)


class AutoClickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("全自動按鍵連點工具")
        self.root.resizable(False, False)

        # ---------- 控制器（模擬輸出） ----------
        self.kb_controller = KeyboardController()
        self.mouse_controller = MouseController()

        # ---------- 狀態 ----------
        self.running = False              # 是否正在連點
        self.click_thread = None          # 連點執行緒
        self.capturing = None             # 目前正在捕捉哪個欄位：'target' 或 'hotkey' 或 None

        # 預設目標：滑鼠左鍵；預設熱鍵：F6
        self.target_key = Button.left     # 可為 Button 或 Key / KeyCode
        self.hotkey = Key.f6

        # ---------- 全域監聽器（一直背景執行，負責熱鍵與捕捉） ----------
        self.kb_listener = KeyboardListener(on_press=self._on_global_key)
        self.kb_listener.daemon = True
        self.kb_listener.start()
        self.mouse_listener = None        # 捕捉滑鼠目標鍵時才暫時啟用

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============================================================
    # 介面
    # ============================================================
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self.root, padding=16)
        frm.grid(row=0, column=0)

        # --- 連點目標 ---
        ttk.Label(frm, text="連點目標：", font=("", 10, "bold")).grid(row=0, column=0, sticky="w", **pad)
        self.lbl_target = ttk.Label(frm, text=key_to_text(self.target_key), width=14,
                                    relief="solid", anchor="center")
        self.lbl_target.grid(row=0, column=1, **pad)
        self.btn_capture_target = ttk.Button(frm, text="捕捉按鍵", command=lambda: self._start_capture("target"))
        self.btn_capture_target.grid(row=0, column=2, **pad)

        # 快速選擇滑鼠鍵
        mouse_frm = ttk.Frame(frm)
        mouse_frm.grid(row=1, column=0, columnspan=3, sticky="w", padx=10)
        ttk.Label(mouse_frm, text="快速選滑鼠：").pack(side="left")
        for name, btn in (("左鍵", Button.left), ("中鍵", Button.middle), ("右鍵", Button.right)):
            ttk.Button(mouse_frm, text=name, width=6,
                       command=lambda b=btn: self._set_target(b)).pack(side="left", padx=3, pady=4)

        ttk.Separator(frm, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)

        # --- 連點間隔 ---
        ttk.Label(frm, text="連點間隔 (毫秒)：").grid(row=3, column=0, sticky="w", **pad)
        self.var_interval = tk.StringVar(value="100")
        ttk.Entry(frm, textvariable=self.var_interval, width=14).grid(row=3, column=1, **pad)
        ttk.Label(frm, text="數字越小越快").grid(row=3, column=2, sticky="w")

        # --- 次數上限 ---
        ttk.Label(frm, text="點擊次數上限：").grid(row=4, column=0, sticky="w", **pad)
        self.var_limit = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.var_limit, width=14).grid(row=4, column=1, **pad)
        ttk.Label(frm, text="0 = 無限").grid(row=4, column=2, sticky="w")

        ttk.Separator(frm, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="ew", pady=8)

        # --- 熱鍵 ---
        ttk.Label(frm, text="啟動/停止熱鍵：", font=("", 10, "bold")).grid(row=6, column=0, sticky="w", **pad)
        self.lbl_hotkey = ttk.Label(frm, text=key_to_text(self.hotkey), width=14,
                                    relief="solid", anchor="center")
        self.lbl_hotkey.grid(row=6, column=1, **pad)
        self.btn_capture_hotkey = ttk.Button(frm, text="捕捉熱鍵", command=lambda: self._start_capture("hotkey"))
        self.btn_capture_hotkey.grid(row=6, column=2, **pad)

        ttk.Separator(frm, orient="horizontal").grid(row=7, column=0, columnspan=3, sticky="ew", pady=8)

        # --- 啟動按鈕與狀態 ---
        self.btn_toggle = ttk.Button(frm, text="開始連點", command=self.toggle)
        self.btn_toggle.grid(row=8, column=0, columnspan=3, sticky="ew", **pad)

        self.lbl_status = ttk.Label(frm, text="● 已停止", foreground="#c0392b", font=("", 11, "bold"))
        self.lbl_status.grid(row=9, column=0, columnspan=3, **pad)

        self.lbl_hint = ttk.Label(frm, text="提示：按下熱鍵即可隨時開始 / 停止", foreground="#666")
        self.lbl_hint.grid(row=10, column=0, columnspan=3)

    # ============================================================
    # 捕捉按鍵 / 熱鍵
    # ============================================================
    def _start_capture(self, field: str):
        """進入捕捉模式：下一個按下的鍵盤鍵或滑鼠鍵會被記錄。"""
        self.capturing = field
        target_label = "目標" if field == "target" else "熱鍵"
        self.lbl_hint.config(text=f"請按下要當作【{target_label}】的鍵盤鍵或滑鼠鍵…", foreground="#2980b9")
        # 目標欄位允許捕捉滑鼠鍵，因此暫時啟用滑鼠監聽
        if field == "target" and self.mouse_listener is None:
            self.mouse_listener = MouseListener(on_click=self._on_global_click)
            self.mouse_listener.daemon = True
            self.mouse_listener.start()

    def _finish_capture(self, key):
        """完成捕捉，套用到對應欄位。回到 UI 執行緒更新。"""
        field = self.capturing
        self.capturing = None
        # 停掉暫時的滑鼠監聽
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None

        if field == "target":
            self.target_key = key
            self.root.after(0, lambda: self.lbl_target.config(text=key_to_text(key)))
        elif field == "hotkey":
            self.hotkey = key
            self.root.after(0, lambda: self.lbl_hotkey.config(text=key_to_text(key)))
        self.root.after(0, lambda: self.lbl_hint.config(
            text="提示：按下熱鍵即可隨時開始 / 停止", foreground="#666"))

    def _set_target(self, btn: Button):
        """快速選擇滑鼠鍵當作目標。"""
        self.target_key = btn
        self.lbl_target.config(text=key_to_text(btn))

    # ============================================================
    # 全域事件回呼
    # ============================================================
    def _on_global_key(self, key):
        """背景鍵盤監聽：負責捕捉模式與熱鍵偵測。"""
        if self.capturing:
            self._finish_capture(key)
            return
        if self.hotkey is not None and key == self.hotkey:
            # 切回 UI 執行緒處理，避免跨執行緒操作 tkinter
            self.root.after(0, self.toggle)

    def _on_global_click(self, x, y, button, pressed):
        """背景滑鼠監聽：僅在捕捉「目標」時使用。"""
        if pressed and self.capturing == "target":
            self._finish_capture(button)
            return False   # 捕捉到後即停止這個暫時監聽

    # ============================================================
    # 開始 / 停止
    # ============================================================
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.running:
            return
        # --- 輸入驗證（防呆） ---
        try:
            interval_ms = float(self.var_interval.get())
            if interval_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("設定錯誤", "連點間隔必須是 0 或正數（毫秒）。")
            return
        try:
            limit = int(self.var_limit.get())
            if limit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("設定錯誤", "點擊次數上限必須是 0 或正整數。")
            return
        if self.target_key is None:
            messagebox.showerror("設定錯誤", "請先設定要連點的目標按鍵。")
            return

        self.interval = interval_ms / 1000.0
        self.limit = limit
        self.running = True
        self._update_status(True)

        self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self.click_thread.start()

    def stop(self):
        self.running = False
        self._update_status(False)

    def _click_loop(self):
        """實際連點迴圈，於獨立執行緒執行。"""
        count = 0
        is_mouse = isinstance(self.target_key, Button)
        while self.running:
            try:
                if is_mouse:
                    self.mouse_controller.click(self.target_key)
                else:
                    self.kb_controller.press(self.target_key)
                    self.kb_controller.release(self.target_key)
            except Exception as e:
                # 模擬失敗時安全停止
                self.running = False
                self.root.after(0, lambda: messagebox.showerror("執行錯誤", f"連點時發生錯誤：\n{e}"))
                break

            count += 1
            if self.limit > 0 and count >= self.limit:
                self.running = False
                self.root.after(0, lambda: self._update_status(False))
                break
            time.sleep(self.interval)

    def _update_status(self, running: bool):
        if running:
            self.lbl_status.config(text="● 連點中…", foreground="#27ae60")
            self.btn_toggle.config(text="停止連點")
        else:
            self.lbl_status.config(text="● 已停止", foreground="#c0392b")
            self.btn_toggle.config(text="開始連點")

    # ============================================================
    # 關閉：確實清除監聽器與執行緒，避免資源殘留
    # ============================================================
    def _on_close(self):
        self.running = False
        try:
            if self.kb_listener is not None:
                self.kb_listener.stop()
            if self.mouse_listener is not None:
                self.mouse_listener.stop()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    AutoClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
