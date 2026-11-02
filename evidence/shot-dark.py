"""深色模式截图（TRANSLATOR_THEME=dark 运行）。"""
import ctypes, os, sys, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE); os.chdir(BASE)
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception: pass
import app as appmod
from PIL import ImageGrab
from translator_domain import Definition
appmod.App._start_trigger = lambda s: None
appmod.App._start_tray = lambda s: None
appmod.App._start_singleton_server = lambda s: None
OUT = os.path.join(BASE, "evidence", "audit-dark"); os.makedirs(OUT, exist_ok=True)

def grab(widget, name):
    hwnd = ctypes.windll.user32.GetAncestor(widget.winfo_id(), 2)
    r = (ctypes.c_long * 4)(); ctypes.windll.user32.GetWindowRect(hwnd, r)
    im = ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3]))
    im.save(os.path.join(OUT, name)); print("saved", name, im.size)

a = appmod.App(); a.popup(); a.root.update(); time.sleep(0.2)
grab(a.root, "d1-empty.png")
a.src_text.delete("1.0","end"); a.src_text.insert("1.0","One concern: the actual app needs a visual check.")
a._dst_set("有个担心：实际界面必须肉眼检查一次，因为几何检查判断不了美丑。设计故意极简，应该看起来安静透气。")
a.root.update(); time.sleep(0.2); grab(a.root, "d2-translate.png")
a._show_dict(Definition(word="resilience", uk="/rɪˈzɪliəns/", us="/rɪˈzɪliəns/",
    senses=[{"pos":"n.","defs":["恢复力，韧性"],"examples":[{"en":"She showed great resilience.","zh":"她表现出极强的韧性。"}]}]))
a.root.update(); time.sleep(0.3); grab(a.root, "d3-dict.png")
a.open_settings(); a.root.update(); w=a.settings_win; w.update(); time.sleep(0.3)
grab(w, "d4-settings.png")
try:
    from PIL import Image as _I
    im = _I.open(os.path.join(OUT, "d4-settings.png")).convert("RGB")
    y = 8
    xs = list(range(300, 500, 10))
    vals = [sum(im.getpixel((x, y))) / 3 for x in xs]
    print("标题栏平均亮度:", round(sum(vals) / len(vals), 1))
except Exception as e:
    print("标题栏采样失败", e)
a.on_quit()
