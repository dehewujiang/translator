# 翻译小助手 · AGENTS.md

常驻后台的 Windows 英译中弹窗：复制英文 → 轻点 Ctrl → 弹出译文/词典。

## 模块地图

| 文件/目录 | 职责 |
|---|---|
| `translator_domain.py` | 契约层：意图（查词/翻译）与结果（译文/词典/失败）的类型，不联网、不读文件 |
| `translator_core.py` | 能力层：结果归一化；唯一入口是 `run_intent` |
| `translator_provider.py` | 接口驱动：OpenAI 兼容请求、SSE 流式、取消；不读配置、不碰界面 |
| `translator_settings.py` | 配置层：路径、schema、原子写、DPAPI 加密、旧配置迁移 |
| `app.py` | 展示层：触发、剪贴板、配置窗、渲染、托盘；不判断词句、不拼提示词 |
| `tests/` | 标准库 unittest，全部离线；跑：`python -m unittest discover -s tests -v` |
| `docs/architecture-redesign.md` | 目标架构、契约、迁移顺序（第 2–4 步未做）、验收单 |
| `evidence/` | 每次任务的机器证据与改动前快照 |

## 依赖方向

`app → core → provider/domain`，不许反向；`app` 与 `core` 都可读 `settings`，`settings` 不依赖本项目其他模块；界面和 core 都不 import requests，不拼 URL，不解析错误文字。

## 交付规矩

- 行为改动先写失败测试再修复；测试不联网、不读写真配置。
- `config.json` 不进版本库，密钥不进文件、不进对话。
- 单文件 exe 经 `翻译小助手.spec` 打包；改代码后 exe 不自动更新，需重打才分发。
