"""中译英提示词框：配置窗实机检查（两框可见、能回填、保存能落盘、矮屏不被挤出）。

[INPUT] 临时配置目录（不碰真实 config.json）。
[OUTPUT] 控制台 PASS/FAIL + evidence/audit/09-settings-zh2en.png / 10-settings-small.png。
[POS] 证据脚本；只验证，不改产品代码。
[PROTOCOL] python evidence/check-zh2en.py
"""
import ctypes
import json
import os
import shutil
import sys
import tempfile
import time
import tkinter as tk

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

临时 = tempfile.mkdtemp(prefix="zh2en-ui-")
os.environ["TRANSLATOR_CONFIG_DIR"] = 临时
os.makedirs(临时, exist_ok=True)
with open(os.path.join(临时, "config.json"), "w", encoding="utf-8") as f:
    json.dump(
        {
            "version": 2,
            "current": "测试",
            "profiles": {
                "测试": {
                    "base_url": "https://example.invalid/v1",
                    "model": "m",
                    "prompt": "英译中提示词原文",
                    "api_key_dpapi": "",
                }
            },
        },
        f,
        ensure_ascii=False,
    )

import app as appmod
from PIL import ImageGrab

appmod.App._start_trigger = lambda s: None
appmod.App._start_tray = lambda s: None
appmod.App._start_singleton_server = lambda s: None

失败 = []


def 断言(条件, 说明):
    print(("PASS  " if 条件 else "FAIL  ") + 说明)
    if not 条件:
        失败.append(说明)


def 找控件(父, 类型, 文本):
    for 子 in 父.winfo_children():
        try:
            if isinstance(子, 类型) and 子.cget("text") == 文本:
                return 子
        except Exception:
            pass
        r = 找控件(子, 类型, 文本)
        if r is not None:
            return r
    return None


def 截图(w, 名字):
    try:
        hwnd = ctypes.windll.user32.GetAncestor(w.winfo_id(), 2)
        r = (ctypes.c_long * 4)()
        ctypes.windll.user32.GetWindowRect(hwnd, r)
        目 = os.path.join(BASE, "evidence", "audit", 名字)
        ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3])).save(目)
        print("saved", 名字)
    except Exception as e:
        print("截图失败:", e)


def 量窗口(w):
    w.update()
    time.sleep(0.2)
    w.update()
    return w


# ============ 第一阶段：正常屏幕 ============
a = appmod.App()
a.root.deiconify()
a.root.update()
a.open_settings()
a.root.update()
w = a.settings_win
量窗口(w)

断言(hasattr(a, "s_prompt_zh2en_text"), "配置窗存在中译英提示词框")
断言(hasattr(a, "s_prompt_text"), "英译中提示词框仍在")
断言(bool(a.s_prompt_text.winfo_ismapped()), "英译中提示词框可见")
断言(bool(a.s_prompt_zh2en_text.winfo_ismapped()), "中译英提示词框可见")

英译中标 = 找控件(w, tk.Label, "英译中要求（英文进、中文出）")
中译英标 = 找控件(w, tk.Label, "中译英要求（中文进、英文出）")
断言(英译中标 is not None, "英译中标签带方向说明")
断言(中译英标 is not None, "中译英标签带方向说明")

英译中 = a.s_prompt_text.get("1.0", "end").strip()
中译英 = a.s_prompt_zh2en_text.get("1.0", "end").strip()
断言(英译中 == "英译中提示词原文", f"英译中框回填正确（实际：{英译中!r}）")
断言(bool(中译英), f"中译英框回填非空（实际：{中译英!r}）")

高 = a.s_prompt_zh2en_text.winfo_height()
断言(高 >= 40, f"中译英框有实际高度，没被压扁（{高}px）")
断言(
    a.s_prompt_zh2en_text.winfo_rooty() + 高 <= w.winfo_rooty() + w.winfo_height(),
    "中译英框完整落在配置窗内，没被裁掉",
)

# 保存能落盘
a.s_prompt_zh2en_text.delete("1.0", "end")
a.s_prompt_zh2en_text.insert("1.0", "地道的英文，只给译文")
a.s_key_var.set("sk-test")
a._settings_save()
w.update()

import translator_settings as S

读回 = S.load_config()
断言(读回.get("prompt_zh2en") == "地道的英文，只给译文", "保存后中译英提示词落盘")
断言(读回.get("prompt") == "英译中提示词原文", "英译中提示词没被连带改掉")

截图(w, "09-settings-zh2en.png")

# ============ 第二阶段：模拟 768px 矮屏（125% 缩放下上限 643px） ============
a._s_dirty = False
try:
    a._settings_close(w)
except Exception:
    try:
        w.destroy()
    except Exception:
        pass
a.settings_win = None
a.root.update()

真实screen = tk.Toplevel.winfo_screenheight
tk.Toplevel.winfo_screenheight = lambda self: 768
try:
    a.open_settings()
    a.root.update()
    w2 = a.settings_win
    量窗口(w2)
finally:
    tk.Toplevel.winfo_screenheight = 真实screen

矮高 = w2.winfo_height()
print(f"  矮屏窗口高度 = {矮高}px（上限 768 - px(100)）")
断言(矮高 <= 768, f"矮屏窗口没超过屏幕高度（{矮高}px）")
断言(bool(a.s_prompt_text.winfo_ismapped()), "矮屏：英译中框仍然可见")
断言(bool(a.s_prompt_zh2en_text.winfo_ismapped()), "矮屏：中译英框仍然可见")
断言(
    a.s_prompt_zh2en_text.winfo_height() >= 20,
    f"矮屏：中译英框仍有可编辑高度（{a.s_prompt_zh2en_text.winfo_height()}px）",
)

底 = w2.winfo_rooty() + w2.winfo_height()
for 名 in ("测试连接", "删除", "保存"):
    钮 = 找控件(w2, tk.Button, 名)
    断言(钮 is not None and bool(钮.winfo_ismapped()), f"矮屏：{名}按钮可见")
    if 钮 is not None:
        断言(
            钮.winfo_rooty() + 钮.winfo_height() <= 底,
            f"矮屏：{名}按钮完整落在窗内",
        )

截图(w2, "10-settings-small.png")

try:
    a._s_dirty = False
    a._settings_close(w2)
except Exception:
    pass
a.on_quit()
shutil.rmtree(临时, ignore_errors=True)
print("")
print("结果：" + ("全部通过" if not 失败 else f"{len(失败)} 条失败"))
sys.exit(1 if 失败 else 0)
