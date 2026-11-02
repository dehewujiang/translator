"""P2 验收脚本：空状态、滚动条、拖宽下限、深色/浅色调色板。任一项 FAIL 非零退出。"""
import ctypes
import os
import subprocess
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
from translator_scale import px

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

结果 = []


def 查(名, 通过, 明细=""):
    结果.append(bool(通过))
    print(("PASS " if 通过 else "FAIL ") + 名 + (f" [{明细}]" if 明细 else ""))


a = appmod.App()
a.popup()
a.root.update()
time.sleep(0.2)
a.root.update()
查("空状态引导可见", bool(a.empty_hint.winfo_ismapped()))

a._dst_set("长译文。" * 200)
a.root.update()
time.sleep(0.3)
a.root.update()
查("长内容出现滚动条", bool(a.dst_bar.winfo_ismapped()), f"yview={a.dst_text.yview()}")
查("滚动条很细", a.dst_bar.winfo_width() <= px(10), f"w={a.dst_bar.winfo_width()}")

a._dst_set("短")
a.root.update()
time.sleep(0.2)
a.root.update()
查("短内容收起滚动条", not bool(a.dst_bar.winfo_ismapped()))
查("有内容时引导隐藏", not bool(a.empty_hint.winfo_ismapped()))

起 = a.root.winfo_width()
x = float(a.root.winfo_rootx() + 起)
a._width_press_r(SimpleNamespace(x_root=x))
a._width_drag(SimpleNamespace(x_root=x + 120))
a.root.update()
查("右侧拖宽生效", a.root.winfo_width() > 起, f"{起}->{a.root.winfo_width()}")

x2 = float(a.root.winfo_rootx() + a.root.winfo_width())
a._width_press_r(SimpleNamespace(x_root=x2))
a._width_drag(SimpleNamespace(x_root=x2 - 3000))
a.root.update()
查("拖宽有下限", a.root.winfo_width() == px(320), f"w={a.root.winfo_width()}")
a._width_release()
a.root.update()
底 = int(px(8) + a.footer.winfo_y() + a.footer.winfo_height())
查("拖宽后底栏不越界", 底 <= a.root.winfo_height(), f"底={底} 窗={a.root.winfo_height()}")
a.on_quit()

# 调色板：浅色与深色各跑一遍纯测试（含对比度）
for 模式, 覆盖 in (("浅色", "light"), ("深色", "dark")):
    env = dict(os.environ)
    env["TRANSLATOR_THEME"] = 覆盖
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_p2", "-q"],
        cwd=BASE, env=env, capture_output=True, text=True,
    )
    查(f"{模式}调色板与 P2 逻辑", r.returncode == 0,
       (r.stderr or "").strip().splitlines()[-1] if r.returncode else "OK")

print("ALL PASS" if all(结果) else f"FAILED {结果.count(False)}")
sys.exit(0 if all(结果) else 1)
