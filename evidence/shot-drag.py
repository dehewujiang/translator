"""拖到底后截图存证：翻译按钮应完整可见。"""
import ctypes
import os
import sys
import time
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import app as appmod
from PIL import ImageGrab

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

a = appmod.App()
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", "Copy this English, tap Ctrl.")
a.dst_text.delete("1.0", "end")
a.dst_text.insert("1.0", "复制这段英文，点一下 Ctrl，中文译文就会冒出来。" * 4)
a.root.deiconify()
a._place_top_right()
a.root.update()
a._refit()
a.root.update()

起点 = float(a.root.winfo_rooty() + a._window_h)
a._grip_press(SimpleNamespace(y_root=起点))
a._grip_drag(SimpleNamespace(y_root=起点 - 400))
a.root.update()
time.sleep(0.3)
a.root.update()

hwnd = ctypes.windll.user32.GetAncestor(a.root.winfo_id(), 2)
rect = (ctypes.c_long * 4)()
ctypes.windll.user32.GetWindowRect(hwnd, rect)
图 = ImageGrab.grab(bbox=(rect[0], rect[1], rect[2], rect[3]))
图.save(os.path.join(BASE, "evidence", "drag-after.png"))
print(f"saved evidence/drag-after.png  size={图.size} window_h={a.root.winfo_height()}")

a.on_quit()
