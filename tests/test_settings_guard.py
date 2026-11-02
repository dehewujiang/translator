"""配置窗保护：删除要确认、没保存的改动关窗前要问。纯逻辑，不建窗口。"""
import unittest

import translator_settings_window as SW


class _假窗:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class _假列表:
    def curselection(self):
        return (0,)


class _假变量:
    def __init__(self):
        self.text = ""

    def set(self, v):
        self.text = v


def _假自己():
    me = SW.SettingsWindowMixin.__new__(SW.SettingsWindowMixin)
    me.settings_win = _假窗()
    me.prof_list = _假列表()
    me._prof_names = ["备用"]
    me.s_hint_var = _假变量()
    me._s_dirty = False
    return me


class 删除二次确认(unittest.TestCase):
    def test_点取消不删(self):
        me = _假自己()
        记录 = []
        原_删除 = SW.delete_profile
        原_询问 = SW.messagebox.askyesno
        try:
            SW.delete_profile = lambda 名: 记录.append(名)
            SW.messagebox.askyesno = lambda *a, **k: False
            me._settings_delete()
        finally:
            SW.delete_profile = 原_删除
            SW.messagebox.askyesno = 原_询问
        self.assertEqual(记录, [], "点了取消却还是删了")

    def test_点确定才删(self):
        me = _假自己()
        记录 = []

        def _假删(名):
            记录.append(名)
            return "备用"

        me._refresh_settings_list = lambda **k: None
        me._home_status = lambda: None
        原_删除 = SW.delete_profile
        原_询问 = SW.messagebox.askyesno
        try:
            SW.delete_profile = _假删
            SW.messagebox.askyesno = lambda *a, **k: True
            me._settings_delete()
        finally:
            SW.delete_profile = 原_删除
            SW.messagebox.askyesno = 原_询问
        self.assertEqual(记录, ["备用"])


class 关窗提醒(unittest.TestCase):
    def test_有改动点取消不关(self):
        me = _假自己()
        me._s_dirty = True
        原_询问 = SW.messagebox.askyesno
        try:
            SW.messagebox.askyesno = lambda *a, **k: False
            me._settings_close()
        finally:
            SW.messagebox.askyesno = 原_询问
        self.assertFalse(me.settings_win.destroyed, "点了取消却把窗口关了")

    def test_没改动直接关(self):
        me = _假自己()
        me._settings_close()
        self.assertTrue(me.settings_win.destroyed)

    def test_有改动点确定就关(self):
        me = _假自己()
        me._s_dirty = True
        原_询问 = SW.messagebox.askyesno
        try:
            SW.messagebox.askyesno = lambda *a, **k: True
            me._settings_close()
        finally:
            SW.messagebox.askyesno = 原_询问
        self.assertTrue(me.settings_win.destroyed)

    def test_询问框出错时不删(self):
        me = _假自己()
        记录 = []
        原_删除 = SW.delete_profile
        原_询问 = SW.messagebox.askyesno
        try:
            SW.delete_profile = lambda 名: 记录.append(名)

            def _炸(*a, **k):
                raise RuntimeError("对话框坏了")

            SW.messagebox.askyesno = _炸
            me._settings_delete()
        finally:
            SW.delete_profile = 原_删除
            SW.messagebox.askyesno = 原_询问
        self.assertEqual(记录, [], "确认框出错却还是删了")


class 关窗异常路径(unittest.TestCase):
    def test_询问框出错时不关(self):
        me = _假自己()
        me._s_dirty = True
        原_询问 = SW.messagebox.askyesno
        try:
            def _炸(*a, **k):
                raise RuntimeError("对话框坏了")

            SW.messagebox.askyesno = _炸
            me._settings_close()
        finally:
            SW.messagebox.askyesno = 原_询问
        self.assertFalse(me.settings_win.destroyed, "提醒框出错却把窗口关了")


if __name__ == "__main__":
    unittest.main()
