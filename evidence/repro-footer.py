"""复现：底边手柄往上拖，底栏翻译按钮被压没。起真实 App，模拟 press+drag，量 footer 是否被裁。"""
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import app as appmod

appmod.App._start_trigger = lambda self: None
appmod.App._start_tray = lambda self: None
appmod.App._start_singleton_server = lambda self: None

a = appmod.App()
a.src_text.delete("1.0", "end")
a.src_text.insert("1.0", "Copy this English, tap Ctrl, and the Chinese shows up.")
a.dst_text.delete("1.0", "end")
a.dst_text.insert("1.0", "复制这段英文，点一下 Ctrl，中文译文就会冒出来。" * 3)
a.root.deiconify()
a._place_top_right()
a.root.update()
a._refit()
a.root.update()

a.root.update_idletasks()
需要 = int(a.root.winfo_reqheight())
print(f"拖前: window_h={a._window_h} 实际高={a.root.winfo_height()} 内容需要={需要}")

# 模拟：在底边按住，往上拖 300px
y0 = float(a.root.winfo_rooty() + a._window_h)
a._grip_press(SimpleNamespace(y_root=y0))
a._grip_drag(SimpleNamespace(y_root=y0 - 300))
a.root.update()

实际高 = a.root.winfo_height()
footer_h = a.footer.winfo_height()
btn_h = a.translate_btn.winfo_height()
# footer 在 card 里，card 外有 8px 透明边
footer底 = 8 + a.footer.winfo_y() + footer_h
print(f"拖后: window_h={a._window_h} 实际高={实际高} footer_h={footer_h} 按钮_h={btn_h} footer底={footer底}")
print(
    "部件: card_h=%d header=%d dst=%d div=%d src_head=%d src=%d footer=%d req=%d"
    % (
        a.card.winfo_height(), a.header.winfo_height(), a.dst_text.winfo_height(),
        a.divider.winfo_height(), a.src_head.winfo_height(), a.src_text.winfo_height(),
        a.footer.winfo_height(), a.card.winfo_reqheight(),
    )
)
for 子 in a.card.pack_slaves():
    print(
        "  child %-10s y=%-4d h=%-4d req_h=%-4d info=%s"
        % (子.winfo_class(), 子.winfo_y(), 子.winfo_height(), 子.winfo_reqheight(),
           子.pack_info())
    )
print(f"footer 是否被裁: {footer底 > 实际高}")
print(f"RED(有bug)={footer底 > 实际高 or footer_h != 32 or btn_h != 32}")

a.on_quit()
