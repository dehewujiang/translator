"""模型接口驱动：把一次请求发出去，把回来的字吐出来。

[INPUT] 地址/密钥/模型 + 系统提示 + 用户内容 + 可选片段回调与取消信号。
[OUTPUT] 完整文本；流式时每收到一段就回调累计文本。
[POS] 能力层最外层；被 translator_core 调用，不认识界面与配置结构。
[PROTOCOL] OpenAI 兼容 POST {base_url}/chat/completions；stream=true 时按 SSE 的 data: 行解析。
"""

import json

import requests

from translator_domain import NETWORK, PARSE, Failure, failure_for_status


def chat(接口地址, 密钥, 模型, 系统提示, 用户内容, on_chunk=None, cancel=None):
    """发一次请求。给了 on_chunk 就走流式，返回完整文本。"""
    地址 = str(接口地址 or "").strip().rstrip("/") + "/chat/completions"
    请求头 = {
        "Authorization": "Bearer " + 密钥,
        "Content-Type": "application/json",
    }
    请求体 = {
        "model": 模型,
        "messages": [
            {"role": "system", "content": 系统提示},
            {"role": "user", "content": 用户内容},
        ],
    }
    流式 = on_chunk is not None
    if 流式:
        请求体["stream"] = True
    try:
        回应 = requests.post(
            地址,
            headers=请求头,
            json=请求体,
            timeout=(10, 60),
            stream=流式,
        )
    except requests.RequestException:
        raise Failure(NETWORK, "网络连接失败，请检查网络后重试。", True)
    with 回应:
        if 回应.status_code != 200:
            raise failure_for_status(回应.status_code)
        if 流式:
            return _读流(回应, on_chunk, cancel)
        return _读整段(回应)


def _读整段(回应):
    try:
        数据 = 回应.json()
        内容 = 数据["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise Failure(PARSE, "翻译结果解析失败，请稍后重试。")
    if 内容 is None:
        return ""
    return str(内容).strip()


def _读流(回应, on_chunk, cancel):
    累计 = ""
    for 原始行 in 回应.iter_lines(decode_unicode=False):
        if cancel is not None and cancel():
            break
        if not 原始行:
            continue
        行 = 原始行.decode("utf-8", "replace") if isinstance(原始行, bytes) else 原始行
        文本 = 行.strip()
        if 文本.startswith("data:"):
            文本 = 文本[5:].strip()
        if 文本 == "[DONE]":
            break
        if not 文本:
            continue
        try:
            数据 = json.loads(文本)
        except ValueError:
            continue
        增量 = _取增量(数据)
        if 增量:
            累计 += 增量
            on_chunk(累计)
    return 累计.strip()


def _取增量(数据):
    try:
        return 数据["choices"][0]["delta"].get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return ""
