"""运行时验收：配置窗删除确认 / 关窗提醒 / 译文只读 / DPI 缩放。全部用假对话框，不碰真配置。"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import app as appmod
import translator_settings_window as SW
from translator_scale import UI_SCALE

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

结果 = []


def 查(名, 通过, 明细=""):
    结果.append(bool(通过))
    print(("PASS " if 通过 else "FAIL ") + 名 + (f" [{明细}]" if 明细 else ""))


a = appmod.App()
a.root.deiconify()
a.root.update()
查("DPI 缩放系数已生效", abs(UI_SCALE - 1.25) < 0.01, f"scale={UI_SCALE}")
查("窗口宽度按缩放放大", a.root.winfo_width() > 380, f"w={a.root.winfo_width()}")
查("译文只读", str(a.dst_text.cget("state")) == "disabled")
a._dst_set("只读也能写")
查("程序写入正常", a.dst_text.get("1.0", "end-1c") == "只读也能写")
查("译文区仍是只读", str(a.dst_text.cget("state")) == "disabled")
try:
    a.dst_text.insert("1.0", "X")  # 模拟用户/野代码直接写
    用户写入生效 = a.dst_text.get("1.0", "end-1c").startswith("X")
except Exception:
    用户写入生效 = False
查("非本类写入被拦住", not 用户写入生效)

# 配置窗
a.open_settings()
a.root.update()
win = a.settings_win
查("配置窗已打开", win is not None and win.winfo_exists())
查("配置窗锁定大小", win.resizable() == (0, 0), f"resizable={win.resizable()}")
实际 = (win.winfo_width(), win.winfo_height())
查("配置窗没有超出屏幕", 实际[1] <= win.winfo_screenheight() - 50, f"size={实际}")

原_询问 = SW.messagebox.askyesno
原_删除 = SW.delete_profile
删记录 = []

# 关窗提醒：有改动 + 点取消 → 窗口还在
a._s_dirty = True
SW.messagebox.askyesno = lambda *x, **k: False
a._settings_close(win)
a.root.update()
查("关窗提醒：点取消窗口还在", bool(win.winfo_exists()))

# 删除确认：点取消 → 不删
a.prof_list.selection_clear(0, "end")
a.prof_list.selection_set(0)
选名 = a._selected_profile_name()
SW.delete_profile = lambda 名: 删记录.append(名)
a._settings_delete()
查("删除确认：点取消不删", 删记录 == [], f"selected={选名} 记录={删记录}")

SW.messagebox.askyesno = lambda *x, **k: True
a._settings_close(win)
a.root.update()
查("确认后关窗成功", not win.winfo_exists())

SW.messagebox.askyesno = 原_询问
SW.delete_profile = 原_删除

a.on_quit()
print("ALL PASS" if all(结果) else f"FAILED {结果.count(False)}")
sys.exit(0 if all(结果) else 1)
