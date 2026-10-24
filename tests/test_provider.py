"""模型接口驱动的单元测试。

[INPUT] 假 HTTP 回应与假 SSE 行，不联网。
[OUTPUT] unittest 断言；覆盖非流式、流式回调、取消、状态码、解析失败。
[POS] 守护 translator_provider.chat 的协议边界。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

import translator_provider
from translator_domain import Failure


class 假回应:
    def __init__(self, status=200, payload=None, lines=None):
        self.status_code = status
        self._payload = payload
        self._lines = lines or []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def json(self):
        return self._payload

    def iter_lines(self, decode_unicode=False):
        for 行 in self._lines:
            yield 行


def 流式行(*片段):
    行 = []
    for 片段内容 in 片段:
        行.append('data: {"choices":[{"delta":{"content":"' + 片段内容 + '"}}]}')
    行.append("data: [DONE]")
    return 行


class 请求测试(unittest.TestCase):
    def setUp(self):
        self._原post = translator_provider.requests.post

    def tearDown(self):
        translator_provider.requests.post = self._原post

    def _发请求(self, 回应, **kwargs):
        self.发送 = mock.Mock(return_value=回应)
        translator_provider.requests.post = self.发送
        return translator_provider.chat(
            "https://example.com/v1/",
            "key",
            "model",
            "系统提示",
            "用户内容",
            **kwargs,
        )

    def test_非流式返回去掉两端空白(self):
        结果 = self._发请求(假回应(payload={"choices": [{"message": {"content": " 你好 "}}]}))
        self.assertEqual(结果, "你好")
        self.assertFalse(self.发送.call_args.kwargs["stream"])

    def test_流式逐段回调累计文本(self):
        片段 = []
        结果 = self._发请求(
            假回应(lines=流式行("你", "好")),
            on_chunk=片段.append,
        )
        self.assertEqual(结果, "你好")
        self.assertEqual(片段, ["你", "你好"])
        self.assertTrue(self.发送.call_args.kwargs["stream"])

    def test_流式忽略空行坏行和事件行(self):
        行 = [
            "",
            "event: ping",
            "data: not-json",
            'data: {"choices":[{"delta":{"content":"好"}}]}',
            "data: [DONE]",
            'data: {"choices":[{"delta":{"content":"不该出现"}}]}',
        ]
        片段 = []
        结果 = self._发请求(假回应(lines=行), on_chunk=片段.append)
        self.assertEqual(结果, "好")
        self.assertEqual(片段, ["好"])

    def test_取消后不再继续读流(self):
        片段 = []
        取消 = mock.Mock(return_value=False)
        取消.side_effect = [False, True, True]

        结果 = self._发请求(
            假回应(lines=流式行("你", "好")),
            on_chunk=片段.append,
            cancel=取消,
        )
        self.assertEqual(结果, "你")
        self.assertEqual(片段, ["你"])

    def test_401抛密钥失败(self):
        with self.assertRaises(Failure) as 捕获:
            self._发请求(假回应(status=401, payload={}))
        self.assertEqual(捕获.exception.kind, "auth")
        self.assertFalse(捕获.exception.retryable)

    def test_网络异常抛网络失败(self):
        self.发送 = mock.Mock(side_effect=translator_provider.requests.RequestException("断网"))
        translator_provider.requests.post = self.发送
        with self.assertRaises(Failure) as 捕获:
            translator_provider.chat("https://x/v1", "k", "m", "s", "u")
        self.assertEqual(捕获.exception.kind, "network")
        self.assertTrue(捕获.exception.retryable)

    def test_返回结构不对抛解析失败(self):
        with self.assertRaises(Failure) as 捕获:
            self._发请求(假回应(payload={"choices": []}))
        self.assertEqual(捕获.exception.kind, "parse")

    def test_接口地址末尾斜杠不会拼出双斜杠(self):
        self._发请求(假回应(payload={"choices": [{"message": {"content": "好"}}]}))
        地址 = self.发送.call_args.args[0]
        self.assertEqual(地址, "https://example.com/v1/chat/completions")

    def test_内容为空返回空串(self):
        结果 = self._发请求(假回应(payload={"choices": [{"message": {"content": None}}]}))
        self.assertEqual(结果, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
