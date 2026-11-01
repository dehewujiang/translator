"""窗口位置回归：拖过后翻译不再弹回右上角；底边框线不被拖拽区盖住。需 Windows 显示环境，否则跳过。"""
import sys
import unittest

try:
    import tkinter as tk
    try:
        _探 = tk.Tk()
        _探.withdraw()
        _探.destroy()
        _显示可用 = True
    except Exception:
        _显示可用 = False
except Exception:
    _显示可用 = False


@unittest.skipUnless(sys.platform == "win32" and _显示可用, "需 Windows 显示环境")
class 位置保持(unittest.TestCase):
    def _起窗(self):
        import app as A
        窗 = A.App.__new__(A.App)
        A.App.__init__(窗)
        窗.root.update()
        self.addCleanup(窗.on_quit)
        return 窗

    def test_拖过后弹新译文不回右上(self):
        窗 = self._起窗()
        窗.popup()
        窗.root.update()
        窗._user_moved = True
        窗.root.geometry("+100+100")
        窗.root.update()
        self.assertEqual((窗.root.winfo_x(), 窗.root.winfo_y()), (100, 100))
        窗.popup()
        窗.root.update()
        self.assertEqual((窗.root.winfo_x(), 窗.root.winfo_y()), (100, 100))

    def test_没拖过弹新译文回右上(self):
        import app as A
        窗 = self._起窗()
        屏宽 = 窗.root.winfo_screenwidth()
        窗.popup()
        窗.root.update()
        self.assertEqual(窗.root.winfo_x(), max(0, 屏宽 - A.WIN_W - 24))
        self.assertEqual(窗.root.winfo_y(), 48)

    def test_底边框线在拖拽区之上(self):
        窗 = self._起窗()
        线 = 窗._bottom_line
        区 = 窗._resize_zone
        self.assertEqual(线.place_info()["y"], str(窗._window_h - 9))
        self.assertEqual(
            int(区.place_info()["y"]) + int(区.place_info()["height"]),
            int(线.place_info()["y"]),
        )
        self.assertEqual(线.cget("cursor"), "size_ns")


if __name__ == "__main__":
    unittest.main()
