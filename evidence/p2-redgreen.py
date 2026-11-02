"""P2 红→绿记录：先制造旧行为/关掉实现跑出红，再恢复跑出绿。"""
import ctypes
import io
import os
import sys
import time
import unittest
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import app as A
import translator_settings_window as SW
import translator_theme as T
from translator_layout import MARGIN

A.App._start_trigger = lambda s: None
A.App._start_tray = lambda s: None
A.App._start_singleton_server = lambda s: None

行 = []


def 记(标签, 文字):
    行.append(f"[{标签}] {文字}")
    print(f"[{标签}] {文字}")


def 跑单测(名):
    buf = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromName(名)
    结果 = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    return 结果.wasSuccessful(), buf.getvalue()


def 红绿(说明, 打补丁, 撤补丁, 测试名):
    打补丁()
    try:
        通过, 输出 = 跑单测(测试名)
    finally:
        撤补丁()
    if 通过:
        记("红失败", f"{说明}：打了补丁居然还通过")
    else:
        记("红", f"{说明}：" + next((l.strip() for l in 输出.splitlines() if "FAIL" in l or "Error" in l), "失败"))
    通过2, _ = 跑单测(测试名)
    记("绿" if 通过2 else "绿失败", f"{说明}：恢复后 {'通过' if 通过2 else '仍失败'}")


# ---- 1) 钥匙显隐 ----
原_显隐 = SW.SettingsWindowMixin._toggle_key_show
红绿(
    "钥匙显隐",
    lambda: setattr(SW.SettingsWindowMixin, "_toggle_key_show", lambda self: None),
    lambda: setattr(SW.SettingsWindowMixin, "_toggle_key_show", 原_显隐),
    "tests.test_p2.钥匙显隐",
)

# ---- 2) 测试连接 ----
原_测试 = SW.SettingsWindowMixin._settings_test
红绿(
    "测试连接",
    lambda: setattr(SW.SettingsWindowMixin, "_settings_test", lambda self: None),
    lambda: setattr(SW.SettingsWindowMixin, "_settings_test", 原_测试),
    "tests.test_p2.测试连接",
)

# ---- 3) 对比度 ----
原_浅 = T.FAINT_FG
def _降对比():
    T.FAINT_FG = "#E8E8E8"
def _恢复对比():
    T.FAINT_FG = 原_浅
红绿("调色板对比度", _降对比, _恢复对比, "tests.test_p2.调色板对比度")

# ---- 4) 空状态 / 滚动条 ----
a = A.App()
a.popup()
a.root.update()
time.sleep(0.2)
a.root.update()

原_提示 = A.App._sync_empty_hint
a.empty_hint.place_forget()
a.root.update()
A.App._sync_empty_hint = lambda self: None
try:
    a._sync_empty_hint()
    a.root.update()
    记("红", f"空状态：关掉实现后引导可见={bool(a.empty_hint.winfo_ismapped())}（应 False）")
finally:
    A.App._sync_empty_hint = 原_提示
a._sync_empty_hint()
a.root.update()
记("绿", f"空状态：恢复后引导可见={bool(a.empty_hint.winfo_ismapped())}（应 True）")

原_滚动 = A.App._on_dst_scroll
a.dst_bar.grid_remove()
a.root.update()
A.App._on_dst_scroll = lambda self, 首, 末: None
a.dst_text.configure(yscrollcommand=a._on_dst_scroll)  # 绑到补丁后的方法
try:
    a._dst_set("长译文。" * 200)
    a.root.update()
    time.sleep(0.3)
    a.root.update()
    记("红", f"滚动条：关掉实现后可见={bool(a.dst_bar.winfo_ismapped())}（应 False）")
finally:
    A.App._on_dst_scroll = 原_滚动
    a.dst_text.configure(yscrollcommand=a._on_dst_scroll)
    a._on_dst_scroll(*[str(v) for v in a.dst_text.yview()])
a.root.update()
time.sleep(0.4)
a.root.update()
记("绿", f"滚动条：恢复后可见={bool(a.dst_bar.winfo_ismapped())}（应 True）")

# ---- 5) 拖宽：复刻"热区在透明边→点击穿透"的旧 bug，再用真鼠标证明 ----
u = ctypes.windll.user32


def 真实拖(x, y, dx):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    a.root.update()
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.12)
    a.root.update()
    for i in range(1, 7):
        u.SetCursorPos(int(x + dx * i / 6), int(y))
        time.sleep(0.04)
        a.root.update()
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.15)
    a.root.update()


def 摆热区(透明边):
    for 边, z in a._width_zones:
        if 透明边:
            z.configure(bg=T.KEY_COLOR)
            if 边 == "left":
                z.place(x=0, y=MARGIN + 13, width=MARGIN, height=max(40, a._window_h - 2 * MARGIN - 26))
            else:
                z.place(x=a._window_w - MARGIN, y=MARGIN + 13, width=MARGIN,
                        height=max(40, a._window_h - 2 * MARGIN - 26))
        else:
            z.configure(bg=T.CARD_BG)
    if not 透明边:
        a._place_resize()


摆热区(True)
a.root.update()
起 = a.root.winfo_width()
真实拖(a.root.winfo_rootx() + a._window_w - MARGIN // 2,
       a.root.winfo_rooty() + a._window_h // 2, 80)
记("红", f"拖宽（热区在透明边）：{起}->{a.root.winfo_width()}（应不变，证明点击穿透）")

摆热区(False)
a.root.update()
起2 = a.root.winfo_width()
真实拖(a.root.winfo_rootx() + a.root.winfo_width() - MARGIN - 6,
       a.root.winfo_rooty() + a.root.winfo_height() // 2, 60)
记("绿", f"拖宽（热区在卡片内）：{起2}->{a.root.winfo_width()}（应变宽）")

a.on_quit()

日志 = "\n".join(行) + "\n"
io.open(os.path.join(BASE, "evidence", "p2-redgreen.log"), "w", encoding="utf-8", newline="").write(日志)
坏 = sum(1 for l in 行 if "红失败" in l or "绿失败" in l)
print("红绿记录完成，异常", 坏)
sys.exit(0 if 坏 == 0 else 1)
