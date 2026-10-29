"""UI 自检截图：起真实 App 界面（屏蔽键盘钩子/托盘/单实例），灌示例文本，截图存 evidence/。"""
import os
import sys
import ctypes
import time

# 先设 DPI 感知：截图（物理像素）和窗口坐标才能对齐
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import app as appmod
from PIL import ImageGrab


def window_bbox(root):
    """用系统级窗口矩形（物理像素），避开高分屏缩放错位。"""
    hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
    rect = (ctypes.c_long * 4)()
    ctypes.windll.user32.GetWindowRect(hwnd, rect)
    return (rect[0], rect[1], rect[2], rect[3])

# 屏蔽副作用：不装全局键盘钩子、不起托盘、不占单实例端口
appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

EN = (
    "One concern: copy buttons that look like links are a significant change. "
    "The actual app needs a visual check, because geometry checks can't judge aesthetics. "
    "The design is deliberately minimal and should look calm and airy."
)
ZH = (
    "有个担心：长得像链接的复制按钮是个大变化，实际界面必须肉眼看一次，"
    "因为几何检查判断不了美丑。设计故意极简，应该看起来安静透气。"
    "再补一行字看看行距和留白够不够呼吸。再补一行字看看行距和留白够不够呼吸。"
)

a = appmod.App()
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", EN)
a.dst_text.delete("1.0", "end")
a.dst_text.insert("1.0", ZH)
a.root.deiconify()
a._place_top_right()
try:
    a.root.lift()
    a.root.focus_force()
except Exception:
    pass
a.root.update()
time.sleep(0.5)
a._refit()
a.root.update()
time.sleep(0.3)


def grab(name):
    a.root.update()
    time.sleep(0.2)
    path = os.path.join(BASE, "evidence", name)
    ImageGrab.grab(bbox=window_bbox(a.root)).save(path)
    print("saved", path)


grab("ui-main.png")

# 提示浮窗：直接在复制图标旁打开
cx = a.copy_btn.winfo_rootx() + 4
cy = a.copy_btn.winfo_rooty() + 4
a._tip.show("复制译文", cx, cy)
a.root.update()
grab("ui-tip.png")
a._tip.hide()

# 展开态
a._toggle_source()
a.root.update()
grab("ui-expanded.png")

a.root.destroy()
print("done")
