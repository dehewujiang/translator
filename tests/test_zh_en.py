"""中译英通道离线测试：mock _call_api，零网络；不读真实配置。

[INPUT] 受控 load_config（setUp 注入）+ 假 _call_api；不读真实 config.json。
[OUTPUT] unittest 断言；覆盖自定义提示词、缺省/空白回退默认、run_intent 分派。
[POS] 守护 translator_core.translate_zh_to_en 与 run_intent 的 zh 分支。
[PROTOCOL] 运行：python -m unittest tests.test_zh_en -v
"""
import json
import unittest

import translator_core as C
from translator_domain import EMPTY, Failure, Intent, Translation


class 中译英(unittest.TestCase):
    def setUp(self):
        self._原接口 = C._call_api
        self._原读配置 = C.load_config
        # 不读、不改真实的 config.json；默认受控配置显式给出默认中译英指令
        C.load_config = lambda: {"prompt": "受控英译中提示", "prompt_zh2en": C.中译英指令}

    def tearDown(self):
        C._call_api = self._原接口
        C.load_config = self._原读配置

    def test_固定指令透传并返回译文(self):
        # 受控配置：prompt_zh2en 为默认中译英指令
        self.assertEqual(C.load_config()["prompt_zh2en"], C.中译英指令)
        抓到 = {}

        def 假调用(系统提示, 用户内容, on_chunk=None, cancel=None):
            抓到["system"] = 系统提示
            抓到["user"] = 用户内容
            抓到["on_chunk"] = on_chunk
            抓到["cancel"] = cancel
            return "Hello"

        C._call_api = 假调用
        try:
            结果 = C.translate_zh_to_en("你好", on_chunk="cb", cancel="cc")
        finally:
            C._call_api = self._原接口
        self.assertEqual(结果, "Hello")
        self.assertEqual(抓到["user"], "你好")
        self.assertEqual(抓到["system"], C.中译英指令)
        self.assertEqual(抓到["on_chunk"], "cb")
        self.assertEqual(抓到["cancel"], "cc")

    def test_自定义提示词透传(self):
        C.load_config = lambda: {"prompt": "中->英", "prompt_zh2en": "自定义中译英"}
        抓到 = {}

        def 假调用(系统提示, 用户内容, on_chunk=None, cancel=None):
            抓到["system"] = 系统提示
            抓到["user"] = 用户内容
            return "Hello"

        C._call_api = 假调用
        try:
            结果 = C.translate_zh_to_en("你好")
        finally:
            C._call_api = self._原接口
        self.assertEqual(结果, "Hello")
        self.assertEqual(抓到["system"], "自定义中译英")
        self.assertEqual(抓到["user"], "你好")

    def test_缺省提示词回退默认(self):
        # 受控配置：缺 prompt_zh2en 键 -> 用 shipped 默认
        C.load_config = lambda: {"prompt": "中->英"}
        抓到 = {}
        C._call_api = lambda 系统提示, 用户内容, on_chunk=None, cancel=None: (
            抓到.setdefault("system", 系统提示),
            "Hello",
        )[1]
        try:
            C.translate_zh_to_en("你好")
        finally:
            C._call_api = self._原接口
        self.assertEqual(抓到["system"], C.中译英指令)

    def test_空白字符串回退默认(self):
        C.load_config = lambda: {"prompt_zh2en": "   "}
        抓到 = {}
        C._call_api = lambda 系统提示, 用户内容, on_chunk=None, cancel=None: (
            抓到.setdefault("system", 系统提示),
            "Hello",
        )[1]
        try:
            C.translate_zh_to_en("你好")
        finally:
            C._call_api = self._原接口
        self.assertEqual(抓到["system"], C.中译英指令)

    def test_空文本直接返回空不调接口(self):
        被调 = []
        C._call_api = lambda *a, **k: (被调.append(1), "x")[1]
        try:
            self.assertEqual(C.translate_zh_to_en("   "), "")
            self.assertEqual(C.translate_zh_to_en(""), "")
            self.assertEqual(C.translate_zh_to_en(None), "")
        finally:
            C._call_api = self._原接口
        self.assertEqual(被调, [])

    def test_run_intent_zh返回英文译文(self):
        C._call_api = lambda *a, **k: "Hello"
        try:
            结果 = C.run_intent(Intent("zh", "你好"))
        finally:
            C._call_api = self._原接口
        self.assertIsInstance(结果, Translation)
        self.assertEqual(结果.text, "Hello")

    def test_run_intent_zh使用自定义提示词(self):
        C.load_config = lambda: {"prompt": "中->英", "prompt_zh2en": "自定义中译英"}
        抓到 = {}

        def 假调用(系统提示, 用户内容, on_chunk=None, cancel=None):
            抓到["system"] = 系统提示
            抓到["user"] = 用户内容
            return "Hello"

        C._call_api = 假调用
        try:
            结果 = C.run_intent(Intent("zh", "你好"))
        finally:
            C._call_api = self._原接口
        self.assertIsInstance(结果, Translation)
        self.assertEqual(结果.text, "Hello")
        self.assertEqual(抓到["system"], "自定义中译英")
        self.assertEqual(抓到["user"], "你好")

    def test_run_intent_zh空返回EMPTY失败(self):
        结果 = C.run_intent(Intent("zh", "   "))
        self.assertIsInstance(结果, Failure)
        self.assertEqual(结果.kind, EMPTY)

    def test_空失败消息不再说英文(self):
        结果 = C.run_intent(Intent("zh", ""))
        self.assertIsInstance(结果, Failure)
        self.assertEqual(结果.kind, EMPTY)
        self.assertNotIn("英文", 结果.message)

    def test_word_text路径不受影响(self):
        # 受控配置：text 走 prompt，word 走单词指令（不受 prompt_zh2en 影响）
        C.load_config = lambda: {"prompt": "英译中自定义", "prompt_zh2en": "中译英自定义"}
        抓到 = {}

        def 假调用(系统提示, 用户内容, on_chunk=None, cancel=None):
            if 系统提示 == C.单词指令:
                return json.dumps({
                    "word": "hi",
                    "uk": "/haɪ/",
                    "us": "/haɪ/",
                    "senses": [{"pos": "int.", "defs": ["你好"],
                                "examples": [{"en": "Hi!", "zh": "你好！"}]}],
                })
            抓到[用户内容] = 系统提示
            return "你好"

        C._call_api = 假调用
        try:
            词 = C.run_intent(Intent("word", "hi"))
            文 = C.run_intent(Intent("text", "hello world"))
        finally:
            C._call_api = self._原接口
        self.assertEqual(词.word, "hi")
        self.assertIsInstance(文, Translation)
        self.assertEqual(文.text, "你好")
        # Intent("text") 仍用 prompt
        self.assertEqual(抓到.get("hello world"), "英译中自定义")
        # Intent("word") 仍用单词指令
        self.assertNotIn("中译英自定义", 抓到.values())


if __name__ == "__main__":
    unittest.main()
