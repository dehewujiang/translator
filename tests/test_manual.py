"""点“翻译”按钮时，框里自己打的字优先于剪贴板（离线，不建托盘/钩子）。

[INPUT] 剪贴板放旧文、原文框打 translator。
[OUTPUT] unittest 断言；只建一个 Tk 窗口，跑完就关，不联网。
[PROTOCOL] 运行：python -m unittest discover -s tests -v
"""

import unittest

import app as appmod


class 翻译按钮优先框里打的字(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        appmod.App._start_trigger = lambda self: None
        appmod.App._start_tray = lambda self: None
        appmod.App._start_singleton_server = lambda self: None

    def setUp(self):
        self.a = appmod.App()
        self.a.root.withdraw()
        self.抓到 = []
        self.a._run_translate = lambda 文本, 热键: self.抓到.append((文本, 热键))

    def tearDown(self):
        try:
            self.a.on_quit()
        except Exception:
            try:
                self.a.root.destroy()
            except Exception:
                pass

    def test_框里打的字不被剪贴板覆盖(self):
        self.a.read_clip = lambda: "上一次复制的一段话"
        self.a.src_text.delete("1.0", "end")
        self.a.src_text.insert("1.0", "translator")
        self.a.on_manual(from_hotkey=False)
        self.assertEqual(len(self.抓到), 1)
        self.assertEqual(self.抓到[0][0], "translator")
        self.assertIn("translator", self.a.src_text.get("1.0", "end"))

    def test_轻点Ctrl还是翻剪贴板(self):
        self.a.read_clip = lambda: "hello world"
        self.a.src_text.delete("1.0", "end")
        self.a.src_text.insert("1.0", "translator")
        self.a.on_manual(from_hotkey=True)
        self.assertEqual(len(self.抓到), 1)
        self.assertEqual(self.抓到[0][0], "hello world")

    def test_原文框回车直接翻译(self):
        序列 = self.a.src_text.bind()
        self.assertTrue("<Return>" in 序列 or "<Key-Return>" in 序列)
        self.a.src_text.delete("1.0", "end")
        self.a.src_text.insert("1.0", "translator")
        结果 = self.a._on_src_return(None)
        self.assertEqual(结果, "break")
        self.assertEqual(len(self.抓到), 1)
        self.assertEqual(self.抓到[0][0], "translator")

    def test_AltQ调出后光标落在原文框(self):
        self.a.root.deiconify()
        self.a.root.update()
        self.a.src_text.delete("1.0", "end")
        self.a.src_text.insert("1.0", "translator")
        self.a._summon_and_focus()
        self.a.root.update()
        self.assertEqual(str(self.a.src_text), str(self.a.root.focus_get()))
        self.assertTrue(self.a.src_text.tag_ranges("sel"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
