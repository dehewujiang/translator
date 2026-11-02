"""P2 截图：空状态 / 长译文滚动条 / 钥匙显隐 / 测试连接按钮。"""
import ctypes, os, sys, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE); os.chdir(BASE)
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception: pass
import app as appmod
from PIL import ImageGrab
appmod.App._start_trigger = lambda s: None
appmod.App._start_tray = lambda s: None
appmod.App._start_singleton_server = lambda s: None
OUT = os.path.join(BASE, "evidence", "audit")
os.makedirs(OUT, exist_ok=True)

def grab(root, name):
    hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
    r = (ctypes.c_long * 4)(); ctypes.windll.user32.GetWindowRect(hwnd, r)
    im = ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3]))
    im.save(os.path.join(OUT, name)); print("saved", name, im.size)

a = appmod.App(); a.root.deiconify(); a._place_top_right(); a.root.update()
a.popup(); a.root.update(); time.sleep(0.2)
grab(a.root, "06-empty.png")
print("空状态可见:", bool(a.empty_hint.winfo_ismapped()))

a.src_text.delete("1.0", "end"); a.src_text.insert("1.0", "Long text")
a._dst_set("这是一段很长的译文。" * 40)
a.root.update(); time.sleep(0.4); a.root.update()
grab(a.root, "07-scroll.png")
print("滚动条可见:", bool(a.dst_bar.winfo_ismapped()), "yview=", a.dst_text.yview())

a.open_settings(); a.root.update(); w = a.settings_win; w.update(); time.sleep(0.3)
hwnd = ctypes.windll.user32.GetAncestor(w.winfo_id(), 2)
r = (ctypes.c_long * 4)(); ctypes.windll.user32.GetWindowRect(hwnd, r)
ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3])).save(os.path.join(OUT, "08-settings-p2.png"))
print("saved 08-settings-p2.png")
a.on_quit()
