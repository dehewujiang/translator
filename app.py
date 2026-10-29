"""翻译小弹窗 app.py
[INPUT] 用户复制的英文剪贴板文本（Ctrl+C 复制后，轻点一下 Ctrl 触发）
[OUTPUT] 小弹窗显示中文翻译，可一键复制译文
[POS] 展示层/适配器：build_intent 把操作变成意图，run_intent 拿回结果，按类型渲染
[PROTOCOL] 启动隐藏 + Ctrl 轻点(<400ms)触发 + 1200ms 防抖；请求号+取消事件（新的顶掉旧的）；流式首段回来才弹窗；窗口高度按内容自适应；关窗口=藏后台，退出才真正退出；点外面立刻藏起；托盘常驻右下角
"""

import ctypes
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

try:
    from translator_core import run_intent
    from translator_settings import (
        load_config,
        save_config,
        load_profiles,
        save_profile,
        delete_profile,
        switch_profile,
        create_empty_profile,
        is_profile_configured,
    )
    from translator_domain import Definition, Failure, Translation, build_intent
    CORE_OK = True
    CORE_ERR = ""
except Exception as e:  # 核心模块缺失时先不崩，等可用
    run_intent = None
    load_config = None
    save_config = None
    load_profiles = None
    save_profile = None
    delete_profile = None
    switch_profile = None
    create_empty_profile = None
    is_profile_configured = None
    Definition = None
    Failure = None
    Translation = None
    build_intent = None
    CORE_OK = False
    CORE_ERR = str(e)

try:
    import pyperclip
    HAS_PYPERCLIP = True
except Exception:
    HAS_PYPERCLIP = False

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except Exception:
    HAS_PIL = False

try:
    import pystray
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False

HAS_TRAY = HAS_PYSTRAY and HAS_PIL

FONT = ("微软雅黑", 11)
SRC_FONT = ("微软雅黑", 10)
TITLE_FONT = ("微软雅黑", 10)
WORD_FONT = ("微软雅黑", 13, "bold")
PHON_FONT = ("微软雅黑", 10)
POS_FONT = ("微软雅黑", 10, "bold")
MAIN_FG = "#1B1B1B"
SUB_FG = "#616161"
FAINT_FG = "#8A8A8A"
LINE = "#EDEBE9"
CARD_BORDER = "#E1E1E1"
ROOT_BG = "#F3F3F3"
CARD_BG = "#FFFFFF"
ACCENT = "#0078D4"
ACCENT_HOVER = "#106EBE"
ACCENT_PRESS = "#005A9E"
DARK_BTN = ACCENT
HINT_FG = "#616161"
WIN_W, WIN_H = 380, 360
DEBOUNCE_MS = 1200
TAP_MAX_MS = 400
SINGLETON_HOST = "127.0.0.1"
SINGLETON_PORT = 51237
GA_ROOT = 2
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOACTIVATE_MOVE_SIZE = 0x13
VK_LBUTTON = 0x01
KEY_DOWN = 0x8000

_singleton_sock = None


def _notify_old_instance():
    """尽力通知旧进程把窗口顶出来，失败就忽略。"""
    try:
        c = socket.create_connection((SINGLETON_HOST, SINGLETON_PORT), timeout=1)
        try:
            c.sendall(b"SHOW")
        except Exception:
            pass
        try:
            c.close()
        except Exception:
            pass
    except Exception:
        pass


def _acquire_singleton():
    """单进程锁：bind 成功就是唯一实例；失败说明已在运行，顶出旧窗口后退出。"""
    global _singleton_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((SINGLETON_HOST, SINGLETON_PORT))
        s.listen(1)
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        _notify_old_instance()
        try:
            # 有显示环境就弹一句，没显示环境就静默退出
            r = tk.Tk()
            r.withdraw()
            try:
                messagebox.showinfo("翻译小助手", "已在运行，已帮你顶出旧窗口")
            finally:
                try:
                    r.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        sys.exit(0)
    _singleton_sock = s
    return s


def _release_singleton():
    global _singleton_sock
    try:
        if _singleton_sock is not None:
            _singleton_sock.close()
    except Exception:
        pass
    _singleton_sock = None


def _按钮(父, 文本, 命令, 主=False, 链接=False):
    if 链接:
        return tk.Button(
            父,
            text=文本,
            command=命令,
            relief="flat",
            bd=0,
            bg="#ffffff",
            fg="#616161",
            activebackground="#F3F3F3",
            activeforeground="#1B1B1B",
            font=("微软雅黑", 10),
            cursor="hand2",
            padx=6,
            pady=0,
            takefocus=0,
        )
    if 主:
        return tk.Button(
            父,
            text=文本,
            command=命令,
            relief="flat",
            bd=0,
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            font=("微软雅黑", 11),
            cursor="hand2",
            padx=10,
            pady=6,
            takefocus=0,
        )
    return tk.Button(
        父,
        text=文本,
        command=命令,
        relief="flat",
        bd=0,
        bg="#E8EAED",
        fg="#333333",
        activebackground="#D8DBDF",
        activeforeground="#111111",
        font=("微软雅黑", 10),
        cursor="hand2",
        padx=10,
        pady=4,
        takefocus=0,
    )


def _算原文高度(文本像素, 题高, 行高):
    """原文区 = 标题 + 6 + 文本 + 18 像素空隙；空文本至少留一行。"""
    return 题高 + 6 + max(int(文本像素), int(行高)) + 18


def _算窗口高度(源行数, 译文行数, 行高, 屏幕高):
    """按内容行数估算窗口高度，夹在最小高度和屏幕上限之间。"""
    固定高 = 132
    源高 = 24 + min(max(int(源行数), 1), 12) * 行高
    译文高 = 24 + min(max(int(译文行数), 1), 30) * 行高
    想要 = 固定高 + 源高 + 译文高
    上限 = max(WIN_H, min(int(屏幕高 * 0.72), 900))
    return max(WIN_H, min(想要, 上限))


def _make_tray_image():
    """64x64 蓝色圆底 + 白色译字，不依赖外部图片文件。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 61, 61], fill=(30, 120, 255, 255))
    try:
        # 中文用微软雅黑，找不到就用默认字体
        font = ImageFont.truetype("msyh.ttc", 30)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    try:
        d.text((32, 33), "译", fill="white", anchor="mm", font=font)
    except Exception:
        d.text((22, 18), "译", fill="white", font=font)
    return img


class _Tip:
    """跟鼠标的小提示：图标旁边浮一句，移开或 1.5 秒后就没。"""
    def __init__(self, 根):
        self._根 = 根
        self._窗 = None
        self._after = None

    def show(self, 文本, x, y):
        self.hide()
        try:
            w = tk.Toplevel(self._根)
            w.overrideredirect(True)
            w.attributes("-topmost", True)
            tk.Label(
                w, text=文本, font=("微软雅黑", 9),
                foreground="#323130", background="#FFFFFF",
                relief="solid", borderwidth=1, padx=6, pady=2,
            ).pack()
            w.geometry(f"+{int(x) + 14}+{int(y) + 12}")
            self._窗 = w
            self._after = self._根.after(1500, self.hide)
        except Exception:
            self._窗 = None

    def hide(self):
        try:
            if self._after is not None:
                try:
                    self._根.after_cancel(self._after)
                except Exception:
                    pass
                self._after = None
        except Exception:
            pass
        窗, self._窗 = self._窗, None
        try:
            if 窗 is not None:
                窗.destroy()
        except Exception:
            pass


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("英文翻译小助手")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self._window_h = WIN_H
        self._place_top_right()
        self.root.attributes("-topmost", True)
        self.root.option_add("*Font", FONT)
        try:
            self.root.configure(background=ROOT_BG)
        except Exception:
            pass
        try:
            style = ttk.Style()
            for theme in ("clam", "vista", "xpnative"):
                try:
                    style.theme_use(theme)
                    break
                except Exception:
                    continue
            style.configure("TFrame", background=ROOT_BG)
            style.configure("TLabel", background=ROOT_BG, foreground=SUB_FG)
            style.configure("Card.TFrame", background=CARD_BG)
            style.configure("Card.TLabel", background=CARD_BG, foreground=SUB_FG)
            style.configure("Status.TLabel", foreground=SUB_FG, background=ROOT_BG)
            style.configure("Title.TLabel", font=TITLE_FONT, foreground=FAINT_FG, background=CARD_BG)
        except Exception:
            pass
        # 启动就藏到后台，不打扰
        self.root.withdraw()
        # 点右上角叉只藏起来，不退出
        self.root.protocol("WM_DELETE_WINDOW", self.on_hide)
        # 点窗口外面就立刻藏起（无延迟）
        self.root.bind("<FocusOut>", self._on_focus_out)

        self.last_trigger = 0.0
        self.last_clip = ""
        self.keyboard_ok = False
        self._ctrl_down_t = None
        self._ctrl_combo = False
        self._request_id = 0
        self._cancel_event = None
        self._popup_on_first_chunk = False
        self._outside_watch = False
        self._mouse_was_down = False
        self._press_outside = False
        self._source_expanded = False
        self._source_compact_lines = 3
        self.settings_win = None
        self.tray_icon = None

        # ---- 状态条平时不占地方：有字才冒出来 ----
        self.status_var = tk.StringVar(value="")
        self._status_after = None
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("微软雅黑", 9),
            foreground=SUB_FG,
            background=ROOT_BG,
        )
        self._tip = _Tip(self.root)
        self._home_status()

        # ---- 译文（上）+ 原文（下）：译文优先，中间细线可拖动手调 ----
        body = ttk.Frame(self.root, style="Card.TFrame")
        body.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        pane_dst = ttk.Frame(body, style="Card.TFrame")
        pane_dst.pack(fill="both", expand=True)
        dst_head = ttk.Frame(pane_dst, style="Card.TFrame")
        dst_head.pack(fill="x", padx=12, pady=(10, 2))
        self.copy_btn = _按钮(dst_head, "⧉", self.on_copy, 链接=True)
        try:
            self.copy_btn.configure(font=("微软雅黑", 11))
        except Exception:
            pass
        self.copy_btn.pack(side="right")
        self.copy_btn.bind("<Enter>", lambda e: self._tip_show("复制译文", e))
        self.copy_btn.bind("<Leave>", self._tip_hide)
        self.dst_text = tk.Text(
            pane_dst,
            height=5,
            font=FONT,
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            background=CARD_BG,
            foreground=MAIN_FG,
            spacing1=4,
            spacing2=2,
            spacing3=6,
            padx=4,
            pady=2,
        )
        self.dst_text.pack(fill="both", expand=True, padx=12)

        # 可拖动的细分隔线：平时 1px 淡线，鼠标上去变深，拖它调两边高度
        self.divider = tk.Frame(body, background=CARD_BG, height=9, cursor="sb_v_double_arrow")
        self.divider.pack(fill="x")
        self.div_line = tk.Frame(self.divider, background=LINE, height=1)
        self.div_line.pack(fill="x", pady=4)
        for 部件 in (self.divider, self.div_line):
            部件.bind("<Enter>", self._div_hover_in)
            部件.bind("<Leave>", self._div_hover_out)
            部件.bind("<ButtonPress-1>", self._div_start)
            部件.bind("<B1-Motion>", self._div_drag)
        self._div_y = None
        self._div_acc = 0.0

        pane_src = ttk.Frame(body, style="Card.TFrame")
        pane_src.pack(fill="x")
        src_head = ttk.Frame(pane_src, style="Card.TFrame")
        src_head.pack(fill="x", padx=12, pady=(6, 0))
        self.expand_btn = _按钮(src_head, "▾", self._toggle_source, 链接=True)
        try:
            self.expand_btn.configure(font=("微软雅黑", 11))
        except Exception:
            pass
        self.expand_btn.pack(side="right")
        self.expand_btn.bind("<Enter>", lambda e: self._tip_show(
            "收起原文" if self._source_expanded else "展开原文", e))
        self.expand_btn.bind("<Leave>", self._tip_hide)
        self.src_text = tk.Text(
            pane_src,
            height=3,
            font=SRC_FONT,
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            background=CARD_BG,
            foreground=SUB_FG,
            spacing1=2,
            spacing2=2,
            spacing3=2,
            padx=4,
            pady=2,
        )
        self.src_text.pack(fill="x", padx=12, pady=(0, 10))
        self.src_text.bind("<MouseWheel>", lambda 事件: self._滚轮(self.src_text, 事件))
        self.src_text.bind("<Return>", self._on_src_return)
        self.dst_text.bind("<MouseWheel>", lambda 事件: self._滚轮(self.dst_text, 事件))

        # ---- 按钮行：蓝色主按钮 + 描边齿轮（等高，Fluent 命令栏） ----
        btns1 = ttk.Frame(self.root, style="TFrame")
        btns1.pack(fill="x", padx=12, pady=(8, 12))
        self._btns = btns1
        btns1.columnconfigure(0, weight=1)
        btns1.columnconfigure(1, weight=0)
        _按钮(btns1, "翻译", self.on_manual, 主=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        self.config_btn = tk.Button(
            btns1,
            text="⚙",
            command=self.open_settings,
            relief="flat",
            bd=0,
            bg=CARD_BG,
            fg="#616161",
            activebackground="#EDEBE9",
            activeforeground="#1B1B1B",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            highlightcolor=CARD_BORDER,
            font=("微软雅黑", 13),
            cursor="hand2",
            padx=10,
            pady=3,
            takefocus=0,
        )
        self.config_btn.grid(row=0, column=1, sticky="ns")
        self.config_btn.bind("<Enter>", lambda e: self._tip_show("配置", e))
        self.config_btn.bind("<Leave>", self._tip_hide)

        if not CORE_OK:
            self.dst_text.insert("1.0", "正在等待核心模块，请稍后再试（不要关闭）。")

        # 初始 360 高可能装不下新字体的 chrome：启动就一次兜底，免得按钮行被挤没
        self._ensure_fits()
        self._place_top_right()

        self._start_trigger()
        self._start_tray()
        self._start_singleton_server()

    # ---------- 点外面立刻藏起 ----------
    def _is_config_open(self):
        try:
            return (
                self.settings_win is not None
                and self.settings_win.winfo_exists()
            )
        except Exception:
            return False

    def _on_focus_out(self, _event=None):
        # 立刻藏起，不加延迟
        try:
            if not self.root.winfo_viewable():
                return  # 本来就藏着，不管
        except Exception:
            return
        # 配置窗口开着时不藏，免得填着东西窗口没了
        if self._is_config_open():
            return
        # 焦点还在主窗口里面的子控件之间转，不藏
        try:
            f = self.root.focus_get()
            if f is not None:
                try:
                    if f.winfo_toplevel() is self.root:
                        return
                except Exception:
                    pass
        except Exception:
            pass
        self.on_hide()

    # ---------- 托盘图标 ----------
    def _start_tray(self):
        if not HAS_TRAY:
            self._home_status()
            self._say_transient("无托盘图标，窗口照常用")
            return
        try:
            image = _make_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._tray_show, default=True),
                pystray.MenuItem("退出", self._tray_quit),
            )
            self.tray_icon = pystray.Icon(
                "翻译小助手", image, "英文翻译小助手", menu
            )
            t = threading.Thread(target=self.tray_icon.run, daemon=True)
            t.start()
        except Exception:
            self.tray_icon = None
            self._home_status()
            self._say_transient("无托盘图标，窗口照常用")

    def _start_singleton_server(self):
        def _serve():
            srv = _singleton_sock
            if srv is None:
                return
            while True:
                try:
                    conn, _ = srv.accept()
                except Exception:
                    return
                try:
                    try:
                        conn.recv(16)
                    except Exception:
                        pass
                    try:
                        self.root.after(0, self.popup)
                    except Exception:
                        pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        t = threading.Thread(target=_serve, daemon=True)
        t.start()

    def _tray_show(self, _icon=None, _item=None):
        # 托盘线程里调，要回到主线程弹窗口
        try:
            self.root.after(0, self.popup)
        except Exception:
            pass

    def _tray_quit(self, _icon=None, _item=None):
        try:
            self.root.after(0, self.on_quit)
        except Exception:
            pass

    # ---------- 藏 / 退 ----------
    def _home_status(self):
        try:
            data = load_profiles()
            cur = data.get("current", "")
        except Exception:
            cur = ""
        try:
            self.root.title(f"英文翻译小助手 · {cur}" if cur else "英文翻译小助手")
        except Exception:
            pass
        try:
            旧 = getattr(self, "_status_after", None)
            if 旧 is not None:
                try:
                    self.root.after_cancel(旧)
                except Exception:
                    pass
                self._status_after = None
        except Exception:
            pass
        self.status_var.set("")
        self._status_hide()

    def _status_show(self):
        """有字才占地方：把状态条插到按钮行上面。"""
        try:
            if self.status_label.winfo_ismapped():
                return
            按钮行 = getattr(self, "_btns", None)
            if 按钮行 is not None:
                self.status_label.pack(fill="x", padx=16, pady=(0, 4), before=按钮行)
            else:
                self.status_label.pack(fill="x", padx=16, pady=(0, 4))
        except Exception:
            pass

    def _status_hide(self):
        try:
            self.status_label.pack_forget()
        except Exception:
            pass

    def _status_hide_and_clear(self):
        try:
            self.status_var.set("")
        except Exception:
            pass
        self._status_hide()

    def _tip_show(self, 文本, 事件):
        try:
            self._tip.show(文本, 事件.x_root, 事件.y_root)
        except Exception:
            pass

    def _tip_hide(self, _事件=None):
        try:
            self._tip.hide()
        except Exception:
            pass

    def _say_transient(self, 文本):
        """平时安静：冒一句小字，2 秒后自己消失。"""
        try:
            旧 = getattr(self, "_status_after", None)
            if 旧 is not None:
                try:
                    self.root.after_cancel(旧)
                except Exception:
                    pass
        except Exception:
            pass
        self.status_var.set(文本)
        self._status_show()
        try:
            self._status_after = self.root.after(2000, self._status_hide_and_clear)
        except Exception:
            self._status_after = None

    def on_hide(self):
        self._outside_watch = False
        self._tip_hide()
        self.root.withdraw()
        self._home_status()

    def on_quit(self):
        self._tip_hide()
        if self._cancel_event is not None:
            self._cancel_event.set()
        try:
            if HAS_KEYBOARD:
                keyboard.unhook_all()
        except Exception:
            pass
        try:
            if self.tray_icon is not None:
                self.tray_icon.stop()
        except Exception:
            pass
        self.tray_icon = None
        _release_singleton()
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _place_top_right(self):
        try:
            sw = self.root.winfo_screenwidth()
            x = max(0, sw - WIN_W - 24)
            self.root.geometry(f"{WIN_W}x{self._window_h}+{x}+48")
        except Exception:
            pass

    def _refit(self):
        # 窗口刚显示时 update_idletasks 拿不到真实宽高，必须先跑一次 update
        try:
            self.root.update()
        except Exception:
            pass
        self._fit_window_height()
        try:
            self.root.update()
        except Exception:
            pass
        self._auto_split()
        # _auto_split 改完原文框高度后，实际需要的高度可能超过窗口：再兜一次底
        try:
            旧高 = self._window_h
            self._ensure_fits()
            if self._window_h > 旧高:
                self._place_top_right()
                self.root.update()
        except Exception:
            pass

    def _toggle_source(self):
        self._source_expanded = not self._source_expanded
        try:
            self.expand_btn.configure(text="▴" if self._source_expanded else "▾")
        except Exception:
            pass
        self._refit()

    def _fit_window_height(self):
        try:
            self.root.update_idletasks()
            行高 = tkfont.Font(font=FONT).metrics("linespace")
            屏高 = self.root.winfo_screenheight()
            源行 = self._source_compact_lines
            if self._source_expanded:
                源行 = min(self._pane_lines(self.src_text), 10)
            self._window_h = _算窗口高度(
                源行,
                self._pane_lines(self.dst_text),
                行高,
                屏高,
            )
            self._ensure_fits()
            self._place_top_right()
        except Exception:
            pass

    def _ensure_fits(self):
        """窗口实际高度至少装下 chrome（按钮行）：不够就长高到请求高度（封顶）。"""
        try:
            self.root.update_idletasks()
            需要 = int(self.root.winfo_reqheight())
            屏高 = int(self.root.winfo_screenheight())
            上限 = max(WIN_H, min(int(屏高 * 0.72), 900))
            if 需要 > self._window_h:
                self._window_h = min(需要, 上限)
        except Exception:
            pass

    def _is_foreground(self):
        try:
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), GA_ROOT)
            return ctypes.windll.user32.GetForegroundWindow() == hwnd
        except Exception:
            return False

    def _show_no_activate(self):
        try:
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), GA_ROOT)
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        except Exception:
            self.root.deiconify()

    def _raise_no_activate(self):
        try:
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), GA_ROOT)
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOACTIVATE_MOVE_SIZE
            )
        except Exception:
            pass

    def _pointer_inside(self):
        try:
            x, y = self.root.winfo_pointerxy()
            left = self.root.winfo_rootx()
            top = self.root.winfo_rooty()
            return (
                left <= x < left + self.root.winfo_width()
                and top <= y < top + self.root.winfo_height()
            )
        except Exception:
            return True

    def _start_outside_watch(self):
        if self._outside_watch:
            return
        self._outside_watch = True
        try:
            self._mouse_was_down = bool(
                ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & KEY_DOWN
            )
        except Exception:
            self._mouse_was_down = False
        self._press_outside = False
        try:
            self.root.after(80, self._watch_outside_click)
        except Exception:
            self._outside_watch = False

    def _watch_outside_click(self):
        if not self._outside_watch:
            return
        try:
            if not self.root.winfo_viewable():
                self._outside_watch = False
                return
            down = bool(
                ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & KEY_DOWN
            )
            if down and not self._mouse_was_down:
                self._press_outside = not self._pointer_inside()
            if self._mouse_was_down and not down:
                if (
                    self._press_outside
                    and not self._is_config_open()
                    and not self._is_foreground()
                    and not self._pointer_inside()
                ):
                    self._outside_watch = False
                    self.on_hide()
                    return
            self._mouse_was_down = down
        except Exception:
            self._outside_watch = False
            return
        try:
            self.root.after(80, self._watch_outside_click)
        except Exception:
            self._outside_watch = False

    def popup(self):
        # 直接顶出来的路径不经过 _refit：先保证窗口装得下按钮行
        self._ensure_fits()
        self._place_top_right()
        try:
            if self.root.winfo_viewable():
                if self._is_foreground():
                    self.root.lift()
                    try:
                        self.root.focus_force()
                    except Exception:
                        pass
                else:
                    self._raise_no_activate()
                self._start_outside_watch()
                return
        except Exception:
            pass
        if self._is_foreground():
            self.root.deiconify()
            self._place_top_right()
            try:
                self.root.lift()
                self.root.focus_force()
            except Exception:
                pass
        else:
            self._show_no_activate()
            self._place_top_right()
            self._raise_no_activate()
        self._start_outside_watch()

    # ---------- 配置小窗（左列表 + 右详情） ----------
    def open_settings(self):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            try:
                self.settings_win.lift()
                self.settings_win.focus_force()
            except Exception:
                pass
            return
        if load_profiles is None:
            self._say_transient("核心模块还没准备好，稍后再打开配置")
            return
        win = tk.Toplevel(self.root)
        self.settings_win = win
        win.title("配置")
        win.geometry("620x480")
        win.attributes("-topmost", True)
        win.option_add("*Font", FONT)
        self._refreshing_list = False
        self._prof_names = []

        left = ttk.Frame(win, width=180)
        left.pack(side="left", fill="y", padx=(10, 4), pady=10)
        try:
            left.pack_propagate(False)
        except Exception:
            pass
        ttk.Label(left, text="方案（点一下就换）", style="Title.TLabel").pack(anchor="w")
        self.prof_list = tk.Listbox(left, font=FONT, exportselection=False)
        self.prof_list.pack(fill="both", expand=True, pady=(4, 6))
        self.prof_list.bind("<<ListboxSelect>>", lambda _e: self._on_profile_selected())
        ttk.Button(left, text="+ 新方案", command=self._settings_add).pack(fill="x")

        right = ttk.Frame(win)
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        ttk.Label(right, text="地址").pack(anchor="w")
        self.s_url_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.s_url_var).pack(fill="x")
        ttk.Label(right, text="如 https://api.deepseek.com/v1", foreground="gray").pack(anchor="w")

        ttk.Label(right, text="钥匙").pack(anchor="w", pady=(6, 0))
        self.s_key_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.s_key_var, show="*").pack(fill="x")
        ttk.Label(right, text="去官网申请，粘贴到这里", foreground="gray").pack(anchor="w")

        ttk.Label(right, text="模型").pack(anchor="w", pady=(6, 0))
        self.s_model_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.s_model_var).pack(fill="x")
        ttk.Label(right, text="如 deepseek-flash，照文档抄", foreground="gray").pack(anchor="w")

        ttk.Label(right, text="翻译要求（想让它怎么翻就怎么写）").pack(anchor="w", pady=(6, 0))
        self.s_prompt_text = tk.Text(right, height=5, font=FONT, wrap="word")
        self.s_prompt_text.pack(fill="x")

        self.s_hint_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.s_hint_var, wraplength=400).pack(
            fill="x", pady=(4, 0)
        )

        row = ttk.Frame(right)
        row.pack(fill="x", pady=8)
        ttk.Button(row, text="保存", command=self._settings_save).pack(side="left", padx=2)
        ttk.Button(row, text="删除", command=self._settings_delete).pack(side="left", padx=2)

        self._refresh_settings_list()

    def _selected_profile_name(self):
        try:
            sel = self.prof_list.curselection()
        except Exception:
            return ""
        if not sel:
            return ""
        idx = sel[0]
        try:
            return self._prof_names[idx]
        except Exception:
            return ""

    def _refresh_settings_list(self, select_name=""):
        try:
            data = load_profiles()
        except Exception as e:
            self.s_hint_var.set(f"读配置失败：{e}")
            return
        names = list(data["profiles"].keys())
        cur = data.get("current", "")
        self._refreshing_list = True
        try:
            self.prof_list.delete(0, "end")
            self._prof_names = list(names)
            pick = 0
            for i, name in enumerate(names):
                try:
                    configured = is_profile_configured(name, data) if is_profile_configured else True
                except Exception:
                    configured = True
                if not configured:
                    label = f"{name} 未配置"
                elif name == cur:
                    label = f"{name} ✓正在用"
                else:
                    label = name
                self.prof_list.insert("end", label)
                if name == (select_name or cur):
                    pick = i
            if names:
                self.prof_list.selection_clear(0, "end")
                self.prof_list.selection_set(pick)
                self.prof_list.see(pick)
        finally:
            self._refreshing_list = False
        self._fill_settings_fields()

    def _fill_settings_fields(self):
        name = (self._selected_profile_name() or "").strip()
        if not name:
            return
        try:
            data = load_profiles()
        except Exception:
            return
        prof = data["profiles"].get(name)
        if prof is None:
            return
        self.s_url_var.set(prof.get("base_url", ""))
        self.s_key_var.set(prof.get("api_key", ""))
        self.s_model_var.set(prof.get("model", ""))
        self.s_prompt_text.delete("1.0", "end")
        self.s_prompt_text.insert("1.0", prof.get("prompt", ""))

    def _settings_add(self):
        try:
            name = simpledialog.askstring("新方案", "请起个新名字，比如：备用", parent=self.settings_win)
        except Exception:
            name = None
        if name is None:
            return
        name = (name or "").strip()
        if not name:
            self.s_hint_var.set("先起个名字才能新增。")
            return
        if create_empty_profile is None:
            self.s_hint_var.set("核心模块还没准备好，稍后再试。")
            return
        try:
            create_empty_profile(name)
            self._refresh_settings_list(select_name=name)
            self._fill_settings_fields()
            self.s_hint_var.set(f"已新建：{name}，右边填好点保存，保存好才能用。现在用的还是原来的，没动。")
        except Exception as e:
            self.s_hint_var.set(str(e))

    def _settings_save(self):
        name = self._selected_profile_name().strip()
        if not name:
            self.s_hint_var.set("先在左边点一个方案再保存。")
            return
        url = self.s_url_var.get().strip()
        key = self.s_key_var.get().strip()
        model = self.s_model_var.get().strip()
        if not url or not key or not model:
            self.s_hint_var.set("地址钥匙模型三样都要填好才能保存，差一样都用不了。")
            return
        try:
            save_profile(
                name,
                key,
                url,
                model,
                self.s_prompt_text.get("1.0", "end").strip(),
            )
            switch_profile(name)
            self._refresh_settings_list(select_name=name)
            self._home_status()
            self.s_hint_var.set(f"已保存并正在用：{name}。")
        except Exception as e:
            self.s_hint_var.set(str(e))

    def _on_profile_selected(self):
        if getattr(self, "_refreshing_list", False):
            return
        name = self._selected_profile_name().strip()
        if not name:
            return
        try:
            data = load_profiles()
            configured = is_profile_configured(name, data) if is_profile_configured else True
        except Exception:
            configured = True
        if not configured:
            self._fill_settings_fields()
            self.s_hint_var.set("这套还没填好，右边填好点保存，保存好才开始用。现在用的还是原来的。")
            return
        try:
            switch_profile(name)
            self._fill_settings_fields()
            self._home_status()
            self.s_hint_var.set(f"已换到：{name}，直接就能用。")
            self._refresh_settings_list(select_name=name)
        except Exception as e:
            self.s_hint_var.set(str(e))

    def _settings_delete(self):
        name = self._selected_profile_name().strip()
        if not name:
            self.s_hint_var.set("先在左边点一个方案再删除。")
            return
        try:
            cur = delete_profile(name)
            self._refresh_settings_list(select_name=cur)
            self.s_hint_var.set(f"已删除：{name}，现在用的是：{cur}。")
            self._home_status()
        except Exception as e:
            self.s_hint_var.set(str(e))

    # ---------- 剪贴板 ----------
    def read_clip(self):
        try:
            if HAS_PYPERCLIP:
                return pyperclip.paste() or ""
        except Exception:
            pass
        try:
            return self.root.clipboard_get()
        except Exception:
            return ""

    # ---------- 触发 ----------
    def _start_trigger(self):
        if HAS_KEYBOARD:
            try:
                keyboard.on_press_key("ctrl", self._on_ctrl_down, suppress=False)
                keyboard.on_release_key("ctrl", self._on_ctrl_up, suppress=False)
                keyboard.on_press(self._on_any_key, suppress=False)
                try:
                    keyboard.add_hotkey("alt+q", self._hotkey_summon, suppress=False)
                except Exception:
                    pass
                self.keyboard_ok = True
            except Exception:
                self.keyboard_ok = False
        if not self.keyboard_ok:
            # 兜底：轮询剪贴板 + 手动按钮
            if CORE_OK:
                self.status_var.set("正在后台，点一下窗口里的翻译也行")
                self._status_show()
            self.root.after(800, self._poll_clip)

    def _hotkey_summon(self):
        try:
            self.root.after(0, self._summon_and_focus)
        except Exception:
            pass

    def _summon_and_focus(self):
        """Alt+Q 调出：窗口顶到前面，光标落进原文框并全选，打字即替换。"""
        self.popup()
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
        try:
            self.src_text.focus_set()
            self.src_text.tag_add("sel", "1.0", "end-1c")
            self.src_text.mark_set("insert", "end-1c")
            self.src_text.see("insert")
        except Exception:
            pass

    def _on_src_return(self, _事件=None):
        """原文框里回车 = 点翻译，不用碰鼠标；Shift+回车仍换行。"""
        self.on_input()
        return "break"

    def _on_ctrl_down(self, _e):
        self._ctrl_down_t = time.time()
        self._ctrl_combo = False

    def _on_any_key(self, e):
        try:
            name = (getattr(e, "name", "") or "").lower()
        except Exception:
            return
        if self._ctrl_down_t is None:
            return
        if name not in ("ctrl", "left ctrl", "right ctrl", ""):
            self._ctrl_combo = True

    def _on_ctrl_up(self, _e):
        if self._ctrl_down_t is None:
            return
        held = (time.time() - self._ctrl_down_t) * 1000
        self._ctrl_down_t = None
        if held > TAP_MAX_MS:
            return
        try:
            if getattr(self, "_ctrl_combo", False):
                return
            if keyboard.is_pressed("c") or keyboard.is_pressed("v") or keyboard.is_pressed("x"):
                return
        except Exception:
            pass
        now = time.time() * 1000
        if now - self.last_trigger < DEBOUNCE_MS:
            return
        self.last_trigger = now
        self.root.after(0, lambda: self.on_manual(from_hotkey=True))

    def _poll_clip(self):
        try:
            cur = self.read_clip()
            if cur and cur != self.last_clip:
                self.last_clip = cur  # 只记录，不自动翻译，等用户点按钮
        except Exception:
            pass
        self.root.after(800, self._poll_clip)

    # ---------- 翻译 ----------
    def _need_config(self):
        if not CORE_OK or load_config is None:
            return False
        try:
            cfg = load_config()
        except Exception:
            return True
        return not (cfg.get("api_key") or "").strip()

    def on_manual(self, from_hotkey=False):
        text = self.read_clip()
        if not from_hotkey:
            # 点按钮：框里有自己打的字就翻框里的，不被剪贴板覆盖
            框里 = self.src_text.get("1.0", "end").strip()
            if 框里 and 框里 != (text or "").strip():
                self.on_input()
                return
        if not text or not text.strip():
            # 剪贴板是空的就退而求其次：翻原文框里打的字
            if self.src_text.get("1.0", "end").strip():
                self.on_input()
                return
            self.popup()
            self._say_transient("先复制英文，或在下面打字再点翻译")
            return
        self.last_clip = text
        short = text.strip()[:500].rstrip("\n") + "\n"
        self.src_text.delete("1.0", "end")
        self.src_text.insert("1.0", short)
        self.src_text.see("1.0")
        self._run_translate(text.strip(), from_hotkey)

    def on_input(self):
        text = self.src_text.get("1.0", "end").strip()
        if not text:
            self._say_transient("下面原文框里先打字，再点翻译")
            return
        self._run_translate(text, False)

    def _run_translate(self, text, from_hotkey):
        self._request_id += 1
        本号 = self._request_id
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._cancel_event = None
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", "翻译中，请稍等…")
        if not CORE_OK or run_intent is None:
            self.popup()
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", "正在等待核心模块，请稍后再点一次。")
            return
        if self._need_config():
            self.popup()
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", "请先点右上角的配置按钮，填好钥匙并保存，然后再翻译。")
            return
        取消 = threading.Event()
        self._cancel_event = 取消
        self._popup_on_first_chunk = bool(from_hotkey)
        if not from_hotkey:
            # 手动点的就直接显示；快捷键触发的等第一段字回来再弹
            self.popup()
        self.status_var.set("正在翻译…")
        意图 = build_intent(text)
        t = threading.Thread(
            target=self._do_intent, args=(意图, 本号, 取消), daemon=True
        )
        t.start()

    def _do_intent(self, 意图, 请求号, 取消):
        def 收到片段(文本):
            try:
                self.root.after(0, self._show_stream, 请求号, 文本)
            except Exception:
                pass

        try:
            结果 = run_intent(意图, on_chunk=收到片段, cancel=取消.is_set)
        except Exception as e:
            结果 = Failure("unknown", f"翻译失败：{e}")
        try:
            self.root.after(0, self._finish_intent, 请求号, 结果)
        except Exception:
            pass

    def _show_stream(self, 请求号, 文本):
        if 请求号 != self._request_id:
            return
        if self._popup_on_first_chunk:
            self._popup_on_first_chunk = False
            self.popup()
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", 文本)
        self.dst_text.see("1.0")

    def _finish_intent(self, 请求号, 结果):
        if 请求号 != self._request_id:
            return
        self._popup_on_first_chunk = False
        self._show_result(结果)
        self._home_status()

    def _show_dict(self, 结果):
        try:
            self.dst_text.tag_config("词", font=WORD_FONT, foreground=MAIN_FG)
            self.dst_text.tag_config("音标", font=PHON_FONT, foreground=FAINT_FG)
            self.dst_text.tag_config("词性", font=POS_FONT, foreground=ACCENT)
            self.dst_text.tag_config("释义", font=FONT, foreground=MAIN_FG)
            self.dst_text.tag_config("例英", font=SRC_FONT, foreground="#323130", lmargin1=16, lmargin2=16)
            self.dst_text.tag_config("例中", font=SRC_FONT, foreground=SUB_FG, lmargin1=16, lmargin2=16)
        except Exception:
            pass
        self.dst_text.delete("1.0", "end")
        try:
            词 = str(结果.word).strip()
            英音 = str(结果.uk).strip()
            美音 = str(结果.us).strip()
            self.dst_text.insert("end", 词 + "  ", "词")
            音标行 = " ".join(p for p in [f"英 {英音}" if 英音 else "", f"美 {美音}" if 美音 else ""] if p)
            if 音标行:
                self.dst_text.insert("end", 音标行, "音标")
            self.dst_text.insert("end", "\n\n")
            序号 = 0
            for 义项 in (结果.senses or []):
                词性 = str(义项.get("pos", "")).strip()
                意思 = [str(m).strip() for m in (义项.get("defs", []) or []) if str(m).strip()]
                if 词性 or 意思:
                    if 词性:
                        self.dst_text.insert("end", 词性 + " ", "词性")
                    if 意思:
                        self.dst_text.insert("end", "；".join(意思), "释义")
                    self.dst_text.insert("end", "\n")
                for 例 in (义项.get("examples", []) or []):
                    序号 += 1
                    英 = str(例.get("en", "")).strip()
                    中 = str(例.get("zh", "")).strip()
                    if 英:
                        self.dst_text.insert("end", f"例{序号}  {英}\n", "例英")
                    if 中:
                        self.dst_text.insert("end", f"       {中}\n", "例中")
                self.dst_text.insert("end", "\n")
        except Exception:
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", str(结果))
        self._source_expanded = False
        self._source_compact_lines = 1
        try:
            self.expand_btn.configure(text="▾")
        except Exception:
            pass
        self.dst_text.see("1.0")
        self.popup()
        self._refit()

    def _滚轮(self, widget, 事件):
        try:
            widget.yview_scroll(int(-事件.delta / 120), "units")
        except Exception:
            pass
        return "break"

    def _pane_lines(self, widget):
        try:
            got = widget.count("1.0", "end", "displaylines")
            n = got[0] if isinstance(got, tuple) else int(got)
            return max(1, n)
        except Exception:
            try:
                return max(1, len(widget.get("1.0", "end").splitlines()))
            except Exception:
                return 1

    def _auto_split(self):
        """按内容定原文框占几行，剩下的全给译文。"""
        try:
            if self._source_expanded:
                源行 = min(self._pane_lines(self.src_text), 10)
            else:
                源行 = self._source_compact_lines
            self.src_text.configure(height=max(1, min(int(源行), 12)))
        except Exception:
            pass

    def _div_hover_in(self, _事件=None):
        try:
            self.div_line.configure(background="#B3D7F5")
        except Exception:
            pass

    def _div_hover_out(self, _事件=None):
        try:
            self.div_line.configure(background=LINE)
        except Exception:
            pass

    def _div_start(self, 事件):
        try:
            self._div_y = float(事件.y_root)
        except Exception:
            self._div_y = None
        self._div_acc = 0.0

    def _div_drag(self, 事件):
        """往下拉分隔线 → 译文变大、原文变小；反之亦然。只管当前这一次。"""
        if self._div_y is None:
            return
        try:
            行高 = tkfont.Font(font=SRC_FONT).metrics("linespace")
            self._div_acc += float(事件.y_root) - self._div_y
            self._div_y = float(事件.y_root)
            整行 = int(self._div_acc / 行高)
            if 整行 == 0:
                return
            self._div_acc -= 整行 * 行高
            现在 = int(self.src_text.cget("height"))
            新高 = min(12, max(1, 现在 - 整行))
            if 新高 != 现在:
                self.src_text.configure(height=新高)
        except Exception:
            pass

    def _show_text(self, 文本):
        self._source_compact_lines = 3
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", 文本 or "没有拿到翻译结果")
        self.dst_text.see("1.0")
        # 先弹出来再分：藏着时量不到高，自动分会被跳过
        self.popup()
        self._refit()

    def _show_failure(self, 失败):
        原文兜底 = str(失败.raw or "").strip()
        self._show_text(原文兜底 or 失败.message)

    def _show_result(self, 结果):
        if isinstance(结果, Failure):
            self._show_failure(结果)
        elif isinstance(结果, Definition):
            self._show_dict(结果)
        elif isinstance(结果, Translation):
            self._show_text(结果.text)
        else:
            self._show_text(str(结果) if 结果 is not None else "")

    def on_copy(self):
        data = self.dst_text.get("1.0", "end").strip()
        if not data:
            return
        try:
            if HAS_PYPERCLIP:
                pyperclip.copy(data)
            else:
                self.root.clipboard_clear()
                self.root.clipboard_append(data)
            self._say_transient("译文已复制，去别处粘贴就行")
        except Exception as e:
            self._say_transient(f"复制失败：{e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    _acquire_singleton()
    try:
        App().run()
    finally:
        _release_singleton()
