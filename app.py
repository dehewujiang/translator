"""翻译小弹窗 app.py
[INPUT] 用户复制的英文剪贴板文本（Ctrl+C 复制后，轻点一下 Ctrl 触发）
[OUTPUT] 小弹窗显示中文翻译，可一键复制译文
[POS] 前端弹窗层：调用 translator_core.translate_en_to_zh，不做翻译逻辑
[PROTOCOL] 启动隐藏 + Ctrl 轻点(<400ms)触发 + 800ms 防抖；翻译放线程，译好才弹窗；关窗口=藏后台，退出按钮才真正退出；点窗口外面立刻藏起；托盘图标常驻右下角
"""

import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

try:
    from translator_core import (
        translate_en_to_zh,
        lookup_word,
        is_single_word,
        load_config,
        save_config,
        load_profiles,
        save_profile,
        delete_profile,
        switch_profile,
        create_empty_profile,
        is_profile_configured,
    )
    CORE_OK = True
    CORE_ERR = ""
except Exception as e:  # 核心模块缺失时先不崩，等可用
    translate_en_to_zh = None
    lookup_word = None
    is_single_word = None
    load_config = None
    save_config = None
    load_profiles = None
    save_profile = None
    delete_profile = None
    switch_profile = None
    create_empty_profile = None
    is_profile_configured = None
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

FONT = ("微软雅黑", 10)
TITLE_FONT = ("微软雅黑", 9, "bold")
HINT_FG = "#666666"
WIN_W, WIN_H = 380, 410
DEBOUNCE_MS = 1200
TAP_MAX_MS = 400
SINGLETON_HOST = "127.0.0.1"
SINGLETON_PORT = 51237

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


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("英文翻译小助手")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self._place_top_right()
        self.root.attributes("-topmost", True)
        self.root.option_add("*Font", FONT)
        try:
            self.root.configure(background="#ffffff")
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
            style.configure("TFrame", background="#ffffff")
            style.configure("TLabel", background="#ffffff")
            style.configure("Status.TLabel", foreground=HINT_FG, background="#ffffff")
            style.configure("Title.TLabel", font=TITLE_FONT, foreground="#333333", background="#ffffff")
            style.configure("Accent.TButton", font=("微软雅黑", 10, "bold"), padding=(5, 2), background="#ffffff", bordercolor="#e0e0e0")
            style.configure("Small.TButton", font=("微软雅黑", 10), padding=(5, 2), background="#ffffff", bordercolor="#e0e0e0")
            style.map("Small.TButton", background=[("active", "#f2f2f2"), ("pressed", "#e8e8e8")])
            style.map("Accent.TButton", background=[("active", "#f2f2f2"), ("pressed", "#e8e8e8")])
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
        self._translating = False
        self.settings_win = None
        self.tray_icon = None

        # ---- 顶栏：左方案名 + 右配置，提示另起一行 ----
        topbar = ttk.Frame(self.root, style="TFrame")
        topbar.pack(fill="x", padx=10, pady=(8, 0))
        self.scheme_var = tk.StringVar(value="")
        ttk.Label(topbar, textvariable=self.scheme_var, style="Title.TLabel").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(topbar, text="配置", command=self.open_settings, width=6, takefocus=False, style="Small.TButton").pack(side="right")
        self.status_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel").pack(
            fill="x", padx=10, pady=(0, 4)
        )
        self._home_status()

        # ---- 原文 ----
        ttk.Label(self.root, text="原文", style="Title.TLabel").pack(anchor="w", padx=10, pady=(2, 0))
        self.src_text = tk.Text(self.root, height=5, font=FONT, wrap="word", relief="flat", borderwidth=0, highlightthickness=1, highlightbackground="#e8e8e8", highlightcolor="#e8e8e8", background="white")
        self.src_text.pack(fill="both", expand=True, padx=10)

        # ---- 译文 ----
        ttk.Label(self.root, text="译文", style="Title.TLabel").pack(anchor="w", padx=10, pady=(6, 0))
        self.dst_text = tk.Text(self.root, height=5, font=FONT, wrap="word", relief="flat", borderwidth=0, highlightthickness=1, highlightbackground="#e8e8e8", highlightcolor="#e8e8e8", background="white")
        self.dst_text.pack(fill="both", expand=True, padx=10)

        # ---- 按钮行：只留一排翻译相关 ----
        btns1 = ttk.Frame(self.root, style="TFrame")
        btns1.pack(fill="x", padx=10, pady=(10, 10))
        ttk.Button(btns1, text="翻译剪贴板", command=self.on_manual, takefocus=False, style="Small.TButton").pack(side="left", padx=(0, 2))
        ttk.Button(btns1, text="翻译输入", command=self.on_input, style="Accent.TButton", takefocus=False).pack(side="left", padx=2)
        ttk.Button(btns1, text="复制译文", command=self.on_copy, takefocus=False, style="Small.TButton").pack(side="left", padx=2)

        if not CORE_OK:
            self.dst_text.insert("1.0", "正在等待核心模块，请稍后再试（不要关闭）。")

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
            self.status_var.set(self.status_var.get() + "（无托盘图标）")
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
            self.status_var.set(self.status_var.get() + "（无托盘图标）")

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
            self.scheme_var.set(f"正在用：{cur}" if cur else "翻译小助手")
        except Exception:
            pass
        self.status_var.set("复制英文后点一下 Ctrl 就翻译")

    def on_hide(self):
        self.root.withdraw()
        self._home_status()

    def on_quit(self):
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
            self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+48")
        except Exception:
            pass

    def popup(self):
        self._place_top_right()
        try:
            if self.root.winfo_viewable():
                self.root.lift()
                try:
                    self.root.focus_force()
                except Exception:
                    pass
                return
        except Exception:
            pass
        self.root.deiconify()
        self._place_top_right()
        try:
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

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
            self.status_var.set("核心模块还没准备好，稍后再打开配置")
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
                self.keyboard_ok = True
            except Exception:
                self.keyboard_ok = False
        if not self.keyboard_ok:
            # 兜底：轮询剪贴板 + 手动按钮
            if CORE_OK:
                self.status_var.set("正在后台，点一下窗口里的翻译剪贴板也行")
            self.root.after(800, self._poll_clip)

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
        if self._translating:
            return
        text = self.read_clip()
        if not text or not text.strip():
            self.popup()
            self.status_var.set("剪贴板是空的，先复制一段英文")
            return
        self.last_clip = text
        short = text.strip()[:500]
        self.src_text.delete("1.0", "end")
        self.src_text.insert("1.0", short)
        self._run_translate(text.strip(), from_hotkey)

    def on_input(self):
        if self._translating:
            return
        text = self.src_text.get("1.0", "end").strip()
        if not text:
            self.status_var.set("上面框里先打字，再点翻译输入")
            return
        self._run_translate(text, False)

    def _run_translate(self, text, from_hotkey):
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", "翻译中，请稍等…")
        if not CORE_OK or translate_en_to_zh is None:
            self.popup()
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", "正在等待核心模块，请稍后再点一次。")
            return
        if self._need_config():
            self.popup()
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", "请先点下面的配置按钮，填好钥匙并保存，然后再翻译。")
            return
        if not from_hotkey:
            # 手动点的就直接显示；快捷键触发的等译好再弹
            self.popup()
        self._translating = True
        try:
            单词 = bool(is_single_word and is_single_word(text.strip()))
        except Exception:
            单词 = False
        if 单词 and lookup_word is not None:
            t = threading.Thread(target=self._do_lookup, args=(text.strip(),), daemon=True)
        else:
            t = threading.Thread(target=self._do_translate, args=(text.strip(),), daemon=True)
        t.start()

    def _do_lookup(self, text):
        try:
            结果 = lookup_word(text)
            self.root.after(0, self._show_dict, 结果)
        except Exception as e:
            原文 = str(e) or ""
            if 原文 and ("{" in 原文 or "word" in 原文):
                self.root.after(0, self._show_result, 原文)
            else:
                self.root.after(0, self._show_result, f"翻译失败：{e}")

    def _show_dict(self, 结果):
        self._translating = False
        try:
            self.dst_text.tag_config("词", font=("微软雅黑", 15, "bold"))
            self.dst_text.tag_config("音标", foreground="#666666")
            self.dst_text.tag_config("词性", font=("微软雅黑", 10, "bold"), foreground="#1a73e8")
            self.dst_text.tag_config("例句", foreground="#666666")
        except Exception:
            pass
        self.dst_text.delete("1.0", "end")
        try:
            词 = str(结果.get("word", "")).strip()
            英音 = str(结果.get("uk", "")).strip()
            美音 = str(结果.get("us", "")).strip()
            self.dst_text.insert("end", 词 + "  ", "词")
            音标行 = " ".join(p for p in [f"英 {英音}" if 英音 else "", f"美 {美音}" if 美音 else ""] if p)
            if 音标行:
                self.dst_text.insert("end", 音标行, "音标")
            self.dst_text.insert("end", "\n")
            序号 = 0
            for 义项 in (结果.get("senses", []) or []):
                词性 = str(义项.get("pos", "")).strip()
                意思 = [str(m).strip() for m in (义项.get("defs", []) or []) if str(m).strip()]
                if 词性 or 意思:
                    self.dst_text.insert("end", "\n" + (词性 + " " if 词性 else "") + "；".join(意思) + "\n", "词性" if 词性 else None)
                for 例 in (义项.get("examples", []) or []):
                    序号 += 1
                    英 = str(例.get("en", "")).strip()
                    中 = str(例.get("zh", "")).strip()
                    if 英:
                        self.dst_text.insert("end", f"例{序号} {英}\n", "例句")
                    if 中:
                        self.dst_text.insert("end", f"      {中}\n", "例句")
        except Exception:
            self.dst_text.delete("1.0", "end")
            self.dst_text.insert("1.0", str(结果))
        self.popup()

    def _do_translate(self, text):
        try:
            result = translate_en_to_zh(text)
        except Exception as e:
            result = f"翻译失败：{e}"
        try:
            self.root.after(0, self._show_result, result)
        except Exception:
            self._translating = False

    def _show_result(self, result):
        self._translating = False
        self.dst_text.delete("1.0", "end")
        self.dst_text.insert("1.0", result or "没有拿到翻译结果")
        # 译好了才弹出来
        self.popup()

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
            self.status_var.set("译文已复制，去别处粘贴就行")
        except Exception as e:
            self.status_var.set(f"复制失败：{e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    _acquire_singleton()
    try:
        App().run()
    finally:
        _release_singleton()
