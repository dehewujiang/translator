# 翻译小助手

常驻后台的 Windows 英译中弹窗：复制英文 → 轻点一下 `Ctrl` → 弹出中文译文。查单词出词典（音标、词性、例句）。

## 直接用（不用装任何东西）

1. 找作者要 `dist\翻译小助手.exe`，双击。右下角托盘冒出“译”字图标就是跑起来了（没弹窗是正常的，它在后台等着）。
2. 右键托盘图标 → 显示窗口 → 点齿轮进配置，把**地址、钥匙、模型**三样填好保存。钥匙去你用的模型官网申请，每台电脑第一次都要填自己的。
3. 复制一段英文，轻点一下 `Ctrl`（点一下就松开），译文弹窗自动出来。

小技巧：`Alt+Q` 随时叫出窗口；光标自动进原文框，打完字按回车就翻；点窗口外面自动藏起；退出走托盘右键。

## 自己跑源码（第一次拉下来看这里）

```bat
git clone https://github.com/dehewujiang/translator.git
cd translator
run.bat            ← 双击：检查 Python → 自动装依赖 → 验零件 → 藏后台运行
```

跑起来长这样：右下角小箭头里冒出蓝色“译”字图标（没弹窗是正常的，它在后台等着）。
如果双击后黑窗口报“缺零件”或“依赖装不上”，上面的红字就是原因，修好重双击就行。
`run_hidden.vbs` 跟 `run.bat` 效果一样，只是不弹黑窗（出问题时还是用 `run.bat`，能看见报错）。

需要 Python 3 + `pip install -r requirements.txt`。跑测试：`python -m unittest discover -s tests -v`（48+ 条，全离线）。

改完代码 exe 不会自动更新，重打才分发：`python -m PyInstaller --noconfirm --clean 翻译小助手.spec`。

## 配置在哪

`%LOCALAPPDATA%\翻译小助手\config.json`。钥匙是加密存的（跟这台 Windows 用户绑定），换电脑要重填。旧明文 `config.json` 不要进版本库（已忽略）。

## 项目结构

| 文件 | 干什么 |
|---|---|
| `app.py` | 界面组装、触发、翻译流程、渲染 |
| `translator_theme.py` | 颜色字体、按钮样子 |
| `translator_layout.py` | 窗口多高（纯算数） |
| `translator_settings_window.py` | 配置窗 |
| `translator_core.py` | 翻译大脑，唯一入口 `run_intent` |
| `translator_domain.py` | 查词/翻译两种意图，三种结果 |
| `translator_provider.py` | 跟模型 API 说话、流式输出 |
| `translator_settings.py` | 读存配置、加密、旧配置搬家 |

依赖只能往下走：`app → core → provider/domain`，不许反向。详细架构见 `docs/architecture-redesign.md`，模块地图见 `AGENTS.md`。
