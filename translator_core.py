"""翻译核心：英文到中文的后端单元。
[INPUT] 英文文本 + 当前方案（由 translator_settings 读取）。
[OUTPUT] 译文 / 词典 / 类型化 Failure；界面只经 run_intent 进入。
[POS] 能力层：被 app.py 使用；向上不认识界面，向下依赖 domain/provider/settings。
[PROTOCOL] 通过 translator_provider 调 OpenAI 兼容接口；配置迁移与加密在 translator_settings。
"""

import json

from translator_domain import (
    CONFIG,
    EMPTY,
    PARSE,
    WORD,
    Definition,
    Failure,
    Intent,
    Translation,
    classify_exception,
    is_single_word,
)
from translator_provider import chat as _驱动对话
from translator_settings import 默认接口地址, 默认模型, 默认提示词, load_config


def _整理接口地址(地址):
    # 去掉末尾的斜杠，避免拼接出双斜杠
    if not 地址:
        return 默认接口地址
    return str(地址).strip().rstrip("/") or 默认接口地址


def _call_api(系统提示, 用户内容, on_chunk=None, cancel=None):
    """调一次当前方案的接口，返回模型原文。缺钥匙抛 CONFIG 失败。"""
    配置 = load_config()
    密钥 = str(配置.get("api_key", "")).strip()
    接口地址 = _整理接口地址(配置.get("base_url", 默认接口地址))
    模型 = str(配置.get("model", 默认模型)).strip() or 默认模型
    if 密钥 == "":
        raise Failure(CONFIG, "还没有设置密钥，请先打开配置填好密钥再翻译。")
    return _驱动对话(
        接口地址,
        密钥,
        模型,
        系统提示,
        用户内容,
        on_chunk=on_chunk,
        cancel=cancel,
    )


单词指令 = (
    "你是英汉词典。用户只给一个英文单词，你只返回 JSON，不要多一个字："
    '{"word":"原词","uk":"英式音标","us":"美式音标",'
    '"senses":[{"pos":"词性如n./vt.","defs":["中文意思1","中文意思2"],'
    '"examples":[{"en":"英文例句","zh":"中文意思"}]}]}。'
    "要求：音标用国际音标并带斜杠；意思按常用排，先核心后引申；"
    "整个单词至少给3个例句，每个例句都要有中文；例句短而常用。"
)


def lookup_word(word) -> Definition:
    """查单词：返回词典对象。模型不听话时抛 PARSE 失败，原文放 raw 里备查。"""
    原文 = str(word or "").strip()
    if not 原文:
        return Definition()
    内容 = _call_api(单词指令, 原文)
    文本 = 内容.strip()
    if 文本.startswith("```"):
        文本 = 文本.strip("`").strip()
        if "\n" in 文本:
            首行, _, 剩下 = 文本.partition("\n")
            if "json" in 首行.lower():
                文本 = 剩下.strip()
    try:
        结果 = json.loads(文本)
    except ValueError:
        raise Failure(PARSE, "模型没有按词典格式返回。", raw=内容)
    义项 = 结果.get("senses") if isinstance(结果, dict) else None
    if not isinstance(义项, list) or not 义项:
        raise Failure(PARSE, "模型没有按词典格式返回。", raw=内容)
    return Definition(
        word=str(结果.get("word", "")).strip() or 原文,
        uk=str(结果.get("uk", "")).strip(),
        us=str(结果.get("us", "")).strip(),
        senses=义项,
        raw=内容,
    )


def translate_en_to_zh(text, on_chunk=None, cancel=None):
    """把英文翻译成中文，只返回中文译文（提示词来自当前方案的 prompt）。"""
    # 空文本直接返回空，不调用接口
    if text is None or str(text).strip() == "":
        return ""
    原文 = str(text)
    配置 = load_config()
    提示词 = str(配置.get("prompt", "") or "").strip() or 默认提示词
    return _call_api(提示词, 原文, on_chunk=on_chunk, cancel=cancel)


def run_intent(意图: Intent, on_chunk=None, cancel=None):
    """唯一入口：按意图分派，成功返回译文/词典，失败返回 Failure，不向界面抛异常。"""
    文本 = str(getattr(意图, "text", "") or "").strip()
    if 文本 == "":
        return Failure(EMPTY, "没有可翻译的内容，先复制一段英文。")
    try:
        if getattr(意图, "kind", "") == WORD:
            return lookup_word(文本)
        return Translation(translate_en_to_zh(文本, on_chunk=on_chunk, cancel=cancel))
    except Failure as 失败:
        return 失败
    except Exception as 错误:
        return classify_exception(错误)
