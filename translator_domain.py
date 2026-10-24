"""意图与结果的契约层：只回答“要做什么”和“做出来是什么”。

[INPUT] 纯文本（来自剪贴板/输入框）；HTTP 状态码（来自 translator_core）。
[OUTPUT] Intent / Translation / Definition / Failure 四种数据结构。
[POS] 最底层；被 translator_core 与 app.py 依赖；不 import 本项目任何模块。
[PROTOCOL] Intent.kind 只有 "word" | "text"；Failure.kind 见 4.3 分类表。
"""

from dataclasses import dataclass, field
from typing import Any

WORD = "word"
TEXT = "text"

# 失败分类：界面按这个决定给什么提示，不解析错误文字
CONFIG = "config"
AUTH = "auth"
ENDPOINT = "endpoint"
RATE_LIMIT = "rate_limit"
SERVER = "server"
NETWORK = "network"
PARSE = "parse"
EMPTY = "empty"
UNKNOWN = "unknown"

# 只去两头的标点，不动词中间的撇号和连字符
_两端标点 = ".,!?;:\"'()[]"


@dataclass
class Intent:
    """用户这次要什么。kind 只决定走词典还是翻译。"""

    kind: str
    text: str


@dataclass
class Translation:
    """一句/一段译文。"""

    text: str


@dataclass
class Definition:
    """一个单词的词典结果。senses 暂保持为原始结构（见设计文档 D4）。"""

    word: str = ""
    uk: str = ""
    us: str = ""
    senses: list[dict[str, Any]] = field(default_factory=list)
    raw: str = ""


@dataclass
class Failure(Exception):
    """失败结果。既是返回值，也是异常：core 内部可以直接抛，边界统一收敛。"""

    kind: str
    message: str
    retryable: bool = False
    raw: str = ""

    def __str__(self) -> str:
        return self.message


def is_single_word(text) -> bool:
    """是不是单个英文单词：只含字母连字符撇号且中间没空格。"""
    片段 = str(text or "").strip().strip(_两端标点)
    if not 片段 or " " in 片段 or "\n" in 片段:
        return False
    for 字 in 片段:
        if not (字.isalpha() and ord(字) < 128 or 字 in "-'"):
            return False
    return 2 <= len(片段) <= 30


def build_intent(text) -> Intent:
    """把原文变成意图；词句判断只在这里做一次。"""
    原文 = str(text or "").strip()
    return Intent(WORD if is_single_word(原文) else TEXT, 原文)


def failure_for_status(status: int, raw: str = "") -> Failure:
    """把 HTTP 状态码翻译成带分类的失败，界面不用再认数字。"""
    码 = str(status)
    if status in (401, 403):
        return Failure(AUTH, f"密钥无效或已过期（{码}），请检查密钥是否正确。", False, raw)
    if status == 404:
        return Failure(ENDPOINT, "接口地址或模型不对（404），请检查地址和模型是否正确。", False, raw)
    if status == 429:
        return Failure(RATE_LIMIT, "请求太频繁（429），请稍后重试。", True, raw)
    if status >= 500:
        return Failure(SERVER, f"翻译失败（错误码 {码}），请稍后重试。", True, raw)
    return Failure(SERVER, f"翻译失败（错误码 {码}），请稍后重试。", False, raw)


def classify_exception(错误: BaseException) -> Failure:
    """未分类异常统一收敛，界面只面对 Failure 一种类型。"""
    if isinstance(错误, Failure):
        return 错误
    return Failure(UNKNOWN, str(错误) or "翻译失败，请稍后重试。")
