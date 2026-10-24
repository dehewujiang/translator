"""配置与密钥存储的单元测试。

[INPUT] 临时目录里的配置文件；Windows 上用真实 DPAPI，不联网。
[OUTPUT] unittest 断言；覆盖首次建配置、迁移、加密、原子写、方案增删切换。
[POS] 守护 translator_settings 的磁盘契约与旧配置迁移。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import json
import os
import tempfile
import unittest
from unittest import mock

import translator_settings as 设置


class 配置存储测试(unittest.TestCase):
    def setUp(self):
        self.临时目录 = tempfile.TemporaryDirectory()
        self.addCleanup(self.临时目录.cleanup)
        self.环境 = mock.patch.dict(
            os.environ, {"TRANSLATOR_CONFIG_DIR": self.临时目录.name}
        )
        self.环境.start()
        self.addCleanup(self.环境.stop)
        self.旧路径 = mock.patch.object(设置, "旧配置路径们", return_value=[])
        self.旧路径.start()
        self.addCleanup(self.旧路径.stop)
        self.配置 = os.path.join(self.临时目录.name, "config.json")

    def _写旧文件(self, 内容):
        路径 = os.path.join(self.临时目录.name, "legacy.json")
        with open(路径, "w", encoding="utf-8") as 文件:
            json.dump(内容, 文件, ensure_ascii=False)
        return 路径

    def _读磁盘(self):
        with open(self.配置, "r", encoding="utf-8") as 文件:
            return json.load(文件)

    def _备份文件(self):
        return [
            名
            for 名 in os.listdir(self.临时目录.name)
            if 名.startswith("config.json.bak-")
        ]

    def test_首次加载建默认配置(self):
        数据 = 设置.load_profiles()
        self.assertEqual(数据["current"], "default")
        self.assertIn("default", 数据["profiles"])
        self.assertTrue(os.path.exists(self.配置))
        self.assertEqual(self._读磁盘()["version"], 2)

    def test_保存后磁盘不含明文钥匙且能读回(self):
        设置.save_profile("work", "sk-secret-123", "https://x/v1", "m", "提示")
        with open(self.配置, "r", encoding="utf-8") as 文件:
            原文 = 文件.read()
        if 设置.HAS_DPAPI:
            self.assertNotIn("sk-secret-123", 原文)
            self.assertIn("api_key_dpapi", 原文)
        数据 = 设置.load_profiles()
        self.assertEqual(数据["profiles"]["work"]["api_key"], "sk-secret-123")

    def test_旧单层配置迁移到新目录并留备份(self):
        旧 = self._写旧文件(
            {
                "api_key": "sk-old-123",
                "base_url": "https://old/v1",
                "model": "old-model",
                "prompt": "旧提示",
            }
        )
        with mock.patch.object(设置, "旧配置路径们", return_value=[旧]):
            数据 = 设置.load_profiles()
        self.assertEqual(数据["profiles"]["default"]["api_key"], "sk-old-123")
        self.assertEqual(数据["profiles"]["default"]["model"], "old-model")
        self.assertTrue(os.path.exists(self.配置))
        self.assertTrue(self._备份文件())
        self.assertTrue(os.path.exists(旧))
        if 设置.HAS_DPAPI:
            with open(self.配置, encoding="utf-8") as 文件:
                self.assertNotIn("sk-old-123", 文件.read())

    def test_旧多方案配置迁移保留当前方案(self):
        旧 = self._写旧文件(
            {
                "current": "deepseek",
                "profiles": {
                    "default": {
                        "api_key": "sk-a",
                        "base_url": "https://a/v1",
                        "model": "ma",
                        "prompt": "pa",
                    },
                    "deepseek": {
                        "api_key": "sk-b",
                        "base_url": "https://b/v1",
                        "model": "mb",
                        "prompt": "pb",
                    },
                },
            }
        )
        with mock.patch.object(设置, "旧配置路径们", return_value=[旧]):
            数据 = 设置.load_profiles()
        self.assertEqual(数据["current"], "deepseek")
        self.assertEqual(数据["profiles"]["deepseek"]["api_key"], "sk-b")
        self.assertEqual(self._读磁盘()["version"], 2)

    def test_未配置方案不能切换(self):
        设置.load_profiles()
        设置.create_empty_profile("备用")
        with self.assertRaises(Exception):
            设置.switch_profile("备用")

    def test_最后一个方案不能删(self):
        设置.load_profiles()
        with self.assertRaises(Exception):
            设置.delete_profile("default")

    def test_损坏配置先备份再回默认(self):
        with open(self.配置, "w", encoding="utf-8") as 文件:
            文件.write("{坏掉的 json")
        数据 = 设置.load_profiles()
        self.assertEqual(数据["current"], "default")
        self.assertTrue(self._备份文件())

    def test_保存方案不切换当前(self):
        设置.save_profile("work", "sk", "https://x/v1", "m", "p")
        self.assertEqual(设置.load_profiles()["current"], "default")

    def test_保存当前方案不传提示词时保留原值(self):
        设置.save_profile("work", "sk", "https://x/v1", "m", "原提示")
        设置.switch_profile("work")
        设置.save_config("sk", "https://x/v1", "m")
        self.assertEqual(设置.load_config()["prompt"], "原提示")

    def test_配置文件位于配置目录(self):
        self.assertEqual(os.path.dirname(设置.配置路径()), self.临时目录.name)

    @unittest.skipUnless(设置.HAS_DPAPI, "需要 Windows DPAPI")
    def test_DPAPI加解密往返(self):
        令牌 = 设置._保护("sk-abc-123")
        self.assertNotIn("sk-abc-123", 令牌)
        self.assertEqual(设置._解开(令牌), "sk-abc-123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
