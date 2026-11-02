"""中译英配置层离线测试：只用临时目录，不读写真配置，不联网。

[INPUT] 临时 TRANSLATOR_CONFIG_DIR 下的手写 config.json（旧 v2 / 扁平旧格式）。
[OUTPUT] unittest 断言；覆盖旧配置回填默认中译英提示词、磁盘不提前重写、保存往返。
[POS] 守护 translator_settings 的 prompt_zh2en 磁盘契约与回填逻辑。
[PROTOCOL] 运行：python -m unittest tests.test_zh2en_config -v
"""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import translator_settings as 设置


class 中译英配置(unittest.TestCase):
    def setUp(self):
        self._旧值 = os.environ.get("TRANSLATOR_CONFIG_DIR")
        self.临时目录 = tempfile.mkdtemp()
        os.environ["TRANSLATOR_CONFIG_DIR"] = self.临时目录
        self._旧路径补丁 = mock.patch.object(设置, "旧配置路径们", return_value=[])
        self._旧路径补丁.start()
        self.addCleanup(self._旧路径补丁.stop)
        self.配置 = os.path.join(self.临时目录, "config.json")

    def tearDown(self):
        if self._旧值 is None:
            os.environ.pop("TRANSLATOR_CONFIG_DIR", None)
        else:
            os.environ["TRANSLATOR_CONFIG_DIR"] = self._旧值
        shutil.rmtree(self.临时目录, ignore_errors=True)

    def _写磁盘(self, 数据):
        with open(self.配置, "w", encoding="utf-8") as 文件:
            json.dump(数据, 文件, ensure_ascii=False, indent=2)

    def _读磁盘(self):
        with open(self.配置, "r", encoding="utf-8") as 文件:
            return json.load(文件)

    def test_旧v2方案缺中译英提示词回填默认且磁盘不提前重写(self):
        self._写磁盘({
            "version": 2,
            "current": "default",
            "profiles": {
                "default": {
                    "base_url": "https://old/v1",
                    "model": "old-model",
                    "prompt": "旧提示",
                }
            },
        })
        配置 = 设置.load_config()
        self.assertEqual(配置["prompt_zh2en"], 设置.默认中译英提示词)
        self.assertEqual(配置["prompt"], "旧提示")
        self.assertEqual(配置["base_url"], "https://old/v1")
        self.assertEqual(配置["model"], "old-model")
        # 未调用任何 save 之前，磁盘文件不得被重写：仍无 prompt_zh2en 键
        磁盘 = self._读磁盘()
        self.assertNotIn("prompt_zh2en", 磁盘["profiles"]["default"])

    def test_扁平旧配置回填默认并保留其他字段(self):
        self._写磁盘({
            "api_key": "",
            "base_url": "https://flat/v1",
            "model": "flat-model",
            "prompt": "扁平提示",
        })
        配置 = 设置.load_config()
        self.assertEqual(配置["prompt_zh2en"], 设置.默认中译英提示词)
        self.assertEqual(配置["prompt"], "扁平提示")
        self.assertEqual(配置["base_url"], "https://flat/v1")
        self.assertEqual(配置["model"], "flat-model")

    def test_新建空方案带默认中译英提示词(self):
        设置.load_profiles()
        方案 = 设置.create_empty_profile("备用")
        self.assertEqual(方案["prompt_zh2en"], 设置.默认中译英提示词)

    def test_保存方案自定义值往返且省略时保留旧值(self):
        设置.save_profile("work", "sk", "https://x/v1", "m", "p", "自定义")
        self.assertEqual(
            设置.load_profiles()["profiles"]["work"]["prompt_zh2en"], "自定义"
        )
        # 不传 prompt_zh2en（旧调用形状）：必须保留已有的自定义值
        设置.save_profile("work", "sk2", "https://y/v1", "m2", "p2")
        self.assertEqual(
            设置.load_profiles()["profiles"]["work"]["prompt_zh2en"], "自定义"
        )

    def test_保存当前方案空字符串回退默认(self):
        设置.save_profile("work", "sk", "https://x/v1", "m", "p", "自定义")
        设置.switch_profile("work")
        设置.save_config("sk", "https://x/v1", "m", "p", "")
        self.assertEqual(设置.load_config()["prompt_zh2en"], 设置.默认中译英提示词)

    def test_保存当前方案旧位置调用保留自定义值(self):
        设置.save_profile("work", "sk", "https://x/v1", "m", "p", "自定义")
        设置.switch_profile("work")
        # 旧形状：只传 4 个位置参数，不带 prompt_zh2en
        设置.save_config("sk", "https://x/v1", "m", "p")
        self.assertEqual(设置.load_config()["prompt_zh2en"], "自定义")


if __name__ == "__main__":
    unittest.main(verbosity=2)
