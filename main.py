"""
VRChat 自动钓鱼脚本 — 入口
============================
启动 tkinter GUI 界面。

快捷键 (VRChat 内也可用):
    F9  = 开始 / 暂停
    F10 = 停止
    F11 = 调试模式
"""

import tkinter as tk
from gui.app import FishingApp


def main():
    root = tk.Tk()
    FishingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
