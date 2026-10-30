"""窗口高度自适应的纯计算测试。

[INPUT] 源文本行数、译文行数、行高、屏幕高。
[OUTPUT] unittest 断言；不创建窗口。
[POS] 守护 translator_layout._算窗口高度 的上下限。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import unittest

import translator_layout
import translator_theme


class 窗口高度测试(unittest.TestCase):
    def test_短内容保持最小高度(self):
        self.assertEqual(translator_layout._算窗口高度(1, 1, 20, 1080), translator_layout.WIN_H)

    def test_长内容按行数变高(self):
        高度 = translator_layout._算窗口高度(8, 20, 20, 1080)
        self.assertGreater(高度, translator_layout.WIN_H)
        self.assertLessEqual(高度, int(1080 * 0.72))

    def test_超长内容不超过屏幕上限(self):
        self.assertLessEqual(translator_layout._算窗口高度(50, 200, 20, 1080), int(1080 * 0.72))

    def test_小屏也不低于最小高度(self):
        self.assertEqual(translator_layout._算窗口高度(1, 1, 20, 400), translator_layout.WIN_H)

    def test_行数为零当作一行(self):
        self.assertEqual(translator_layout._算窗口高度(0, 0, 20, 1080), translator_layout.WIN_H)

    def test_原文高度等于文本加18像素(self):
        self.assertEqual(translator_layout._算原文高度(200, 17, 19), 17 + 6 + 200 + 18)

    def test_空原文至少留一行加18像素(self):
        self.assertEqual(translator_layout._算原文高度(0, 17, 19), 17 + 6 + 19 + 18)


class 无边框卡片节奏测试(unittest.TestCase):
    def test_1行内容回最小高度(self):
        self.assertEqual(
            translator_layout._算窗口高度(1, 1, 20, 1080), translator_layout.WIN_H
        )

    def test_6行译文撑高窗口(self):
        self.assertGreater(
            translator_layout._算窗口高度(3, 6, 20, 1080), translator_layout.WIN_H
        )

    def test_超长内容仍卡屏幕上限(self):
        self.assertLessEqual(
            translator_layout._算窗口高度(50, 200, 20, 1080), int(1080 * 0.72)
        )

    def test_固定铬等于文档化垂直节奏之和(self):
        L = translator_layout
        self.assertEqual(
            L.FIXED_CHROME,
            L.MARGIN * 2
            + L.TOP_PAD
            + L.HEADER_H
            + L.GAP_AFTER_HEADER
            + L.GAP_BEFORE_DIV
            + L.DIV_H
            + L.GAP_AFTER_DIV
            + L.LABEL_H
            + L.GAP_AFTER_LABEL
            + L.GAP_BEFORE_FOOTER
            + L.FOOTER_H
            + L.BOTTOM_PAD,
        )

    def test_顶栏与原文行高度等于图标按钮尺寸(self):
        self.assertEqual(translator_layout.HEADER_H, translator_theme.ICON_BTN)
        self.assertEqual(translator_layout.LABEL_H, translator_theme.ICON_BTN)

    def test_固定铬等于203(self):
        self.assertEqual(translator_layout.FIXED_CHROME, 203)


if __name__ == "__main__":
    unittest.main(verbosity=2)
