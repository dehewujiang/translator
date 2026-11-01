"""拉伸相关纯函数单测：高度钳制 + 四角图案对称，全离线不建窗口。"""
import unittest

from app import _是否该藏
from translator_layout import WIN_H, _钳制窗口高度
from translator_theme import _corner_kind


class 高度钳制(unittest.TestCase):
    def test_过矮钳到最小高(self):
        self.assertEqual(_钳制窗口高度(100, 1080), WIN_H)

    def test_过高钳到屏幕上限(self):
        上限 = max(WIN_H, min(int(1080 * 0.72), 900))
        self.assertEqual(_钳制窗口高度(2000, 1080), 上限)

    def test_区间内原样返回(self):
        self.assertEqual(_钳制窗口高度(500, 1080), 500)


class 四角对称(unittest.TestCase):
    def test_外角透明内里白(self):
        self.assertEqual(_corner_kind("tl", 0, 0), "transparent")
        self.assertEqual(_corner_kind("tl", 12, 12), "white")
        self.assertEqual(_corner_kind("br", 12, 12), "transparent")
        self.assertEqual(_corner_kind("br", 0, 0), "white")

    def test_四角镜像对称(self):
        for y in range(13):
            for x in range(13):
                基 = _corner_kind("tl", x, y)
                self.assertEqual(_corner_kind("tr", 12 - x, y), 基, f"tr({12 - x},{y})")
                self.assertEqual(_corner_kind("bl", x, 12 - y), 基, f"bl({x},{12 - y})")
                self.assertEqual(_corner_kind("br", 12 - x, 12 - y), 基)


class 钉住逻辑(unittest.TestCase):
    def test_钉住时一律不藏(self):
        self.assertFalse(_是否该藏(True, True, False, False, False))
        self.assertFalse(_是否该藏(True, True, True, True, True))

    def test_没钉且条件全满足才藏(self):
        self.assertTrue(_是否该藏(False, True, False, False, False))

    def test_有任一阻挡就不藏(self):
        self.assertFalse(_是否该藏(False, False, False, False, False))
        self.assertFalse(_是否该藏(False, True, True, False, False))
        self.assertFalse(_是否该藏(False, True, False, True, False))
        self.assertFalse(_是否该藏(False, True, False, False, True))
