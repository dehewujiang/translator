"""中译英红绿证据脚本：先 RED（旧固定指令行为必败）再 GREEN（当前实现必过）。

[INPUT] 无；子进程跑 unittest（tests.test_zh_en / tests.test_zh2en_config），离线。
[OUTPUT] evidence/test-zh2en-redgreen.log（UTF-8）+ 控制台 RESULT 行；全符合预期才 exit 0。
[POS] 证据层；只读被测模块行为，不改任何源码与配置。
[PROTOCOL] 运行：python evidence/zh2en-redgreen.py（cwd 必须在项目根）
"""

import os
import subprocess
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
日志路径 = os.path.join(根, "evidence", "test-zh2en-redgreen.log")

绿命令 = [sys.executable, "-m", "unittest", "tests.test_zh_en", "tests.test_zh2en_config", "-v"]

红代码 = (
    "import sys; sys.path.insert(0, " + repr(根) + ")\n"
    "import translator_core\n"
    "def 旧实现(text, on_chunk=None, cancel=None):\n"
    '    if text is None or str(text).strip() == "":\n'
    '        return ""\n'
    "    return translator_core._call_api(translator_core.中译英指令, str(text), on_chunk=on_chunk, cancel=cancel)\n"
    "translator_core.translate_zh_to_en = 旧实现\n"
    "import unittest\n"
    'result = unittest.main(module=None, argv=["x", "tests.test_zh_en"], exit=False, verbosity=2)\n'
    "sys.exit(0 if result.result.wasSuccessful() else 1)\n"
)
红命令 = [sys.executable, "-c", 红代码]


def 跑(命令, 阶段名):
    进程 = subprocess.run(
        命令,
        cwd=根,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    输出 = "### %s: %s\n返回码: %d\n\n%s\n%s\n" % (
        阶段名,
        " ".join(命令[:4]) + (" ..." if len(命令) > 4 else ""),
        进程.returncode,
        进程.stdout,
        进程.stderr,
    )
    return 进程.returncode, 输出


def 主():
    绿码, 绿输出 = 跑(绿命令, "GREEN")
    红码, 红输出 = 跑(红命令, "RED(旧固定指令行为)")
    红文本 = 红输出
    红提到自定义 = "自定义" in 红文本
    绿符合 = 绿码 == 0
    红符合 = 红码 != 0 and 红提到自定义
    行 = []
    行.append("GREEN EXPECTED -> got exit=%d (%s)" % (绿码, "OK" if 绿符合 else "FAIL"))
    行.append("RED EXPECTED -> got exit=%d, mentions-custom-prompt=%s (%s)" % (
        红码, 红提到自定义, "OK" if 红符合 else "FAIL"))
    if 绿符合 and 红符合:
        行.append("RESULT: RED->GREEN OK")
    else:
        行.append("RESULT: RED->GREEN FAIL")
    汇总 = "\n".join(行) + "\n"
    with open(日志路径, "w", encoding="utf-8") as 文件:
        文件.write(汇总 + "\n" + 绿输出 + "\n" + 红输出)
    print(汇总, end="")
    return 0 if (绿符合 and 红符合) else 1


if __name__ == "__main__":
    sys.exit(主())
