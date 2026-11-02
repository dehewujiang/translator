"""配置窗列表配色：正在用=蓝字+✓，选中=浅蓝底；断言真实颜色，不只断言"没报错"。需显示环境。"""
import sys
import unittest

import translator_scale  # noqa: F401  先声明 DPI，再建 Tk（测试卫生）

try:
    import tkinter as tk

    _探 = tk.Tk()
    _探.withdraw()
    _探.destroy()
    _显示可用 = True
except Exception:
    _显示可用 = False

from translator_settings_window import SettingsWindowMixin
from translator_theme import ACCENT_TEXT, FAINT_FG, MAIN_FG, SELECT_FG_ACCENT


@unittest.skipUnless(sys.platform == "win32" and _显示可用, "需 Windows 显示环境")
class 列表配色(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.lb = tk.Listbox(self.root)
        for 标签 in ("✓ a", "b", "c（未配置）"):
            self.lb.insert("end", 标签)
        self.me = SettingsWindowMixin.__new__(SettingsWindowMixin)
        self.me.prof_list = self.lb
        self.me._cur_index = 0
        self.me._row_state = [("a", True), ("b", True), ("c", False)]
        self.addCleanup(self.root.destroy)

    def _前景(self, i):
        return str(self.lb.itemcget(i, "foreground")).lower()

    def _选中字色(self):
        return str(self.lb.cget("selectforeground")).lower()

    def test_选中正在用时文字是蓝色(self):
        self.lb.selection_set(0)
        self.me._apply_list_style()
        self.assertEqual(self._前景(0), ACCENT_TEXT.lower(), "正在用那行没有蓝色")
        self.assertEqual(self._选中字色(), SELECT_FG_ACCENT.lower(), "选中态把蓝色盖掉了")

    def test_选中别的方案时正在用仍蓝_其余正常(self):
        self.lb.selection_set(1)
        self.me._apply_list_style()
        self.assertEqual(self._选中字色(), MAIN_FG.lower())
        self.assertEqual(self._前景(0), ACCENT_TEXT.lower(), "正在用那行丢了蓝色")
        self.assertEqual(self._前景(2), FAINT_FG.lower(), "未配置那行没有变浅")

if __name__ == "__main__":
    unittest.main()
