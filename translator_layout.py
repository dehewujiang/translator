"""窗口高度数学：纯计算，不建窗口。

[INPUT] 行数、行高、屏幕高等纯数值。
[OUTPUT] 原文区高度、窗口高度（像素整数）。
[POS] 纯计算模块；被 app.py 依赖；不 import 本项目任何模块。
[PROTOCOL] 原文区 = 标题 + 6 + 文本 + 18 像素空隙；窗口高度按内容行数估算，夹在最小高度和屏幕上限之间。

无边框卡片垂直节奏（外窗 380 宽，上下各 8px 透明边，卡片 364 宽）：
  透明边 8 → 顶垫 12 → 顶栏 28 → 间 8 → 译文 → 间 22 → 分隔 9 →
  间 14 → “原文”行 28 → 间 6 → 原文 → 间 10 → 底栏 32 → 底垫 18 → 透明边 8
固定铬 = 16 + 12+28+8+22+9+14+28+6+10+32+18 = 203（不含两块可变文本）。
“原文”行 28px = 内含 28px 图标按钮（ICON_BTN），行高由按钮撑起，非 8pt 文字行高。
顶栏 28px = 内含 28px 图标按钮（ICON_BTN），与 translator_theme.ICON_BTN 同值。
"""

WIN_W, WIN_H = 380, 360

MARGIN = 8
TOP_PAD = 12
HEADER_H = 28
GAP_AFTER_HEADER = 8
GAP_BEFORE_DIV = 22
DIV_H = 9
GAP_AFTER_DIV = 14
LABEL_H = 28
GAP_AFTER_LABEL = 6
GAP_BEFORE_FOOTER = 10
FOOTER_H = 32
BOTTOM_PAD = 18

FIXED_CHROME = (
    MARGIN * 2
    + TOP_PAD
    + HEADER_H
    + GAP_AFTER_HEADER
    + GAP_BEFORE_DIV
    + DIV_H
    + GAP_AFTER_DIV
    + LABEL_H
    + GAP_AFTER_LABEL
    + GAP_BEFORE_FOOTER
    + FOOTER_H
    + BOTTOM_PAD
)


def _算原文高度(文本像素, 题高, 行高):
    """原文区 = 标题 + 6 + 文本 + 18 像素空隙；空文本至少留一行。"""
    return 题高 + 6 + max(int(文本像素), int(行高)) + 18


def _钳制窗口高度(想要, 屏幕高):
    """把任意高度钳在 [最小高度, 屏幕上限] 之间；拖拽手柄与自动算高共用。"""
    上限 = max(WIN_H, min(int(屏幕高 * 0.72), 900))
    return max(WIN_H, min(int(想要), 上限))


def _算窗口高度(源行数, 译文行数, 行高, 屏幕高):
    """按内容行数估算窗口高度，夹在最小高度和屏幕上限之间。"""
    固定高 = FIXED_CHROME
    源高 = min(max(int(源行数), 1), 12) * 行高
    译文高 = min(max(int(译文行数), 1), 30) * 行高
    return _钳制窗口高度(固定高 + 源高 + 译文高, 屏幕高)
