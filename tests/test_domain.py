"""意图与结果契约的单元测试。

[INPUT] 纯文本；translator_core._call_api 被替换成假函数，不联网。
[OUTPUT] unittest 断言；覆盖词句判定、异常收敛、结果分派、失败分类。
[POS] 守护 translator_domain 与 translator_core.run_intent 的边界契约。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import unittest

import translator_core
from translator_domain import (
    Definition,
    Failure,
    Intent,
    Translation,
    build_intent,
    failure_for_status,
)


class 词句判定测试(unittest.TestCase):
    def test_普通单词走词典(self):
        self.assertEqual(build_intent("king").kind, "word")

    def test_两边标点会去掉(self):
        self.assertEqual(build_intent("  hello,  ").kind, "word")

    def test_句子走翻译(self):
        self.assertEqual(build_intent("good morning").kind, "text")

    def test_撇号和连字符算单词(self):
        self.assertEqual(build_intent("don't").kind, "word")
        self.assertEqual(build_intent("well-known").kind, "word")

    def test_数字不是单词(self):
        self.assertEqual(build_intent("123").kind, "text")

    def test_中文不是单词(self):
        self.assertEqual(build_intent("中文").kind, "text")

    def test_单个字母不算单词(self):
        self.assertEqual(build_intent("a").kind, "text")

    def test_空文本保留为空(self):
        意图 = build_intent("   ")
        self.assertEqual(意图.kind, "text")
        self.assertEqual(意图.text, "")


class 失败分类测试(unittest.TestCase):
    def test_401是密钥问题且不可重试(self):
        失败 = failure_for_status(401)
        self.assertEqual(失败.kind, "auth")
        self.assertFalse(失败.retryable)

    def test_404是地址或模型问题(self):
        self.assertEqual(failure_for_status(404).kind, "endpoint")

    def test_429是限流且可重试(self):
        失败 = failure_for_status(429)
        self.assertEqual(失败.kind, "rate_limit")
        self.assertTrue(失败.retryable)

    def test_500是服务端问题且可重试(self):
        失败 = failure_for_status(500)
        self.assertEqual(失败.kind, "server")
        self.assertTrue(失败.retryable)

    def test_其他状态码归服务端(self):
        self.assertEqual(failure_for_status(418).kind, "server")


class 结果分派测试(unittest.TestCase):
    def setUp(self):
        self._原接口 = translator_core._call_api
        self._原读配置 = translator_core.load_config
        # 不读、不改真实的 config.json
        translator_core.load_config = lambda: {"prompt": "翻译成中文"}

    def tearDown(self):
        translator_core._call_api = self._原接口
        translator_core.load_config = self._原读配置

    def test_空文本不调接口(self):
        调用记录 = []

        def 假接口(*_args, **_kwargs):
            调用记录.append(1)
            return "不该被调用"

        translator_core._call_api = 假接口
        结果 = translator_core.run_intent(Intent("text", ""))
        self.assertIsInstance(结果, Failure)
        self.assertEqual(结果.kind, "empty")
        self.assertEqual(调用记录, [])

    def test_句子返回译文对象(self):
        translator_core._call_api = lambda _system, _user, **_kwargs: "你好"
        结果 = translator_core.run_intent(Intent("text", "hello"))
        self.assertIsInstance(结果, Translation)
        self.assertEqual(结果.text, "你好")

    def test_单词返回词典对象(self):
        载荷 = (
            '{"word":"king","uk":"/kɪŋ/","us":"/kɪŋ/",'
            '"senses":[{"pos":"n.","defs":["国王"],"examples":[]}]}'
        )
        translator_core._call_api = lambda _system, _user, **_kwargs: 载荷
        结果 = translator_core.run_intent(Intent("word", "king"))
        self.assertIsInstance(结果, Definition)
        self.assertEqual(结果.word, "king")
        self.assertEqual(结果.senses[0]["pos"], "n.")

    def test_词典带代码围栏也能解析(self):
        载荷 = (
            '```json\n{"word":"king","uk":"","us":"",'
            '"senses":[{"pos":"n.","defs":["国王"]}]}\n```'
        )
        translator_core._call_api = lambda _system, _user, **_kwargs: 载荷
        结果 = translator_core.run_intent(Intent("word", "king"))
        self.assertIsInstance(结果, Definition)

    def test_已知失败原样传递(self):
        def 假接口(*_args, **_kwargs):
            raise Failure(kind="network", message="网络连接失败", retryable=True)

        translator_core._call_api = 假接口
        结果 = translator_core.run_intent(Intent("text", "hello"))
        self.assertIsInstance(结果, Failure)
        self.assertEqual(结果.kind, "network")
        self.assertTrue(结果.retryable)

    def test_未知异常收敛成失败对象(self):
        def 假接口(*_args, **_kwargs):
            raise RuntimeError("炸了")

        translator_core._call_api = 假接口
        结果 = translator_core.run_intent(Intent("text", "hello"))
        self.assertIsInstance(结果, Failure)
        self.assertEqual(结果.kind, "unknown")
        self.assertIn("炸了", 结果.message)

    def test_词典返回格式不对时保留原文(self):
        translator_core._call_api = lambda _system, _user, **_kwargs: "不是 json"
        with self.assertRaises(Failure) as 捕获:
            translator_core.lookup_word("king")
        self.assertEqual(捕获.exception.kind, "parse")
        self.assertEqual(捕获.exception.raw, "不是 json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
