# 收工证据（三行）

1. 做了什么：把“词句判断”和“结果类型”从界面抽到独立模块；翻译、词典、失败三种结果统一走一个入口，界面按类型渲染，删掉了靠错误文字猜类型的写法。
2. 验了什么：20 条单测先红后绿（红 = 模块不存在，退出码 1；绿 = 20 条通过，退出码 0）；4 个文件语法检查通过；导入冒烟正常；测试全程不联网。
3. 还剩什么：线程排队、供应商适配、配置与密钥、结果卡片都还没做（第 2–4 步）；exe 没重打；真实弹窗要按下面验收单人工过一遍。

## 验收单（按顺序点一遍）

1. 打开程序 → 复制单词 `king` → 轻点 Ctrl → □ 弹出词典：词头、音标、词性、至少 3 个例句。
2. 复制 `good morning` → 轻点 Ctrl → □ 弹出中文译文，不是词典。
3. 复制一段带路径的英文（如 `open C:\temp\a.txt now`）→ 轻点 Ctrl → □ 路径保持原样。
4. 点“配置” → 把钥匙改错 → 保存 → 翻译 → □ 提示密钥无效，能改回来。
5. 断网后翻译 → □ 提示网络连接失败，不是白屏或英文报错。
6. 连点两次 Ctrl（内容不同）→ □ 当前版本仍可能显示先一次的结果（第 2 步修，此项只记录现状）。

任意一条不对：告诉我第几条 + 实际看到什么，不要自己改文件。

## 证据在哪

- 机器证据：`evidence/test.log`（红/绿/终验）、`evidence/diff.patch`（逐行差异）、`evidence/run.json`（命令与退出码）
- 改动前快照：`evidence/before/app.py`、`evidence/before/translator_core.py`
- 临时备份：`C:\Users\Administrator\AppData\Local\Temp\opencode\translator-checkpoint-20261024-131348`

## 回退

把 `evidence/before/` 里两个文件复制回项目根目录，再删掉新加的 `translator_domain.py`、`tests/`、`docs/architecture-redesign.md`，即回到改动前。回退前先确认没有别的新改动。
