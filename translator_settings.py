"""配置与密钥存储：路径、迁移、原子写、Windows 当前用户加密。

[INPUT] 用户方案（地址/模型/提示词/明文钥匙）；旧版 config.json。
[OUTPUT] 规范化多方案数据；磁盘上钥匙是 DPAPI 密文，配置在用户目录。
[POS] 配置层；被 translator_core 与 app.py 使用；不联网、不碰界面。
[PROTOCOL] 磁盘格式 {"version":2,"current":...,"profiles":{名:{base_url,model,prompt,api_key_dpapi}}}。
"""

import base64
import ctypes
import json
import os
import shutil
import sys
import time

默认提示词 = "你是翻译，只返回中文译文，代码和路径不要翻译，保持原样。"
默认接口地址 = "https://opencode.ai/inference/openai/v1"
默认模型 = "deepseek-v4.1-flash"
配置版本 = 2
目录名 = "翻译小助手"

HAS_DPAPI = sys.platform == "win32" and hasattr(ctypes, "windll")


class _数据块(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


if HAS_DPAPI:
    _CryptProtectData = ctypes.windll.crypt32.CryptProtectData
    _CryptProtectData.argtypes = [
        ctypes.POINTER(_数据块),
        ctypes.c_wchar_p,
        ctypes.POINTER(_数据块),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_数据块),
    ]
    _CryptProtectData.restype = ctypes.c_int

    _CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
    _CryptUnprotectData.argtypes = [
        ctypes.POINTER(_数据块),
        ctypes.c_void_p,
        ctypes.POINTER(_数据块),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(_数据块),
    ]
    _CryptUnprotectData.restype = ctypes.c_int

    _LocalFree = ctypes.windll.kernel32.LocalFree
    _LocalFree.argtypes = [ctypes.c_void_p]
    _LocalFree.restype = ctypes.c_void_p


def 配置目录():
    指定 = os.environ.get("TRANSLATOR_CONFIG_DIR", "").strip()
    if 指定:
        return os.path.abspath(指定)
    根 = os.environ.get("LOCALAPPDATA", "").strip() or os.path.expanduser("~")
    return os.path.join(根, 目录名)


def 配置路径():
    return os.path.join(配置目录(), "config.json")


def 旧配置路径们():
    候选 = []
    for 目录 in (
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.abspath(sys.executable)),
    ):
        路径 = os.path.join(目录, "config.json")
        if 路径 not in 候选:
            候选.append(路径)
    return 候选


def _块(数据):
    缓冲 = ctypes.create_string_buffer(数据, len(数据))
    return _数据块(len(数据), ctypes.cast(缓冲, ctypes.POINTER(ctypes.c_char))), 缓冲


def _保护(明文):
    if not HAS_DPAPI:
        raise OSError("当前系统不支持密钥加密")
    输入块, _保活 = _块(明文.encode("utf-8"))
    输出块 = _数据块()
    成功 = _CryptProtectData(
        ctypes.byref(输入块), None, None, None, None, 0, ctypes.byref(输出块)
    )
    if not 成功:
        raise OSError(ctypes.GetLastError(), "密钥加密失败")
    try:
        密文 = ctypes.string_at(输出块.pbData, 输出块.cbData)
    finally:
        _LocalFree(ctypes.cast(输出块.pbData, ctypes.c_void_p))
    return base64.b64encode(密文).decode("ascii")


def _解开(令牌):
    if not HAS_DPAPI:
        return ""
    try:
        数据 = base64.b64decode(str(令牌), validate=True)
    except (ValueError, TypeError):
        return ""
    if not 数据:
        return ""
    输入块, _保活 = _块(数据)
    输出块 = _数据块()
    成功 = _CryptUnprotectData(
        ctypes.byref(输入块), None, None, None, None, 0, ctypes.byref(输出块)
    )
    if not 成功:
        return ""
    try:
        明文 = ctypes.string_at(输出块.pbData, 输出块.cbData)
    finally:
        _LocalFree(ctypes.cast(输出块.pbData, ctypes.c_void_p))
    try:
        return 明文.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _默认方案():
    return {
        "api_key": "",
        "base_url": 默认接口地址,
        "model": 默认模型,
        "prompt": 默认提示词,
    }


def _补齐方案(方案):
    if not isinstance(方案, dict):
        方案 = {}
    出 = {}
    for 键 in ("api_key", "base_url", "model", "prompt"):
        值 = 方案.get(键, "")
        出[键] = 值.strip() if isinstance(值, str) else ("" if 值 is None else str(值))
    return 出


def _带钥匙(方案):
    if not isinstance(方案, dict):
        return _默认方案()
    明文 = 方案.get("api_key", "")
    令牌 = 方案.get("api_key_dpapi", "")
    if isinstance(令牌, str) and 令牌.strip() and HAS_DPAPI:
        解开 = _解开(令牌)
        if 解开:
            明文 = 解开
    return _补齐方案(
        {
            "api_key": 明文,
            "base_url": 方案.get("base_url", ""),
            "model": 方案.get("model", ""),
            "prompt": 方案.get("prompt", ""),
        }
    )


def _规范化数据(原始):
    if not isinstance(原始, dict):
        原始 = {}
    方案集原始 = 原始.get("profiles")
    if isinstance(方案集原始, dict) and 方案集原始:
        方案集 = {名: _带钥匙(配) for 名, 配 in 方案集原始.items()}
        当前 = 原始.get("current")
        if 当前 not in 方案集:
            当前 = next(iter(方案集))
        return {"version": 配置版本, "current": 当前, "profiles": 方案集}
    老方案 = {
        键: 原始[键]
        for 键 in ("api_key", "base_url", "model", "prompt")
        if 键 in 原始
    }
    return {
        "version": 配置版本,
        "current": "default",
        "profiles": {"default": _带钥匙(老方案)},
    }


def _空数据():
    return {
        "version": 配置版本,
        "current": "default",
        "profiles": {"default": _默认方案()},
    }


def _读取原始():
    for 路径 in [配置路径()] + 旧配置路径们():
        if not os.path.exists(路径):
            continue
        try:
            with open(路径, "r", encoding="utf-8") as 文件:
                return json.load(文件), 路径
        except (OSError, ValueError):
            return None, 路径
    return None, None


def _需要回写(原始, 来源):
    if not isinstance(原始, dict):
        return True
    if 来源 != 配置路径():
        return True
    if 原始.get("version") != 配置版本:
        return True
    方案集 = 原始.get("profiles")
    if not isinstance(方案集, dict) or not 方案集:
        return True
    if HAS_DPAPI:
        for 方案 in 方案集.values():
            if not isinstance(方案, dict):
                return True
            if str(方案.get("api_key", "")).strip():
                return True
    return False


def _备份(路径):
    try:
        os.makedirs(配置目录(), exist_ok=True)
        标记 = time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns() % 1000000)
        目标 = os.path.join(配置目录(), "config.json.bak-" + 标记)
        shutil.copy2(路径, 目标)
    except OSError:
        pass


def _写入数据(数据):
    目录 = 配置目录()
    os.makedirs(目录, exist_ok=True)
    路径 = 配置路径()
    磁盘 = {
        "version": 配置版本,
        "current": 数据.get("current", "default"),
        "profiles": {},
    }
    for 名, 方案 in 数据.get("profiles", {}).items():
        完整 = _补齐方案(方案)
        项 = {
            "base_url": 完整["base_url"],
            "model": 完整["model"],
            "prompt": 完整["prompt"],
        }
        钥匙 = 完整["api_key"]
        if 钥匙:
            if HAS_DPAPI:
                项["api_key_dpapi"] = _保护(钥匙)
            else:
                项["api_key"] = 钥匙
        磁盘["profiles"][名] = 项
    临时 = 路径 + ".tmp"
    try:
        with open(临时, "w", encoding="utf-8") as 文件:
            json.dump(磁盘, 文件, ensure_ascii=False, indent=2)
            文件.flush()
            os.fsync(文件.fileno())
        os.replace(临时, 路径)
    except OSError:
        try:
            os.remove(临时)
        except OSError:
            pass
        raise


def _复制(数据):
    return {
        "version": 配置版本,
        "current": 数据["current"],
        "profiles": {名: dict(方案) for 名, 方案 in 数据["profiles"].items()},
    }


def load_profiles():
    """读取当前方案集；旧格式自动迁移，钥匙解密后返回。"""
    原始, 来源 = _读取原始()
    if 原始 is None:
        if 来源:
            _备份(来源)
        数据 = _空数据()
        _写入数据(数据)
        return _复制(数据)
    数据 = _规范化数据(原始)
    if _需要回写(原始, 来源):
        if 来源 and os.path.abspath(来源) != os.path.abspath(配置路径()):
            _备份(来源)
        _写入数据(数据)
    return _复制(数据)


def get_current_name():
    return load_profiles()["current"]


def load_config():
    """读取当前方案（兼容老调用：返回单层 dict）。"""
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
    """保存到当前方案。prompt 不传则保留原值。"""
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
    """新建一套空方案（地址钥匙模型留空，只带默认提示词），不切换当前。"""
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
    """地址钥匙模型三样都有才算好。"""
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
    """删除一个方案。删当前用的会自动换到另一个；最后一个不让删。"""
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
