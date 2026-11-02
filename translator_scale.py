"""translator_scale.py
[INPUT] 无（读 Windows 系统 DPI；可用 TRANSLATOR_UI_SCALE 环境变量覆盖，仅作预览用）。
[OUTPUT] UI_SCALE（1.0 = 100%）、px(值) 像素换算、tk_scaling() 字号基准。
[POS] 环境层：零项目依赖；被 theme / layout / app / settings_window 共用。
[PROTOCOL] 导入即声明进程 DPI 感知；所有 96dpi 设计稿像素都必须过 px()，字号用 point 由 Tk 自己缩放。
"""

import ctypes
import os


def _声明_dpi_感知():
    """必须在任何 Tk 窗口创建之前调用，否则 Windows 会把整窗当图片拉大（发虚）。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _系统_dpi():
    try:
        return int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        pass
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, 88))  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi
    except Exception:
        return 96


_声明_dpi_感知()

_覆盖 = os.environ.get("TRANSLATOR_UI_SCALE", "").strip()
try:
    UI_SCALE = float(_覆盖) if _覆盖 else _系统_dpi() / 96.0
except Exception:
    UI_SCALE = _系统_dpi() / 96.0

UI_SCALE = max(1.0, min(UI_SCALE, 2.0))


def px(值):
    """把 96dpi 设计稿上的像素换算成当前屏幕像素。"""
    return int(round(float(值) * UI_SCALE))


def tk_scaling():
    """Tk 的点→像素基准，与 px() 同步，字体和留白一起放大。"""
    return 96.0 * UI_SCALE / 72.0
