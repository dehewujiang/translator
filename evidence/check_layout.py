"""无边框卡片回归检查：起真实 App（屏蔽键盘钩子/托盘/单实例），逐项打印 PASS/FAIL。

覆盖：窗口 380 宽、无边框、色键、状态条出现/消失时底栏仍为 32px、
两种窗口高度下四角遮罩位置、窗口区域无品红残留像素。
任一项 FAIL 即非零退出；全过打印 ALL PASS，否则 FAILED n。
"""
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

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import app as appmod
from PIL import ImageGrab

FAILURES = 0


def check(名字, 通过, 明细=""):
    global FAILURES
    尾 = f" [{明细}]" if 明细 else ""
    print(f"{'PASS' if 通过 else 'FAIL'} {名字}{尾}")
    if not 通过:
        FAILURES += 1


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

a = appmod.App()
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", "Copy this English, tap Ctrl, and the Chinese shows up.")
a.dst_text.delete("1.0", "end")
a.dst_text.insert("1.0", "复制这段英文，点一下 Ctrl，中文译文就会冒出来。")
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

# ---- 窗口基本形状 ----
check("窗口宽==380", a.root.winfo_width() == 380, f"w={a.root.winfo_width()}")
try:
    无边框 = bool(a.root.overrideredirect())
except Exception:
    无边框 = False
check("无边框 overrideredirect", 无边框, f"overrideredirect={无边框}")
try:
    色键 = a.root.wm_attributes("-transparentcolor")
except Exception as e:
    色键 = f"<读不到: {e}>"
check("色键已设置", str(色键).lower() == "#ff00fe", f"transparentcolor={色键}")

# ---- 缺陷 1 回归：状态条出现时底栏不被压扁 ----
a.status_var.set("译文已复制，去别处粘贴就行")
a._status_show()
a.root.update()
time.sleep(0.2)
check("状态显示时底栏==32", a.footer.winfo_height() == 32,
      f"footer_h={a.footer.winfo_height()}")
check("状态显示时翻译按钮==32", a.translate_btn.winfo_height() == 32,
      f"btn_h={a.translate_btn.winfo_height()}")

# ---- 状态条消失后底栏仍在 ----
a._status_hide()
a.root.update()
time.sleep(0.2)
check("状态隐藏后底栏==32", a.footer.winfo_height() == 32,
      f"footer_h={a.footer.winfo_height()}")
check("状态隐藏后翻译按钮==32", a.translate_btn.winfo_height() == 32,
      f"btn_h={a.translate_btn.winfo_height()}")


def check_corners(标签):
    高 = a.root.winfo_height()
    底 = 高 - 8 - 13
    期望 = {"tl": 8, "tr": 8, "bl": 底, "br": 底}
    for 角 in ("tl", "tr", "bl", "br"):
        实测 = a._corners[角].winfo_y()
        check(f"角遮罩@{标签}/{角} y=={期望[角]}", 实测 == 期望[角],
              f"y={实测} win_h={高}")


# ---- 两种窗口高度下四角遮罩位置 ----
check_corners(f"{a.root.winfo_height()}")
高2 = a.root.winfo_height() + 150
a._window_h = 高2
a._place_top_right()
a.root.update()
a._place_corners()
a.root.update()
time.sleep(0.2)
check_corners(f"{a.root.winfo_height()}")

# ---- 窗口区域无品红残留 ----
try:
    图 = ImageGrab.grab(bbox=window_bbox(a.root)).convert("RGB")
    品红数 = sum(1 for p in 图.getdata() if p == (255, 0, 254))
except Exception as e:
    品红数 = -1
    print(f"截图失败: {e}")
check("窗口内无品红像素", 品红数 == 0, f"magenta={品红数}")

a.root.destroy()

if FAILURES:
    print(f"FAILED {FAILURES}")
    sys.exit(1)
print("ALL PASS")
