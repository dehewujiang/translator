"""中文自动识别的单元测试（离线）。

[INPUT] 纯文本；不联网、不读写真配置。
[OUTPUT] unittest 断言；覆盖纯中文、混合中英、英文单词/句子、空/None、纯标点。
[POS] 守护 translator_domain.contains_chinese 与 build_intent 的 "zh" 契约。
[PROTOCOL] 运行：python -m unittest tests.test_zh_detect -v
"""

import unittest

from translator_domain import build_intent, contains_chinese


class 中文识别测试(unittest.TestCase):
    def test_纯中文返回真(self):
        self.assertTrue(contains_chinese("你好"))

    def test_混合中英返回真(self):
        self.assertTrue(contains_chinese("这个bug怎么修"))

    def test_扩展A区返回真(self):
        self.assertTrue(contains_chinese("㐀"))

    def test_纯英文单词返回假(self):
        self.assertFalse(contains_chinese("hello"))

    def test_纯英文句子返回假(self):
        self.assertFalse(contains_chinese("good morning"))

    def test_空字符串返回假(self):
        self.assertFalse(contains_chinese(""))

    def test_None返回假(self):
        self.assertFalse(contains_chinese(None))

    def test_纯标点返回假(self):
        self.assertFalse(contains_chinese(".,!?"))


class 意图分派测试(unittest.TestCase):
    def test_纯中文走zh(self):
        意图 = build_intent("你好")
        self.assertEqual(意图.kind, "zh")
        self.assertEqual(意图.text, "你好")

    def test_混合中英走zh(self):
        意图 = build_intent("这个bug怎么修")
        self.assertEqual(意图.kind, "zh")

    def test_英文单词仍走word(self):
        self.assertEqual(build_intent("hello").kind, "word")

    def test_英文句子仍走text(self):
        self.assertEqual(build_intent("good morning").kind, "text")

    def test_空文本仍走text(self):
        意图 = build_intent("   ")
        self.assertEqual(意图.kind, "text")
        self.assertEqual(意图.text, "")

    def test_None仍走text(self):
        意图 = build_intent(None)
        self.assertEqual(意图.kind, "text")
        self.assertEqual(意图.text, "")

    def test_纯标点仍走text(self):
        self.assertEqual(build_intent(".,!?").kind, "text")


if __name__ == "__main__":
    unittest.main(verbosity=2)
