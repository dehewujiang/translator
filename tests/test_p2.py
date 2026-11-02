"""P2 行为测试：钥匙显隐、测试连接成功/失败、深色/浅色调色板对比度。不建窗口。"""
import time
import unittest

import translator_settings_window as SW
import translator_theme as T


class _假框:
    def __init__(self, 值=""):
        self.值 = 值
        self.配置 = {}

    def configure(self, **k):
        self.配置.update(k)


class _假变量:
    def __init__(self, 值=""):
        self.值 = 值

    def get(self):
        return self.值

    def set(self, v):
        self.值 = v


class _假窗:
    def after(self, _ms, fn):
        fn()


def _假自己(url="https://x/v1", key="k", model="m"):
    me = SW.SettingsWindowMixin.__new__(SW.SettingsWindowMixin)
    me.s_url_var = _假变量(url)
    me.s_key_var = _假变量(key)
    me.s_model_var = _假变量(model)
    me.s_hint_var = _假变量("")
    me.settings_win = _假窗()
    me.test_btn = _假框()
    me.s_key_entry = _假框()
    me.key_toggle = _假框()
    me._key_shown = False
    return me


class 钥匙显隐(unittest.TestCase):
    def test_点一下显示再点一下隐藏(self):
        me = _假自己()
        me._toggle_key_show()
        self.assertEqual(me.s_key_entry.配置.get("show"), "")
        self.assertEqual(me.key_toggle.配置.get("text"), "隐藏")
        me._toggle_key_show()
        self.assertEqual(me.s_key_entry.配置.get("show"), "*")
        self.assertEqual(me.key_toggle.配置.get("text"), "显示")


class 测试连接(unittest.TestCase):
    def _跑(self, me, 耗时上限=2.0):
        起 = time.time()
        while time.time() - 起 < 耗时上限:
            if "测试" not in str(me.s_hint_var.值):
                return me.s_hint_var.值
            time.sleep(0.01)
        return me.s_hint_var.值

    def test_成功时给正常提示(self):
        me = _假自己()
        原 = SW._接口chat
        try:
            SW._接口chat = lambda *a, **k: "正常"
            me._settings_test()
            结果 = self._跑(me)
        finally:
            SW._接口chat = 原
        self.assertIn("连接正常", 结果)
        self.assertEqual(me.test_btn.配置.get("state"), "normal")

    def test_失败时给失败提示(self):
        me = _假自己()
        原 = SW._接口chat

        def _炸(*a, **k):
            raise RuntimeError("超时")

        try:
            SW._接口chat = _炸
            me._settings_test()
            结果 = self._跑(me)
        finally:
            SW._接口chat = 原
        self.assertIn("连接失败", 结果)

    def test_缺字段不发请求(self):
        me = _假自己(key="")
        调用 = []
        原 = SW._接口chat
        try:
            SW._接口chat = lambda *a, **k: 调用.append(1) or "正常"
            me._settings_test()
        finally:
            SW._接口chat = 原
        self.assertEqual(调用, [])
        self.assertIn("三样都填好", me.s_hint_var.值)


def _对比度(a, b):
    def 亮度(h):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    la, lb = 亮度(a), 亮度(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class 调色板对比度(unittest.TestCase):
    def test_当前模式文字和图标够清楚(self):
        self.assertGreaterEqual(_对比度(T.FAINT_FG, T.CARD_BG), 4.5)
        self.assertGreaterEqual(_对比度(T.SUB_FG, T.CARD_BG), 4.5)
        self.assertGreaterEqual(_对比度(T.MAIN_FG, T.CARD_BG), 7.0)
        self.assertGreaterEqual(_对比度(T.ICON_FG, T.CARD_BG), 3.0)
        self.assertGreaterEqual(_对比度(T.TIP_FG, T.TIP_BG), 4.5)
        self.assertGreaterEqual(_对比度(T.ACCENT_TEXT, T.CARD_BG), 4.5)

    def test_界面不许用品红色(self):
        for 名 in ("CARD_BG", "MAIN_FG", "SUB_FG", "FAINT_FG", "LINE", "EDGE",
                   "HOVER_BG", "ICON_FG", "PAGE_BG", "SELECT_BG", "TIP_BG"):
            self.assertNotEqual(getattr(T, 名).upper(), "#FF00FE", 名)


if __name__ == "__main__":
    unittest.main()
