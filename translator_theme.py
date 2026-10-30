"""translator_theme.py
[INPUT] 父容器、文本、命令与坐标等展示参数（由调用方传入）
[OUTPUT] 带统一样式的按钮/提示/托盘图标对象，以及字体颜色常量
[POS] 展示层之下的主题与小部件工厂，只管样子不管行为
[PROTOCOL] 纯搬运 app.py 现有代码，不改逻辑；不依赖本项目其他模块
"""

import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageTk = None
    HAS_PIL = False

FONT = ("微软雅黑", 11)
SRC_FONT = ("微软雅黑", 10)
LBL_FONT = ("微软雅黑", 8)
TITLE_FONT = ("微软雅黑", 10)
WORD_FONT = ("微软雅黑", 13, "bold")
PHON_FONT = ("微软雅黑", 10)
POS_FONT = ("微软雅黑", 10, "bold")
MAIN_FG = "#14171A"
SUB_FG = "#5B6470"
FAINT_FG = "#8A94A3"
LINE = "#EBEEF2"
CARD_BG = "#FFFFFF"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_PRESS = "#1E40AF"
HOVER_BG = "#F2F4F7"
KEY_COLOR = "#FF00FE"
ICON_FG = "#98A2B0"
RADIUS = 12
EDGE = "#E6E9EF"
PAD_X = 18
ICON_BTN = 28


def _hex_to_rgb(颜色):
    颜色 = 颜色.lstrip("#")
    return (int(颜色[0:2], 16), int(颜色[2:4], 16), int(颜色[4:6], 16))


def _make_tray_image():
    """64x64 蓝色圆底 + 白色译字，不依赖外部图片文件。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 61, 61], fill=(30, 120, 255, 255))
    try:
        # 中文用微软雅黑，找不到就用默认字体
        font = ImageFont.truetype("msyh.ttc", 30)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    try:
        d.text((32, 33), "译", fill="white", anchor="mm", font=font)
    except Exception:
        d.text((22, 18), "译", fill="white", font=font)
    return img


def _图标底布(边=32):
    """透明正方形画布：所有图标共享的 32x32 可点击热区。"""
    return Image.new("RGBA", (边, 边), (0, 0, 0, 0))


def _make_copy_image(边=32):
    """复制图标：后纸纯描边 + 前纸白底填充再描边，遮挡关系才读得出来。"""
    画 = _图标底布(边)
    d = ImageDraw.Draw(画)
    灰 = _hex_to_rgb(ICON_FG)
    中 = 边 // 2
    # 后纸（右上）：只描边，不填充
    d.rounded_rectangle(
        [中 - 2, 中 - 9, 中 + 8, 中 + 1], radius=2, outline=灰 + (255,), width=2
    )
    # 前纸（左下）：白底填充 + 描边，盖住后纸的交叠处
    d.rounded_rectangle(
        [中 - 8, 中 - 3, 中 + 2, 中 + 9],
        radius=2,
        fill=(255, 255, 255, 255),
        outline=灰 + (255,),
        width=2,
    )
    return ImageTk.PhotoImage(画)


def _make_close_image(边=32):
    """关闭 ✕：两笔细线，低对比灰。"""
    画 = _图标底布(边)
    d = ImageDraw.Draw(画)
    灰 = _hex_to_rgb(ICON_FG)
    中 = 边 // 2
    半 = 5
    d.line([中 - 半, 中 - 半, 中 + 半, 中 + 半], fill=灰 + (255,), width=2, joint="curve")
    d.line([中 + 半, 中 - 半, 中 - 半, 中 + 半], fill=灰 + (255,), width=2, joint="curve")
    return ImageTk.PhotoImage(画)


def _make_chevron_image(展开=False, 边=32):
    """下 / 上箭头：三点折线，低对比灰。"""
    画 = _图标底布(边)
    d = ImageDraw.Draw(画)
    灰 = _hex_to_rgb(ICON_FG)
    中 = 边 // 2
    if 展开:
        点 = [(中 - 5, 中 + 3), (中, 中 - 2), (中 + 5, 中 + 3)]
    else:
        点 = [(中 - 5, 中 - 3), (中, 中 + 2), (中 + 5, 中 - 3)]
    d.line(点, fill=灰 + (255,), width=2, joint="curve")
    return ImageTk.PhotoImage(画)


def _make_gear_image(边=32):
    """齿轮：18px 外径、6 齿、机身 r=6.5；16px/8 齿在小尺寸下会糊成一团。"""
    画 = _图标底布(边)
    d = ImageDraw.Draw(画)
    灰 = _hex_to_rgb(SUB_FG)
    中 = 边 / 2.0
    import math

    外 = 9.0  # 18px 外径 / 2
    根 = 5.6  # 齿根（机身边缘附近）
    for i in range(6):
        角 = math.pi / 3 * i
        x1, y1 = 中 + 根 * math.cos(角), 中 + 根 * math.sin(角)
        x2, y2 = 中 + 外 * math.cos(角), 中 + 外 * math.sin(角)
        d.line([x1, y1, x2, y2], fill=灰 + (255,), width=3)
    机身 = 6.5
    d.ellipse(
        [中 - 机身, 中 - 机身, 中 + 机身, 中 + 机身],
        fill=(255, 255, 255, 255),
        outline=灰 + (255,),
        width=2,
    )
    孔 = 2.3
    d.ellipse(
        [中 - 孔, 中 - 孔, 中 + 孔, 中 + 孔],
        outline=灰 + (255,),
        width=2,
    )
    return ImageTk.PhotoImage(画)


def _make_primary_button_image(状态="normal", 宽=96, 高=32, 半径=8):
    """翻译主按钮底图：圆角 8px 纯色块；Tk 原生按钮画不出圆角。"""
    色 = {"normal": ACCENT, "hover": ACCENT_HOVER, "press": ACCENT_PRESS}.get(
        状态, ACCENT
    )
    超 = 3
    大 = (宽 * 超, 高 * 超)
    画 = Image.new("RGBA", 大, (0, 0, 0, 0))
    d = ImageDraw.Draw(画)
    d.rounded_rectangle(
        [0, 0, 大[0] - 1, 大[1] - 1], radius=半径 * 超, fill=_hex_to_rgb(色) + (255,)
    )
    画 = 画.resize((宽, 高), Image.LANCZOS)
    return ImageTk.PhotoImage(画)


def _make_secondary_button_image(状态="normal", 宽=96, 高=32, 半径=8):
    """次要按钮底图：圆角浅灰块；+ 新方案 / 删除 共用。"""
    色 = {"normal": HOVER_BG, "hover": "#E6E9EF", "press": "#DCE0E6"}.get(
        状态, HOVER_BG
    )
    超 = 3
    大 = (宽 * 超, 高 * 超)
    画 = Image.new("RGBA", 大, (0, 0, 0, 0))
    d = ImageDraw.Draw(画)
    d.rounded_rectangle(
        [0, 0, 大[0] - 1, 大[1] - 1], radius=半径 * 超, fill=_hex_to_rgb(色) + (255,)
    )
    画 = 画.resize((宽, 高), Image.LANCZOS)
    return ImageTk.PhotoImage(画)


def _make_corner_image(角, 边=13, 半径=RADIUS):
    """圆角遮罩：角外透明、角内填白、1px EDGE 描边；超采样抗锯齿。

    角 ∈ {"tl", "tr", "bl", "br"}；圆心取对应卡片内角。
    """
    超 = 4
    大 = 边 * 超
    R = 半径 * 超
    中心 = {"tl": (大, 大), "tr": (0, 大), "bl": (大, 0), "br": (0, 0)}[角]
    白 = Image.new("L", (大, 大), 0)
    描 = Image.new("L", (大, 大), 0)
    dp = ImageDraw.Draw(白)
    dp.ellipse(
        [中心[0] - R, 中心[1] - R, 中心[0] + R, 中心[1] + R], fill=255
    )
    de = ImageDraw.Draw(描)
    de.ellipse(
        [中心[0] - R, 中心[1] - R, 中心[0] + R, 中心[1] + R],
        outline=255,
        width=max(1, 超 // 2),
    )
    # 角内其余部分（圆心所在的整行/整列）补白：圆只盖住扇形，边缘条带要填满
    if 角 == "tl":
        dp.rectangle([中心[0] - R, 中心[1], 大, 大], fill=255)
        dp.rectangle([中心[0], 0, 大, 大], fill=255)
    elif 角 == "tr":
        dp.rectangle([0, 中心[1], 中心[0] + R, 大], fill=255)
        dp.rectangle([0, 0, 中心[0], 大], fill=255)
    elif 角 == "bl":
        dp.rectangle([中心[0] - R, 0, 大, 中心[1] + R], fill=255)
        dp.rectangle([中心[0], 0, 大, 大], fill=255)
    else:
        dp.rectangle([0, 0, 中心[0] + R, 中心[1] + R], fill=255)
        dp.rectangle([0, 0, 中心[0], 大], fill=255)
        dp.rectangle([0, 0, 大, 中心[1]], fill=255)
    白 = 白.resize((边, 边), Image.LANCZOS)
    描 = 描.resize((边, 边), Image.LANCZOS)
    画 = Image.new("RGBA", (边, 边), (0, 0, 0, 0))
    白点 = 白.load()
    描点 = 描.load()
    像素 = 画.load()
    边色 = _hex_to_rgb(EDGE)
    # 二值 alpha：半透明像素盖在 KEY_COLOR 底上会调出粉边，
    # 色键只能抠掉纯透明像素，所以覆盖过半才画，否则全透。
    for y in range(边):
        for x in range(边):
            if 描点[x, y] >= 128:
                像素[x, y] = 边色 + (255,)
            elif 白点[x, y] >= 128:
                像素[x, y] = (255, 255, 255, 255)
    return ImageTk.PhotoImage(画)


def _make_tip_image(文本):
    """深色圆角气泡：整块用 PIL 画，边角靠色键抠掉，返回 PhotoImage。"""
    try:
        font = ImageFont.truetype("msyh.ttc", 12)
    except Exception:
        font = ImageFont.load_default()
    try:
        bbox = font.getbbox(文本)
    except Exception:
        bbox = None
    if bbox:
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        tw, th = 72, 15
    pad_x, pad_y = 8, 4
    W = max(1, tw + pad_x * 2)
    H = max(1, th + pad_y * 2)
    超 = 4
    # 只把圆角遮罩超采样再二值化：半透明像素盖在色键上会出粉边，
    # 而色键只能抠纯透明，所以覆盖过半才留，否则全透。
    遮 = Image.new("L", (W * 超, H * 超), 0)
    ImageDraw.Draw(遮).rounded_rectangle(
        [0, 0, W * 超 - 1, H * 超 - 1], radius=6 * 超, fill=255
    )
    遮 = 遮.resize((W, H), Image.LANCZOS).point(lambda v: 255 if v >= 128 else 0)
    画 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    画.paste(
        Image.new("RGBA", (W, H), _hex_to_rgb("#2A2F36") + (255,)), (0, 0), 遮
    )
    d = ImageDraw.Draw(画)
    tx = pad_x - (bbox[0] if bbox else 0)
    ty = pad_y - (bbox[1] if bbox else 0)
    try:
        d.text((tx, ty), 文本, fill=(255, 255, 255, 255), font=font)
    except Exception:
        d.text((pad_x, pad_y), 文本, fill=(255, 255, 255, 255), font=font)
    return ImageTk.PhotoImage(画)


class _Tip:
    """跟鼠标的小提示：图标旁边浮一句，移开或 1.5 秒后就没。"""
    _深底 = "#2A2F36"

    def __init__(self, 根):
        self._根 = 根
        self._窗 = None
        self._after = None
        self._图 = None

    def show(self, 文本, x, y):
        self.hide()
        try:
            w = tk.Toplevel(self._根)
            w.overrideredirect(True)
            w.attributes("-topmost", True)
            if HAS_PIL:
                图 = _make_tip_image(文本)
                self._图 = 图
                标 = tk.Label(
                    w, image=图, bg=KEY_COLOR, bd=0, highlightthickness=0,
                    borderwidth=0, padx=0, pady=0,
                )
                标.pack()
                try:
                    w.wm_attributes("-transparentcolor", KEY_COLOR)
                except Exception:
                    # 色键不可用：退回无边框纯色方块，先保证字看得清
                    self._图 = None
                    try:
                        标.destroy()
                    except Exception:
                        pass
                    标 = tk.Label(
                        w, text=文本, font=("微软雅黑", 9),
                        foreground="#FFFFFF", background=self._深底,
                        bd=0, highlightthickness=0, padx=8, pady=4,
                    )
                    标.pack()
            else:
                标 = tk.Label(
                    w, text=文本, font=("微软雅黑", 9),
                    foreground="#FFFFFF", background=self._深底,
                    bd=0, highlightthickness=0, padx=8, pady=4,
                )
                标.pack()
            w.geometry(f"+{int(x) + 14}+{int(y) + 12}")
            self._窗 = w
            self._after = self._根.after(1500, self.hide)
        except Exception:
            self._窗 = None

    def hide(self):
        try:
            if self._after is not None:
                try:
                    self._根.after_cancel(self._after)
                except Exception:
                    pass
                self._after = None
        except Exception:
            pass
        窗, self._窗 = self._窗, None
        try:
            if 窗 is not None:
                窗.destroy()
        except Exception:
            pass
