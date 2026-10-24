"""窗口高度自适应的纯计算测试。

[INPUT] 源文本行数、译文行数、行高、屏幕高。
[OUTPUT] unittest 断言；不创建窗口。
[POS] 守护 app._算窗口高度 的上下限。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import unittest

import app


class 窗口高度测试(unittest.TestCase):
    def test_短内容保持最小高度(self):
        self.assertEqual(app._算窗口高度(1, 1, 20, 1080), app.WIN_H)

    def test_长内容按行数变高(self):
        高度 = app._算窗口高度(8, 20, 20, 1080)
        self.assertGreater(高度, app.WIN_H)
        self.assertLessEqual(高度, int(1080 * 0.72))

    def test_超长内容不超过屏幕上限(self):
        self.assertLessEqual(app._算窗口高度(50, 200, 20, 1080), int(1080 * 0.72))

    def test_小屏也不低于最小高度(self):
        self.assertEqual(app._算窗口高度(1, 1, 20, 400), app.WIN_H)

    def test_行数为零当作一行(self):
        self.assertEqual(app._算窗口高度(0, 0, 20, 1080), app.WIN_H)


if __name__ == "__main__":
    unittest.main(verbosity=2)
