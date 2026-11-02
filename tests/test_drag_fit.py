"""拖矮回归：底边手柄往上拖到底，翻译按钮不能被挤出卡片 / 压没。需 Windows 显示环境，否则跳过。"""
import sys
import unittest
from types import SimpleNamespace

from translator_layout import FOOTER_H, MARGIN
from translator_scale import px

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
class 拖矮不压按钮(unittest.TestCase):
    def _起窗(self):
        import app as A

        A.App._start_trigger = lambda self: None
        A.App._start_tray = lambda self: None
        A.App._start_singleton_server = lambda self: None
        窗 = A.App.__new__(A.App)
        A.App.__init__(窗)
        窗.root.update()
        self.addCleanup(窗.on_quit)
        return 窗

    def _拖到(self, 窗, 位移):
        起点 = float(窗.root.winfo_rooty() + 窗._window_h)
        窗._grip_press(SimpleNamespace(y_root=起点))
        窗._grip_drag(SimpleNamespace(y_root=起点 + 位移))
        窗.root.update()

    def test_往上拖到底底栏仍在卡片内(self):
        窗 = self._起窗()
        窗.dst_text.delete("1.0", "end")
        窗.dst_text.insert("1.0", "这是一段用来撑高译文区的中文内容。" * 6)
        窗.src_text.delete("1.0", "end")
        窗.src_text.insert("1.0", "Copy this English, tap Ctrl.")
        窗.popup()
        窗.root.update()
        窗._refit()
        窗.root.update()

        self._拖到(窗, -400)

        高 = 窗.root.winfo_height()
        底 = MARGIN + 窗.footer.winfo_y() + 窗.footer.winfo_height()
        self.assertLessEqual(底, 高, f"底栏底边 {底} 超出窗口 {高}")
        self.assertEqual(窗.footer.winfo_height(), FOOTER_H)
        self.assertEqual(窗.translate_btn.winfo_height(), FOOTER_H)

    def test_拖矮再拖高原文框恢复(self):
        窗 = self._起窗()
        窗.popup()
        窗.root.update()
        窗._refit()
        窗.root.update()
        自然 = int(窗.src_text.cget("height"))

        self._拖到(窗, -400)
        self._拖到(窗, 400)

        self.assertEqual(int(窗.src_text.cget("height")), 自然)

    def test_译文区只读且程序还能写入(self):
        窗 = self._起窗()
        self.assertEqual(str(窗.dst_text.cget("state")), "disabled")
        窗._dst_set("测试内容")
        self.assertEqual(窗.dst_text.get("1.0", "end-1c"), "测试内容")
        self.assertEqual(str(窗.dst_text.cget("state")), "disabled")

    def test_左右拖宽有下限且底栏不越界(self):
        窗 = self._起窗()
        窗.popup()
        窗.root.update()
        窗._refit()
        窗.root.update()
        起 = 窗.root.winfo_width()

        x = float(窗.root.winfo_rootx() + 起)
        窗._width_press_r(SimpleNamespace(x_root=x))
        窗._width_drag(SimpleNamespace(x_root=x + 120))
        窗.root.update()
        self.assertGreater(窗.root.winfo_width(), 起)

        x2 = float(窗.root.winfo_rootx() + 窗.root.winfo_width())
        窗._width_press_r(SimpleNamespace(x_root=x2))
        窗._width_drag(SimpleNamespace(x_root=x2 - 2000))
        窗.root.update()
        self.assertEqual(窗.root.winfo_width(), px(320))
        窗._width_release()
        窗.root.update()

        底 = MARGIN + 窗.footer.winfo_y() + 窗.footer.winfo_height()
        self.assertLessEqual(底, 窗.root.winfo_height())


if __name__ == "__main__":
    unittest.main()
