"""translator_theme.py
[INPUT] 父容器、文本、命令与坐标等展示参数（由调用方传入）
[OUTPUT] 带统一样式的按钮/提示/托盘图标对象，以及字体颜色常量
[POS] 展示层之下的主题与小部件工厂，只管样子不管行为
[PROTOCOL] 纯搬运 app.py 现有代码，不改逻辑；不依赖本项目其他模块
"""

import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except Exception:
    HAS_PIL = False

FONT = ("微软雅黑", 11)
SRC_FONT = ("微软雅黑", 10)
TITLE_FONT = ("微软雅黑", 10)
WORD_FONT = ("微软雅黑", 13, "bold")
PHON_FONT = ("微软雅黑", 10)
POS_FONT = ("微软雅黑", 10, "bold")
MAIN_FG = "#1B1B1B"
SUB_FG = "#616161"
FAINT_FG = "#8A8A8A"
LINE = "#EDEBE9"
CARD_BORDER = "#E1E1E1"
ROOT_BG = "#F3F3F3"
CARD_BG = "#FFFFFF"
ACCENT = "#0078D4"
ACCENT_HOVER = "#106EBE"
ACCENT_PRESS = "#005A9E"
DARK_BTN = ACCENT
HINT_FG = "#616161"

def _按钮(父, 文本, 命令, 主=False, 链接=False):
    if 链接:
        return tk.Button(
            父,
            text=文本,
            command=命令,
            relief="flat",
            bd=0,
            bg="#ffffff",
            fg="#616161",
            activebackground="#F3F3F3",
            activeforeground="#1B1B1B",
            font=("微软雅黑", 10),
            cursor="hand2",
            padx=6,
            pady=0,
            takefocus=0,
        )
    if 主:
        return tk.Button(
            父,
            text=文本,
            command=命令,
            relief="flat",
            bd=0,
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            font=("微软雅黑", 11),
            cursor="hand2",
            padx=10,
            pady=6,
            takefocus=0,
        )
    return tk.Button(
        父,
        text=文本,
        command=命令,
        relief="flat",
        bd=0,
        bg="#E8EAED",
        fg="#333333",
        activebackground="#D8DBDF",
        activeforeground="#111111",
        font=("微软雅黑", 10),
        cursor="hand2",
        padx=10,
        pady=4,
        takefocus=0,
    )


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


class _Tip:
    """跟鼠标的小提示：图标旁边浮一句，移开或 1.5 秒后就没。"""
    def __init__(self, 根):
        self._根 = 根
        self._窗 = None
        self._after = None

    def show(self, 文本, x, y):
        self.hide()
        try:
            w = tk.Toplevel(self._根)
            w.overrideredirect(True)
            w.attributes("-topmost", True)
            tk.Label(
                w, text=文本, font=("微软雅黑", 9),
                foreground="#323130", background="#FFFFFF",
                relief="solid", borderwidth=1, padx=6, pady=2,
            ).pack()
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
