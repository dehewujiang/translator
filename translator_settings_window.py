"""配置窗：左列表选方案、右详情填地址钥匙模型与提示词。

[INPUT] App 实例（self：settings_win、prof_list、s_* 等状态全挂在它身上）。
[OUTPUT] 620x480 配置小窗；保存/删除/切换直接写配置。
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
    HOVER_BG,
    EDGE,
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
        页底 = "#F7F8FA"
        win = tk.Toplevel(self.root)
        self.settings_win = win
        win.title("配置")
        win.geometry("620x480")
        win.attributes("-topmost", True)
        win.configure(bg=页底)
        win.option_add("*Font", FONT)
        self._refreshing_list = False
        self._prof_names = []

        left = tk.Frame(win, bg=页底, width=212)
        left.pack(side="left", fill="y")
        try:
            left.pack_propagate(False)
        except Exception:
            pass
        tk.Frame(win, width=1, bg=LINE).pack(side="left", fill="y")

        tk.Label(
            left, text="方案（点一下就换）", font=SRC_FONT, fg=SUB_FG, bg=页底,
            anchor="w",
        ).pack(fill="x", padx=20, pady=(20, 10))
        list_wrap = tk.Frame(
            left, bg=CARD_BG, bd=0,
            highlightthickness=1, highlightbackground=EDGE, highlightcolor=ACCENT,
        )
        list_wrap.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.prof_list = tk.Listbox(
            list_wrap, font=FONT, bd=0, relief="flat",
            highlightthickness=0, bg=CARD_BG, fg=MAIN_FG,
            selectbackground="#E8EFFF", selectforeground=MAIN_FG,
            activestyle="none", exportselection=False,
        )
        self.prof_list.pack(fill="both", expand=True, padx=6, pady=4)
        self.prof_list.bind("<<ListboxSelect>>", lambda _e: self._on_profile_selected())
        self.prof_list.bind(
            "<FocusIn>", lambda _e: list_wrap.configure(highlightbackground=ACCENT)
        )
        self.prof_list.bind(
            "<FocusOut>", lambda _e: list_wrap.configure(highlightbackground=EDGE)
        )

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
            font=FONT, width=148, height=32, padx=0, pady=0,
        )
        if not self._s_add_imgs:
            try:
                add_btn.configure(image="", bg=HOVER_BG, activebackground="#E6E9EF")
            except Exception:
                pass
        add_btn.pack(fill="x", padx=20, pady=(0, 20))
        _bind_hover(add_btn, self._s_add_imgs)

        right = tk.Frame(win, bg=CARD_BG)
        right.pack(side="left", fill="both", expand=True)
        body = tk.Frame(right, bg=CARD_BG)
        body.pack(fill="both", expand=True, padx=20, pady=20)

        self.s_hint_var = tk.StringVar(value="")
        row = tk.Frame(body, bg=CARD_BG)
        row.pack(side="bottom", fill="x", pady=(16, 0))
        hint_stat = tk.Label(
            body, textvariable=self.s_hint_var, font=SRC_FONT, fg=SUB_FG,
            bg=CARD_BG, anchor="w", justify="left", wraplength=380,
        )
        hint_stat.pack(side="bottom", fill="x", pady=(8, 0))

        def _recolor_hint(*_a):
            try:
                v = self.s_hint_var.get()
                hint_stat.configure(
                    fg="#C0392B" if v.startswith("读配置失败") else SUB_FG
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

        def 输入框(var, show=None):
            e = tk.Entry(
                body, textvariable=var, font=FONT, relief="flat", bd=0,
                highlightthickness=1, highlightbackground=EDGE, highlightcolor=ACCENT,
                bg=CARD_BG, fg=MAIN_FG, insertbackground=MAIN_FG,
            )
            if show:
                e.configure(show=show)
            return e

        字段名("地址").pack(fill="x")
        self.s_url_var = tk.StringVar()
        输入框(self.s_url_var).pack(fill="x", pady=(4, 0), ipady=4)
        提示("如 https://api.deepseek.com/v1").pack(fill="x", pady=(4, 0))

        字段名("钥匙").pack(fill="x", pady=(12, 0))
        self.s_key_var = tk.StringVar()
        输入框(self.s_key_var, show="*").pack(fill="x", pady=(4, 0), ipady=4)
        提示("去官网申请，粘贴到这里").pack(fill="x", pady=(4, 0))

        字段名("模型").pack(fill="x", pady=(12, 0))
        self.s_model_var = tk.StringVar()
        输入框(self.s_model_var).pack(fill="x", pady=(4, 0), ipady=4)
        提示("如 deepseek-flash，照文档抄").pack(fill="x", pady=(4, 0))

        字段名("翻译要求（想让它怎么翻就怎么写）").pack(fill="x", pady=(12, 0))
        self.s_prompt_text = tk.Text(
            body, height=5, font=SRC_FONT, wrap="word",
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=EDGE, highlightcolor=ACCENT,
            bg=CARD_BG, fg=MAIN_FG, insertbackground=MAIN_FG,
            padx=6, pady=4,
        )
        self.s_prompt_text.pack(fill="both", expand=True, pady=(4, 0))

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
            font=FONT, width=88, height=32, padx=0, pady=0,
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
            font=FONT, width=88, height=32, padx=0, pady=0,
        )
        if not self._s_del_imgs:
            try:
                del_btn.configure(
                    image="", bg=HOVER_BG, activebackground="#E6E9EF"
                )
            except Exception:
                pass
        del_btn.pack(side="right", padx=(0, 8))
        _bind_hover(del_btn, self._s_del_imgs)

        self._refresh_settings_list()

        try:
            win.update_idletasks()
            高 = max(480, win.winfo_reqheight())
            高 = min(高, win.winfo_screenheight() - 100)
            win.geometry(f"620x{高}")
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
