# 模块边界（界面重做后）

- `app.py`（组装）：无边框窗口创建、拖动/关闭/Esc、触发、剪贴板、翻译流程、渲染、托盘；混入 `SettingsWindowMixin`。
- `translator_theme.py`：样子——色板常量、`ICON_BTN`、PIL 画的图标（复制/关闭/箭头/齿轮）、按钮底图工厂、四角圆角遮罩、`_Tip` 悬停气泡。无项目 import。
- `translator_layout.py`：纯算数（`WIN_W`、`FIXED_CHROME=203`、高度公式），零 import。
- `translator_settings_window.py`：配置窗，**全部 tk 控件**（不用 ttk），只读 `settings`/`theme`，测试连接时直接调 `provider.chat`。
- 依赖：`app → {theme,layout,settings_window,core}`；`core → provider/domain`；不许反向。

## 关键约束

- 主窗是 `overrideredirect(True)` + `wm_attributes("-transparentcolor", KEY_COLOR #FF00FE)`：任何界面元素都不能用 `#FF00FE`；圆角靠四角 13×13 遮罩，窗口变高必须重新摆放四角。
- 顶栏 28px、图标按钮 28px、原文行 28px 三者必须相等（测试锁死 `HEADER_H == LABEL_H == ICON_BTN`）。
- 状态条挂在顶栏里，绝不能进卡片的主 pack 链——进了就会压扁底栏。
- 配置窗不能 `overrideredirect`（它是对话框，要标题栏）。
- 拖拽调高矮时下限仍是 `WIN_H=360`，但卡片内容（尤其两块文本框）可能更高：拖完必须调 `_fit_panes()` 收文本框行数，否则底栏会被挤出卡片。
- 所有 96dpi 像素常量必须过 `px()`；新增控件/间距时严禁写裸数字，否则 125% 下会错位。
- 译文区是只读的：程序写入必须走 `_dst_edit()` / `_dst_set()`，直接 insert 会被 Tk 忽略。
- Tk Listbox 不支持逐项 `-font`；列表状态只能用 `foreground` / `selectforeground` / ✓ 表达。
- 不可逆操作的确认框：`askyesno` 抛异常时一律按"取消"处理（fail-closed）。
- 深色模式：`translator_theme` 导入时读注册表 `AppsUseLightTheme`，`TRANSLATOR_THEME=dark|light` 可覆盖；DARK 时导入即调 uxtheme `SetPreferredAppMode(2)`（进程级，必须在建 Tk 前）。
- 主窗色键（`-transparentcolor`）会让子窗口标题栏变不了深色：配置窗必须"建窗前短暂摘色键 → update → AllowDarkModeForWindow + DWM 20/19 → 立刻恢复"。
- 译文滚动条是自绘的（Frame 轨道 + Frame 滑块），溢出才 grid，滑块拖动用 `y_root - 轨道 rooty`。
- 拖宽热区必须在卡片内部（不透明），透明边上的热区会被色键点击穿透；拖动时锚定被拖边并夹在屏幕内。
- 测试全离线；`config.json` 不入库；exe 在 `dist/` 不入库，分发前重打。
- 中译英提示词按方案存 `prompt_zh2en`；`translate_zh_to_en` 读它、空则回退 `默认中译英提示词`。`_补齐方案` 在读取时补默认，磁盘要等下次保存才落盘（配置版本号仍是 2，不强制迁移）。
- 配置窗有两个提示词框（英译中 / 中译英），都用 `<<Modified>>` 标记未保存；矮屏时 `_fit_prompt_boxes` 先收行数（最差各 1 行），不得让任一框或底部按钮被挤出可视区。
- 测试不得读真实配置：`tests/test_zh_en.py` 替换 `translator_core.load_config`；`tests/test_zh2en_config.py` 用 `TRANSLATOR_CONFIG_DIR` 指向临时目录。
