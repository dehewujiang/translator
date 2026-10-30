# 模块边界（界面重做后）

- `app.py`（组装）：无边框窗口创建、拖动/关闭/Esc、触发、剪贴板、翻译流程、渲染、托盘；混入 `SettingsWindowMixin`。
- `translator_theme.py`：样子——色板常量、`ICON_BTN`、PIL 画的图标（复制/关闭/箭头/齿轮）、按钮底图工厂、四角圆角遮罩、`_Tip` 悬停气泡。无项目 import。
- `translator_layout.py`：纯算数（`WIN_W`、`FIXED_CHROME=203`、高度公式），零 import。
- `translator_settings_window.py`：配置窗，**全部 tk 控件**（不用 ttk），只读 `settings` 与 `theme`。
- 依赖：`app → {theme,layout,settings_window,core}`；`core → provider/domain`；不许反向。

## 关键约束

- 主窗是 `overrideredirect(True)` + `wm_attributes("-transparentcolor", KEY_COLOR #FF00FE)`：任何界面元素都不能用 `#FF00FE`；圆角靠四角 13×13 遮罩，窗口变高必须重新摆放四角。
- 顶栏 28px、图标按钮 28px、原文行 28px 三者必须相等（测试锁死 `HEADER_H == LABEL_H == ICON_BTN`）。
- 状态条挂在顶栏里，绝不能进卡片的主 pack 链——进了就会压扁底栏。
- 配置窗不能 `overrideredirect`（它是对话框，要标题栏）。
- 测试全离线；`config.json` 不入库；exe 在 `dist/` 不入库，分发前重打。
