"""翻译核心：英文到中文的后端单元。
[INPUT] 英文文本 + config.json 当前方案（api_key / base_url / model / prompt）。
[OUTPUT] 中文译文字符串；配置读写走当前方案，多方案存 profiles 下。
[POS] 被 app.py 导入使用，提供 load_config、save_config、translate_en_to_zh 及多方案管理函数。
[PROTOCOL] 兼容 OpenAI 的聊天接口 POST {base_url}/chat/completions；老版单层 config.json 自动迁移。
"""

import json
import os

import requests

默认提示词 = "你是翻译，只返回中文译文，代码和路径不要翻译，保持原样。"
默认接口地址 = "https://opencode.ai/inference/openai/v1"
默认模型 = "deepseek-v4.1-flash"

# 配置文件放在本文件同一目录
配置文件路径 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _整理接口地址(地址):
    # 去掉末尾的斜杠，避免拼接出双斜杠
    if not 地址:
        return 默认接口地址
    return str(地址).strip().rstrip("/") or 默认接口地址


def _默认方案():
    return {
        "api_key": "",
        "base_url": 默认接口地址,
        "model": 默认模型,
        "prompt": 默认提示词,
    }


def _补齐方案(方案):
    # 只保证四个键存在，不强填默认值——空就是没填好，列表要打未配置标。
    # 翻译时缺地址模型再临时用默认，不写回文件。
    if not isinstance(方案, dict):
        方案 = {}
    出 = {}
    for 键 in ("api_key", "base_url", "model", "prompt"):
        值 = 方案.get(键, "")
        出[键] = str(值).strip() if isinstance(值, str) else (值 or "")
    if 出.get("api_key") is None:
        出["api_key"] = ""
    return 出


def _规范化数据(原始):
    # 把老版单层格式和新版多方案格式统一成 {"current":..., "profiles":{...}}
    if not isinstance(原始, dict):
        原始 = {}
    if "profiles" in 原始 and isinstance(原始["profiles"], dict) and 原始["profiles"]:
        方案集 = {名: _补齐方案(配) for 名, 配 in 原始["profiles"].items()}
        当前 = 原始.get("current")
        if 当前 not in 方案集:
            当前 = next(iter(方案集))
        return {"current": 当前, "profiles": 方案集}
    # 老版单层：整个 dict 就是一个方案（保留用户原来的值）
    老方案 = {}
    for 键 in ("api_key", "base_url", "model", "prompt"):
        if 键 in 原始:
            老方案[键] = 原始[键]
    if 老方案 or True:
        # 即使是空文件，也保留成 default 方案（值用默认补齐）
        return {"current": "default", "profiles": {"default": _补齐方案(老方案)}}


def _读取原始():
    if not os.path.exists(配置文件路径):
        return None
    try:
        with open(配置文件路径, "r", encoding="utf-8") as 文件:
            return json.load(文件)
    except (OSError, ValueError):
        return None


def _写入数据(数据):
    with open(配置文件路径, "w", encoding="utf-8") as 文件:
        json.dump(数据, 文件, ensure_ascii=False, indent=2)


def load_profiles():
    """返回规范化后的多方案数据 {"current":..., "profiles":{...}}，顺手迁移老格式。"""
    原始 = _读取原始()
    if 原始 is None:
        数据 = {"current": "default", "profiles": {"default": _默认方案()}}
        try:
            _写入数据(数据)
        except OSError:
            pass
        return {"current": "default", "profiles": {"default": dict(数据["profiles"]["default"])}}
    数据 = _规范化数据(原始)
    # 老格式或缺字段时回写，实现自动迁移（保留用户原来的值）
    try:
        _写入数据(数据)
    except OSError:
        pass
    return 数据


def get_current_name():
    """返回当前方案名。"""
    return load_profiles()["current"]


def load_config():
    """读取当前方案的配置（兼容老调用：返回单层 dict）。"""
    数据 = load_profiles()
    当前 = 数据["current"]
    方案 = 数据["profiles"].get(当前)
    if 方案 is None:
        当前 = next(iter(data_profiles(数据)))
        方案 = 数据["profiles"][当前]
    return dict(方案)


def data_profiles(数据):
    return 数据["profiles"]


def save_config(api_key, base_url, model, prompt=None):
    """保存到当前方案。老调用 save_config(key, url, model) 照样能用；prompt 不传则保留原值。"""
    数据 = load_profiles()
    当前 = 数据["current"]
    旧 = 数据["profiles"].get(当前, {})
    if prompt is None:
        prompt = 旧.get("prompt", 默认提示词)
    if base_url is None or str(base_url).strip() == "":
        base_url = 默认接口地址
    if model is None or str(model).strip() == "":
        model = 默认模型
    if api_key is None:
        api_key = ""
    数据["profiles"][当前] = _补齐方案(
        {"api_key": api_key, "base_url": base_url, "model": model, "prompt": prompt}
    )
    _写入数据(数据)
    return dict(数据["profiles"][当前])


def save_profile(name, api_key="", base_url="", model="", prompt=""):
    """新建或更新一个方案（不切换当前）。返回存好的方案。"""
    名 = str(name or "").strip()
    if not 名:
        raise Exception("方案名字不能为空。")
    数据 = load_profiles()
    数据["profiles"][名] = _补齐方案(
        {"api_key": api_key, "base_url": base_url, "model": model, "prompt": prompt}
    )
    _写入数据(数据)
    return dict(数据["profiles"][名])


def switch_profile(name):
    """切换当前方案。没填好的方案不让切，避免翻不出。"""
    名 = str(name or "").strip()
    数据 = load_profiles()
    if 名 not in 数据["profiles"]:
        raise Exception("没有这个方案：" + 名)
    if not is_profile_configured(名, 数据):
        raise Exception("这套还没填好，填好保存后才能用。")
    数据["current"] = 名
    _写入数据(数据)
    return dict(数据["profiles"][名])


def create_empty_profile(name):
    """新建一套空方案（地址钥匙模型留空，只带默认提示词），不切换当前。重名会报错。"""
    名 = str(name or "").strip()
    if not 名:
        raise Exception("方案名字不能为空。")
    数据 = load_profiles()
    if 名 in 数据["profiles"]:
        raise Exception("已经有这个名字了，换个名字。")
    数据["profiles"][名] = {
        "api_key": "",
        "base_url": "",
        "model": "",
        "prompt": 默认提示词,
    }
    _写入数据(数据)
    return dict(数据["profiles"][名])


def is_profile_configured(name, 数据=None):
    """这套填好了没有：地址钥匙模型三样都有才算好，供切换和列表打标用。"""
    try:
        数据 = 数据 or load_profiles()
        方案 = 数据["profiles"].get(str(name or "").strip(), {})
        return bool(
            str(方案.get("base_url", "")).strip()
            and str(方案.get("api_key", "")).strip()
            and str(方案.get("model", "")).strip()
        )
    except Exception:
        return False


def delete_profile(name):
    """删除一个方案。删的是当前用的会自动换到另一个；最后一个不让删。返回切换后的当前名。"""
    名 = str(name or "").strip()
    数据 = load_profiles()
    if 名 not in 数据["profiles"]:
        raise Exception("没有这个方案：" + 名)
    if len(数据["profiles"]) <= 1:
        raise Exception("只剩最后一个方案了，不能再删。")
    del 数据["profiles"][名]
    if 数据["current"] == 名:
        数据["current"] = next(iter(数据["profiles"]))
    _写入数据(数据)
    return 数据["current"]


def _call_api(系统提示, 用户内容):
    """调一次当前方案的接口，返回模型原文。地址模型缺时临时用默认，缺钥匙抛中文提示。"""
    配置 = load_config()
    密钥 = str(配置.get("api_key", "")).strip()
    接口地址 = _整理接口地址(配置.get("base_url", 默认接口地址))
    模型 = str(配置.get("model", 默认模型)).strip() or 默认模型
    if 密钥 == "":
        raise Exception("还没有设置密钥，请先打开配置填好密钥再翻译。")
    网址 = 接口地址 + "/chat/completions"
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
    try:
        回应 = requests.post(网址, headers=请求头, json=请求体, timeout=30)
    except requests.RequestException:
        raise Exception("网络连接失败，请检查网络后重试。")
    if 回应.status_code == 401:
        raise Exception("密钥无效或已过期（401），请检查密钥是否正确。")
    if 回应.status_code == 404:
        raise Exception("接口地址或模型不对（404），请检查地址和模型是否正确。")
    if 回应.status_code != 200:
        raise Exception("翻译失败（错误码 " + str(回应.status_code) + "），请稍后重试。")
    try:
        数据 = 回应.json()
        内容 = 数据["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise Exception("翻译结果解析失败，请稍后重试。")
    if 内容 is None:
        return ""
    return str(内容).strip()


单词指令 = (
    "你是英汉词典。用户只给一个英文单词，你只返回 JSON，不要多一个字："
    '{"word":"原词","uk":"英式音标","us":"美式音标",'
    '"senses":[{"pos":"词性如n./vt.","defs":["中文意思1","中文意思2"],'
    '"examples":[{"en":"英文例句","zh":"中文意思"}]}]}。'
    "要求：音标用国际音标并带斜杠；意思按常用排，先核心后引申；"
    "整个单词至少给3个例句，每个例句都要有中文；例句短而常用。"
)


def lookup_word(word):
    """查单词：返回词典 dict，含 word/uk/us/senses。模型不听话时抛原文，界面直接显示原文。"""
    原文 = str(word or "").strip()
    if not 原文:
        return {"word": "", "uk": "", "us": "", "senses": [], "_raw": ""}
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
        raise Exception(内容)
    if not isinstance(结果, dict) or not 结果.get("senses"):
        raise Exception(内容)
    return 结果


def is_single_word(text):
    """是不是单个英文单词：只含字母连字符撇号且中间没空格，句子走翻译，单词走词典。"""
    片段 = str(text or "").strip().strip(".,!?;:\"'()[]")
    if not 片段 or " " in 片段 or "\n" in 片段:
        return False
    for 字 in 片段:
        if not (字.isalpha() and ord(字) < 128 or 字 in "-'"):
            return False
    return 2 <= len(片段) <= 30


def translate_en_to_zh(text):
    """把英文翻译成中文，只返回中文译文（提示词来自当前方案的 prompt）。"""
    # 空文本直接返回空，不调用接口
    if text is None or str(text).strip() == "":
        return ""
    原文 = str(text)
    配置 = load_config()
    提示词 = str(配置.get("prompt", "") or "").strip() or 默认提示词
    return _call_api(提示词, 原文)
