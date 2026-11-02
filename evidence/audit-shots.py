"""UI 审核用截图：主窗翻译 / 词典 / 状态提示 / 配置窗 / 悬停气泡。"""
import ctypes
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
OUT = os.path.join(BASE, "evidence", "audit")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import app as appmod
from PIL import ImageGrab
from translator_domain import Definition

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

os.makedirs(OUT, exist_ok=True)


def grab(root, name):
    hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
    rect = (ctypes.c_long * 4)()
    ctypes.windll.user32.GetWindowRect(hwnd, rect)
    图 = ImageGrab.grab(bbox=(rect[0], rect[1], rect[2], rect[3]))
    图.save(os.path.join(OUT, name))
    print("saved", name, 图.size)


a = appmod.App()
a.root.deiconify()
a._place_top_right()
a.root.update()

# 1. 长翻译
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", "One concern: copy buttons that look like links are a significant change. The actual app needs a visual check.")
a._dst_set("有个担心：长得像链接的复制按钮是个大变化，实际界面必须肉眼检查一次，因为几何检查判断不了美丑。设计故意极简，应该看起来安静透气。")
a.popup()
a.root.update()
a._refit()
a.root.update()
time.sleep(0.3)
grab(a.root, "01-main-translate.png")

# 2. 状态提示
a._say_transient("译文已复制，去别处粘贴就行")
a.root.update()
time.sleep(0.2)
grab(a.root, "02-main-status.png")
a._status_hide()

# 3. 词典
定义 = Definition(
    word="resilience",
    uk="/rɪˈzɪliəns/",
    us="/rɪˈzɪliəns/",
    senses=[
        {"pos": "n.", "defs": ["恢复力，韧性", "弹性"], "examples": [
            {"en": "She showed great resilience in the face of failure.", "zh": "面对失败，她表现出极强的韧性。"}
        ]},
        {"pos": "n.", "defs": ["（材料）回弹性"], "examples": []},
    ],
)
a._show_dict(定义)
a.root.update()
time.sleep(0.3)
grab(a.root, "03-dict.png")

# 4. 悬停气泡
a._tip_show("拖动调高度", type("E", (), {"x_root": a.root.winfo_rootx() + 300, "y_root": a.root.winfo_rooty() + 330})())
a.root.update()
time.sleep(0.2)
图 = None
try:
    上 = a._tip._窗
    if 上 is not None:
        上.update()
        hwnd = ctypes.windll.user32.GetAncestor(上.winfo_id(), 2)
        rect = (ctypes.c_long * 4)()
        ctypes.windll.user32.GetWindowRect(hwnd, rect)
        图 = ImageGrab.grab(bbox=(rect[0], rect[1], rect[2], rect[3]))
        图.save(os.path.join(OUT, "04-tip.png"))
        print("saved 04-tip.png", 图.size)
except Exception as e:
    print("tip shot failed", e)

# 5. 配置窗
a.open_settings()
a.root.update()
time.sleep(0.5)
try:
    窗 = a.settings_win
    if 窗 is not None:
        窗.update()
        hwnd = ctypes.windll.user32.GetAncestor(窗.winfo_id(), 2)
        rect = (ctypes.c_long * 4)()
        ctypes.windll.user32.GetWindowRect(hwnd, rect)
        图 = ImageGrab.grab(bbox=(rect[0], rect[1], rect[2], rect[3]))
        图.save(os.path.join(OUT, "05-settings.png"))
        print("saved 05-settings.png", 图.size)
except Exception as e:
    print("settings shot failed", e)

a.on_quit()
