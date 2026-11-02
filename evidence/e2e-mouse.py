"""真实鼠标端到端：系统级按下/移动/抬起，验证拖宽与滚动条滑块。任一项 FAIL 退出非零。"""
import ctypes
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import app as appmod
from translator_scale import px

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

u = ctypes.windll.user32
结果 = []


def 查(名, 通过, 明细=""):
    结果.append(bool(通过))
    print(("PASS " if 通过 else "FAIL ") + 名 + (f" [{明细}]" if 明细 else ""))


def 移到(x, y, 步=6, 间隔=0.012):
    sx, sy = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    x = max(0, min(int(x), sx - 1))
    y = max(0, min(int(y), sy - 1))
    u.SetCursorPos(x, y)
    time.sleep(间隔)


def 按下():
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.03)


def 松开():
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.05)


def 拖动(从, 到, 步=12):
    x0, y0 = 从
    移到(x0, y0)
    按下()
    try:
        a.root.update()
    except Exception:
        pass
    for i in range(1, 步 + 1):
        移到(x0 + (到[0] - x0) * i / 步, y0 + (到[1] - y0) * i / 步)
        try:
            a.root.update()
        except Exception:
            pass
    松开()
    try:
        a.root.update()
    except Exception:
        pass


原鼠标 = None
try:
    点 = ctypes.wintypes.POINT()
    u.GetCursorPos(ctypes.byref(点))
    原鼠标 = (点.x, 点.y)
except Exception:
    pass

a = appmod.App()
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", "Long enough source text for scrolling checks.")
a._dst_set("这是一段很长的译文。" * 200)
a.popup()
a.root.update()
time.sleep(0.4)
a.root.update()

wx, wy = int(a.root.winfo_rootx()), int(a.root.winfo_rooty())
ww, wh = int(a.root.winfo_width()), int(a.root.winfo_height())
高边 = wh // 2

# ---- 右边拖宽（真实鼠标）----
起宽 = a.root.winfo_width()
右边x = wx + ww - px(8) - px(3)
拖动((右边x, wy + 高边), (右边x + px(60), wy + 高边))
a.root.update()
time.sleep(0.2)
加宽后 = a.root.winfo_width()
查("真实鼠标拖右边能加宽", 加宽后 > 起宽, f"{起宽}->{加宽后}")
右缘 = a.root.winfo_x() + a.root.winfo_width()
查("右边缘不越出屏幕", 右缘 <= u.GetSystemMetrics(0), f"右缘={右缘}")

# ---- 左边拖宽（右边缘应基本不动）----
左缘前 = a.root.winfo_x() + a.root.winfo_width()
左边x = a.root.winfo_rootx() + px(8) + px(3)
拖动((左边x, a.root.winfo_rooty() + 高边), (左边x - px(50), a.root.winfo_rooty() + 高边))
a.root.update()
time.sleep(0.2)
左缘后 = a.root.winfo_x() + a.root.winfo_width()
查("真实鼠标拖左边能加宽", a.root.winfo_width() > 加宽后, f"{加宽后}->{a.root.winfo_width()}")
查("拖左边时右边缘不动", abs(左缘后 - 左缘前) <= px(2), f"{左缘前}->{左缘后}")

# ---- 滚动条滑块（真实鼠标）----
a.root.update()
time.sleep(0.3)
a.root.update()
可见 = bool(a.dst_bar.winfo_ismapped())
查("长内容滚动条出现", 可见)
if 可见:
    前 = a.dst_text.yview()[0]
    拇指x = a.dst_thumb.winfo_rootx() + a.dst_thumb.winfo_width() // 2
    拇指y = a.dst_thumb.winfo_rooty() + a.dst_thumb.winfo_height() // 2
    拖动((拇指x, 拇指y), (拇指x, 拇指y + 90))
    a.root.update()
    time.sleep(0.2)
    后 = a.dst_text.yview()[0]
    查("真实鼠标拖滑块能滚", 后 > 前 + 0.05, f"{前:.2f}->{后:.2f}")

# ---- 轨道点击 ----
if 可见:
    轨x = a.dst_bar.winfo_rootx() + a.dst_bar.winfo_width() // 2
    轨顶 = a.dst_bar.winfo_rooty()
    轨高 = a.dst_bar.winfo_height()
    前 = a.dst_text.yview()[0]
    移到(轨x, 轨顶 + int(轨高 * 0.9))
    按下()
    松开()
    a.root.update()
    后 = a.dst_text.yview()[0]
    查("点轨道能跳转", 后 > 前 + 0.1, f"{前:.2f}->{后:.2f}")

# ---- 滚到中间再抓滑块（不能跳回顶部）----
if 可见:
    a.dst_text.yview_moveto(0.5)
    a.root.update()
    time.sleep(0.25)
    a.root.update()
    前 = a.dst_text.yview()[0]
    拇指x = a.dst_thumb.winfo_rootx() + a.dst_thumb.winfo_width() // 2
    拇指y = a.dst_thumb.winfo_rooty() + a.dst_thumb.winfo_height() // 2
    拖动((拇指x, 拇指y), (拇指x, 拇指y + 40), 步=8)
    a.root.update()
    time.sleep(0.2)
    后 = a.dst_text.yview()[0]
    查("中间抓滑块不跳顶", 后 >= 前 - 0.02, f"{前:.2f}->{后:.2f}")

a.on_quit()
if 原鼠标:
    u.SetCursorPos(*原鼠标)

print("ALL PASS" if all(结果) else f"FAILED {结果.count(False)}")
sys.exit(0 if all(结果) else 1)
