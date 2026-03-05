"""
屏幕截取模块
============
使用 mss 进行屏幕截取 (Linux 版本)

支持两种截取方式:
1. 窗口截取 - 通过窗口位置和大小截取
2. 全屏截取 - 回退方案

注意: mss 实例是线程本地的，不能跨线程使用。
"""

import os
import threading
import cv2
import numpy as np
from mss import mss

import config
from utils.logger import log


class ScreenCapture:
    """高速屏幕截取器（线程安全）"""

    def __init__(self):
        self._local = threading.local()   # 每个线程独立的 mss 实例
        self.screen_w = 0
        self.screen_h = 0

        # 主线程中获取屏幕尺寸
        sct = self._get_sct()
        primary = sct.monitors[1]
        self.screen_w = primary["width"]
        self.screen_h = primary["height"]

        # 确保 debug 目录存在
        os.makedirs(config.DEBUG_DIR, exist_ok=True)

    def _get_sct(self):
        """获取当前线程的 mss 实例（延迟初始化）"""
        if not hasattr(self._local, "sct") or self._local.sct is None:
            self._local.sct = mss()
        return self._local.sct

    # ────────────────── 屏幕截取 ──────────────────

    def grab(self, region=None):
        """
        截取屏幕。
        Args:
            region: (x, y, w, h) 或 None=全屏
        Returns:
            BGR numpy 数组
        """
        sct = self._get_sct()

        if region:
            mon = {
                "left":   int(region[0]),
                "top":    int(region[1]),
                "width":  max(1, int(region[2])),
                "height": max(1, int(region[3])),
            }
        else:
            mon = sct.monitors[1]

        raw = np.array(sct.grab(mon))
        return raw[:, :, :3].copy()

    # ────────────────── 主接口 ──────────────────

    def grab_window(self, window_mgr):
        """
        截取 VRChat 窗口的客户区。

        Args:
            window_mgr: WindowManager 实例
        Returns:
            (image, region)  — region 为 (x, y, w, h) 或 None
        """
        region = window_mgr.get_region()
        if region and region[2] > 0 and region[3] > 0:
            return self.grab(region), region

        # 最后回退: 全屏
        return self.grab(), None

    # ────────────────── 工具方法 ──────────────────

    def save_debug(self, image, name: str = "screenshot"):
        """保存调试截图到 debug/ 目录"""
        path = os.path.join(config.DEBUG_DIR, f"{name}.png")
        cv2.imwrite(path, image)
        log.debug(f"调试截图已保存: {path}")

    def reset_capture_method(self):
        """
        重置截取方式检测。
        (Linux 版本不需要，保留接口兼容性)
        """
        pass