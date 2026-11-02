"""配置窗：左列表选方案、右详情填地址钥匙模型与提示词。

[INPUT] App 实例（self：settings_win、prof_list、s_* 等状态全挂在它身上）。
[OUTPUT] 620 宽、最小 560 高的配置小窗（小屏自动收提示词框行数）；保存/删除/切换直接写配置。
[POS] 展示层；被 app.App 混入（class App(SettingsWindowMixin)）；只读 translator_settings 与 translator_theme，不反向依赖 app。
[PROTOCOL] 方法一字不改从 app.py 搬入；self 指调用方 App 实例。
"""

import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    from translator_settings import (
        load_profiles,
        save_profile,
        delete_profile,
        switch_profile,
        create_empty_profile,
        is_profile_configured,
    )
except Exception:
    load_profiles = None
    save_profile = None
    delete_profile = None
    switch_profile = None
    create_empty_profile = None
    is_profile_configured = None

try:
    from translator_provider import chat as _接口chat
except Exception:
    _接口chat = None

from translator_scale import px
from translator_theme import (
    FONT,
    SRC_FONT,
    LBL_FONT,
    MAIN_FG,
    SUB_FG,
    FAINT_FG,
    LINE,
    CARD_BG,
    ACCENT,
    ACCENT_HOVER,
    HOVER_BG,
    EDGE,
    PAGE_BG,
    SELECT_BG,
    SELECT_FG_ACCENT,
    SECONDARY_HOVER,
    ACCENT_TEXT,
    ERROR_FG,
    DARK,
    _make_primary_button_image,
    _make_secondary_button_image,
)


class SettingsWindowMixin:
    """配置窗整坨：打开、列表、回填、新增、保存、切换、删除。"""

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
        页底 = PAGE_BG
        原色键 = None
        if DARK:
            # 主窗的色键会让新窗口的标题栏变不了深色：建窗前摘掉，设完立刻恢复
            try:
                原色键 = self.root.wm_attributes("-transparentcolor")
                self.root.wm_attributes("-transparentcolor", "")
            except Exception:
                原色键 = None
        try:
            win = tk.Toplevel(self.root)
            self.settings_win = win
            win.title("配置")
            win.geometry(f"{px(620)}x{px(480)}")
            try:
                win.resizable(False, False)
            except Exception:
                pass
            if DARK:
                win.update()
                self._apply_dark_titlebar(win)
        finally:
            if 原色键:
                try:
                    self.root.wm_attributes("-transparentcolor", 原色键)
                except Exception:
                    pass

        try:
            win.protocol("WM_DELETE_WINDOW", lambda: self._settings_close(win))
        except Exception:
            pass
        win.attributes("-topmost", True)
        win.configure(bg=页底)
        win.option_add("*Font", FONT)
        self._refreshing_list = False
        self._refreshing_fields = False
        self._s_dirty = False
        self._prof_names = []

        left = tk.Frame(win, bg=页底, width=px(212))
        left.pack(side="left", fill="y")
        try:
            left.pack_propagate(False)
        except Exception:
            pass
        tk.Frame(win, width=1, bg=LINE).pack(side="left", fill="y")

        tk.Label(
            left, text="方案（点一下就换）", font=SRC_FONT, fg=SUB_FG, bg=页底,
            anchor="w",
        ).pack(fill="x", padx=px(20), pady=(px(18), px(8)))
        list_wrap = tk.Frame(
            left, bg=CARD_BG, bd=0,
            highlightthickness=1, highlightbackground=EDGE, highlightcolor=ACCENT,
        )
        list_wrap.pack(fill="both", expand=True, padx=px(20), pady=(0, px(8)))
        self.prof_list = tk.Listbox(
            list_wrap, font=FONT, bd=0, relief="flat",
            highlightthickness=0, bg=CARD_BG, fg=MAIN_FG,
            selectbackground=SELECT_BG, selectforeground=MAIN_FG,
            selectborderwidth=0,
            activestyle="none", exportselection=False,
        )
        self.prof_list.pack(fill="both", expand=True, padx=px(6), pady=px(4))
        self.prof_list.bind("<<ListboxSelect>>", self._on_list_select)

        def _bind_hover(btn, imgs):
            def on_enter(_e=None):
                try:
                    btn.configure(image=imgs.get("hover", imgs.get("normal")))
                except Exception:
                    pass

            def on_leave(_e=None):
                try:
                    btn.configure(image=imgs.get("normal"))
                except Exception:
                    pass

            def on_press(_e=None):
                try:
                    btn.configure(image=imgs.get("press", imgs.get("normal")))
                except Exception:
                    pass

            def on_release(_e=None):
                try:
                    btn.configure(image=imgs.get("hover", imgs.get("normal")))
                except Exception:
                    pass

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            btn.bind("<ButtonPress-1>", on_press)
            btn.bind("<ButtonRelease-1>", on_release)

        try:
            self._s_add_imgs = {
                k: _make_secondary_button_image(k, 148, 32)
                for k in ("normal", "hover", "press")
            }
        except Exception:
            self._s_add_imgs = {}
        add_btn = tk.Button(
            left, text="+ 新方案", command=self._settings_add,
            image=self._s_add_imgs.get("normal"), compound="center",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            takefocus=0, bg=页底, fg=MAIN_FG,
            activebackground=页底, activeforeground=MAIN_FG,
            font=FONT, width=px(148), height=px(32), padx=0, pady=0,
        )
        if not self._s_add_imgs:
            try:
                add_btn.configure(image="", bg=HOVER_BG, activebackground="#E6E9EF")
            except Exception:
                pass
        add_btn.pack(fill="x", padx=px(20), pady=(0, px(16)))
        _bind_hover(add_btn, self._s_add_imgs)

        right = tk.Frame(win, bg=CARD_BG)
        right.pack(side="left", fill="both", expand=True)
        body = tk.Frame(right, bg=CARD_BG)
        body.pack(fill="both", expand=True, padx=px(20), pady=px(16))

        self.s_hint_var = tk.StringVar(value="")
        row = tk.Frame(body, bg=CARD_BG)
        row.pack(side="bottom", fill="x", pady=(px(12), 0))
        hint_stat = tk.Label(
            body, textvariable=self.s_hint_var, font=SRC_FONT, fg=SUB_FG,
            bg=CARD_BG, anchor="w", justify="left", wraplength=px(356),
        )
        hint_stat.pack(side="bottom", fill="x", pady=(px(6), 0))

        def _recolor_hint(*_a):
            try:
                v = self.s_hint_var.get()
                hint_stat.configure(
                    fg=ERROR_FG if v.startswith("读配置失败") else SUB_FG
                )
            except Exception:
                pass

        try:
            self.s_hint_var.trace_add("write", _recolor_hint)
        except Exception:
            pass

        def 字段名(text):
            return tk.Label(
                body, text=text, font=SRC_FONT, fg=SUB_FG, bg=CARD_BG, anchor="w"
            )

        def 提示(text):
            return tk.Label(
                body, text=text, font=LBL_FONT, fg=FAINT_FG, bg=CARD_BG, anchor="w"
            )

        def 输入框(var, show=None, parent=None):
            e = tk.Entry(
                parent if parent is not None else body,
                textvariable=var, font=FONT, relief="flat", bd=0,
                highlightthickness=1, highlightbackground=EDGE, highlightcolor=ACCENT,
                bg=CARD_BG, fg=MAIN_FG, insertbackground=MAIN_FG,
            )
            if show:
                e.configure(show=show)
            return e

        字段名("地址").pack(fill="x")
        self.s_url_var = tk.StringVar()
        输入框(self.s_url_var).pack(fill="x", pady=(px(4), 0), ipady=px(4))
        提示("如 https://api.deepseek.com/v1").pack(fill="x", pady=(px(3), 0))

        字段名("钥匙").pack(fill="x", pady=(px(9), 0))
        self.s_key_var = tk.StringVar()
        钥匙行 = tk.Frame(body, bg=CARD_BG)
        钥匙行.pack(fill="x", pady=(px(4), 0))
        self.s_key_entry = 输入框(self.s_key_var, show="*", parent=钥匙行)
        self.s_key_entry.pack(side="left", fill="x", expand=True, ipady=px(4))
        self._key_shown = False
        self.key_toggle = tk.Button(
            钥匙行, text="显示", command=self._toggle_key_show,
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            takefocus=0, bg=CARD_BG, fg=SUB_FG, activebackground=HOVER_BG,
            activeforeground=SUB_FG, font=("微软雅黑", 9), width=5, padx=px(2),
        )
        self.key_toggle.pack(side="right", padx=(px(6), 0), fill="y")
        提示("去官网申请，粘贴到这里").pack(fill="x", pady=(px(3), 0))

        字段名("模型").pack(fill="x", pady=(px(9), 0))
        self.s_model_var = tk.StringVar()
        输入框(self.s_model_var).pack(fill="x", pady=(px(4), 0), ipady=px(4))
        提示("如 deepseek-flash，照文档抄").pack(fill="x", pady=(px(3), 0))

        字段名("英译中要求（英文进、中文出）").pack(fill="x", pady=(px(9), 0))
        self.s_prompt_text = tk.Text(
            body, height=4, width=1, font=SRC_FONT, wrap="word",
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=EDGE, highlightcolor=ACCENT,
            bg=CARD_BG, fg=MAIN_FG, insertbackground=MAIN_FG,
            padx=px(6), pady=px(4),
        )
        self.s_prompt_text.pack(fill="both", expand=True, pady=(px(4), 0))

        字段名("中译英要求（中文进、英文出）").pack(fill="x", pady=(px(9), 0))
        self.s_prompt_zh2en_text = tk.Text(
            body, height=3, width=1, font=SRC_FONT, wrap="word",
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=EDGE, highlightcolor=ACCENT,
            bg=CARD_BG, fg=MAIN_FG, insertbackground=MAIN_FG,
            padx=px(6), pady=px(4),
        )
        self.s_prompt_zh2en_text.pack(fill="both", expand=True, pady=(px(4), 0))
        提示("留空就用默认：只返回英文译文，代码和路径保持原样").pack(fill="x", pady=(px(3), 0))

        for _变量 in (self.s_url_var, self.s_key_var, self.s_model_var):
            try:
                _变量.trace_add("write", self._mark_dirty)
            except Exception:
                pass
        try:
            self.s_prompt_text.bind("<<Modified>>", self._mark_prompt_dirty)
        except Exception:
            pass
        try:
            self.s_prompt_zh2en_text.bind("<<Modified>>", self._mark_zh2en_dirty)
        except Exception:
            pass

        try:
            self._s_save_imgs = {
                k: _make_primary_button_image(k, 88, 32)
                for k in ("normal", "hover", "press")
            }
        except Exception:
            self._s_save_imgs = {}
        save_btn = tk.Button(
            row, text="保存", command=self._settings_save,
            image=self._s_save_imgs.get("normal"), compound="center",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            takefocus=0, bg=CARD_BG, fg="#FFFFFF",
            activebackground=CARD_BG, activeforeground="#FFFFFF",
            font=FONT, width=px(88), height=px(32), padx=0, pady=0,
        )
        if not self._s_save_imgs:
            try:
                save_btn.configure(
                    image="", bg=ACCENT, activebackground=ACCENT
                )
            except Exception:
                pass
        save_btn.pack(side="right")
        _bind_hover(save_btn, self._s_save_imgs)

        try:
            self._s_del_imgs = {
                k: _make_secondary_button_image(k, 88, 32)
                for k in ("normal", "hover", "press")
            }
        except Exception:
            self._s_del_imgs = {}
        del_btn = tk.Button(
            row, text="删除", command=self._settings_delete,
            image=self._s_del_imgs.get("normal"), compound="center",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            takefocus=0, bg=CARD_BG, fg=MAIN_FG,
            activebackground=CARD_BG, activeforeground=MAIN_FG,
            font=FONT, width=px(88), height=px(32), padx=0, pady=0,
        )
        if not self._s_del_imgs:
            try:
                del_btn.configure(
                    image="", bg=HOVER_BG, activebackground="#E6E9EF"
                )
            except Exception:
                pass
        del_btn.pack(side="right", padx=(0, px(8)))
        _bind_hover(del_btn, self._s_del_imgs)

        try:
            self._s_test_imgs = {
                k: _make_secondary_button_image(k, 96, 32)
                for k in ("normal", "hover", "press")
            }
        except Exception:
            self._s_test_imgs = {}
        self.test_btn = tk.Button(
            row, text="测试连接", command=self._settings_test,
            image=self._s_test_imgs.get("normal"), compound="center",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            takefocus=0, bg=CARD_BG, fg=MAIN_FG,
            activebackground=CARD_BG, activeforeground=MAIN_FG,
            font=FONT, width=px(96), height=px(32), padx=0, pady=0,
        )
        if not self._s_test_imgs:
            try:
                self.test_btn.configure(
                    image="", bg=HOVER_BG, activebackground="#E6E9EF"
                )
            except Exception:
                pass
        self.test_btn.pack(side="right", padx=(0, px(8)))
        _bind_hover(self.test_btn, self._s_test_imgs)

        self._refresh_settings_list()

        try:
            win.update_idletasks()
            需要 = win.winfo_reqheight()
            上限 = win.winfo_screenheight() - px(100)
            if 需要 > 上限:
                self._fit_prompt_boxes(win, 上限)
                win.update_idletasks()
                需要 = win.winfo_reqheight()
            高 = max(px(560), 需要)
            高 = min(高, 上限)
            win.geometry(f"{px(620)}x{高}")
        except Exception:
            pass

    def _apply_dark_titlebar(self, win):
        """让系统标题栏跟随深色：先允许本窗用深色，再设 DWM 属性（20=Win10 20H1+，19=更早）。"""
        try:
            import ctypes

            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetAncestor(win.winfo_id(), 2)
            if not hwnd:
                return
            try:
                ctypes.WinDLL("uxtheme.dll")[133](hwnd, True)  # AllowDarkModeForWindow
            except Exception:
                pass
            值 = ctypes.c_int(1)
            for 属性 in (20, 19):
                try:
                    结果 = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 属性, ctypes.byref(值), ctypes.sizeof(值)
                    )
                except Exception:
                    continue
                if 结果 == 0:
                    break
        except Exception:
            pass

    def _toggle_key_show(self):
        self._key_shown = not getattr(self, "_key_shown", False)
        try:
            self.s_key_entry.configure(show="" if self._key_shown else "*")
            self.key_toggle.configure(text="隐藏" if self._key_shown else "显示")
        except Exception:
            pass

    def _settings_test(self):
        """用右边填的地址/钥匙/模型真发一次最小请求，让用户当场知道能不能用。"""
        url = self.s_url_var.get().strip()
        key = self.s_key_var.get().strip()
        model = self.s_model_var.get().strip()
        if not (url and key and model):
            self.s_hint_var.set("地址、钥匙、模型三样都填好才能测试。")
            return
        if _接口chat is None:
            self.s_hint_var.set("接口模块没准备好，稍后再试。")
            return
        try:
            self.test_btn.configure(state="disabled")
        except Exception:
            pass
        self.s_hint_var.set("正在测试连接…")

        def 收尾(文字):
            try:
                self.test_btn.configure(state="normal")
            except Exception:
                pass
            self.s_hint_var.set(文字)

        def 跑():
            try:
                回 = _接口chat(url, key, model, "你是连接测试助手。", "只回复两个字：正常")
                文字 = f"连接正常：模型回复「{(回 or '').strip()[:20]}」"
            except Exception as e:
                文字 = "连接失败：" + str(getattr(e, "message", e) or e)
            try:
                self.settings_win.after(0, lambda: 收尾(文字))
            except Exception:
                pass

        import threading

        threading.Thread(target=跑, daemon=True).start()

    def _on_list_select(self, _e=None):
        self._apply_list_style()
        self._on_profile_selected()

    def _apply_list_style(self):
        """正在用：✓ + 蓝字；选中：浅蓝底。选中项的文字颜色由 selectforeground 决定，
        所以当选中的就是"正在用"时，把 selectforeground 也调成蓝色。"""
        try:
            sel = self.prof_list.curselection()
            选中 = sel[0] if sel else -1
            正在用 = getattr(self, "_cur_index", -1)
            self.prof_list.configure(
                selectforeground=SELECT_FG_ACCENT if 选中 == 正在用 and 正在用 >= 0 else MAIN_FG
            )
            for i, (_名, 配好) in enumerate(getattr(self, "_row_state", [])):
                if i == 正在用:
                    self.prof_list.itemconfig(i, foreground=ACCENT_TEXT)
                elif not 配好:
                    self.prof_list.itemconfig(i, foreground=FAINT_FG)
                else:
                    self.prof_list.itemconfig(i, foreground=MAIN_FG)
        except Exception:
            pass

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
            self._row_state = []
            self._cur_index = names.index(cur) if cur in names else -1
            pick = 0
            for i, name in enumerate(names):
                try:
                    configured = is_profile_configured(name, data) if is_profile_configured else True
                except Exception:
                    configured = True
                if name == cur:
                    label = f"✓ {name}"
                elif not configured:
                    label = f"{name}（未配置）"
                else:
                    label = name
                self.prof_list.insert("end", label)
                self._row_state.append((name, configured))
                if name == (select_name or cur):
                    pick = i
            if names:
                self.prof_list.selection_clear(0, "end")
                self.prof_list.selection_set(pick)
                self.prof_list.see(pick)
            self._apply_list_style()
        finally:
            self._refreshing_list = False
        self._fill_settings_fields()

    def _settings_close(self, win=None):
        """关窗：有没保存的改动先问一句，别让用户白填。"""
        win = win or getattr(self, "settings_win", None)
        if getattr(self, "_s_dirty", False):
            try:
                关 = messagebox.askyesno(
                    "配置", "还有改动没保存，关掉就丢了。要关掉吗？", parent=win
                )
            except Exception:
                关 = False
            if not 关:
                return
        try:
            win.destroy()
        except Exception:
            pass

    def _mark_dirty(self, *_a):
        if getattr(self, "_refreshing_fields", False):
            return
        self._s_dirty = True

    def _mark_prompt_dirty(self, _e=None):
        try:
            if not self.s_prompt_text.edit_modified():
                return
            self.s_prompt_text.edit_modified(False)
        except Exception:
            pass
        self._mark_dirty()

    def _mark_zh2en_dirty(self, _e=None):
        try:
            if not self.s_prompt_zh2en_text.edit_modified():
                return
            self.s_prompt_zh2en_text.edit_modified(False)
        except Exception:
            pass
        self._mark_dirty()

    def _fit_prompt_boxes(self, win, 可用高):
        """小屏时先收提示词框行数：宁可少显示几行，也不让新加的中译英框被挤出可视区。"""
        try:
            框们 = [self.s_prompt_text, self.s_prompt_zh2en_text]
            while win.winfo_reqheight() > 可用高:
                最高 = max(框们, key=lambda w: int(w.cget("height")))
                if int(最高.cget("height")) <= 1:
                    break
                最高.configure(height=int(最高.cget("height")) - 1)
                win.update_idletasks()
        except Exception:
            pass

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
        self._refreshing_fields = True
        try:
            self.s_url_var.set(prof.get("base_url", ""))
            self.s_key_var.set(prof.get("api_key", ""))
            self.s_model_var.set(prof.get("model", ""))
            self.s_prompt_text.delete("1.0", "end")
            self.s_prompt_text.insert("1.0", prof.get("prompt", ""))
            self.s_prompt_zh2en_text.delete("1.0", "end")
            self.s_prompt_zh2en_text.insert("1.0", prof.get("prompt_zh2en", ""))
            try:
                self.s_prompt_text.edit_modified(False)
            except Exception:
                pass
            try:
                self.s_prompt_zh2en_text.edit_modified(False)
            except Exception:
                pass
            self._s_dirty = False
        finally:
            self._refreshing_fields = False

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
                prompt_zh2en=self.s_prompt_zh2en_text.get("1.0", "end").strip(),
            )
            switch_profile(name)
            self._refresh_settings_list(select_name=name)
            self._home_status()
            self._s_dirty = False
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
            确认 = messagebox.askyesno(
                "删除方案",
                f"确定删除「{name}」吗？删了要重新填地址和钥匙。",
                parent=self.settings_win,
            )
        except Exception:
            确认 = False
        if not 确认:
            return
        try:
            cur = delete_profile(name)
            self._refresh_settings_list(select_name=cur)
            self.s_hint_var.set(f"已删除：{name}，现在用的是：{cur}。")
            self._home_status()
        except Exception as e:
            self.s_hint_var.set(str(e))
