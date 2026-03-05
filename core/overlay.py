"""
ROI Overlay (Linux 版本)
========================
Linux 环境下不支持透明覆盖窗口，提供兼容的空实现。

在 X11 环境下，创建真正的透明覆盖窗口需要使用 Xlib 或 xcb，
这会比较复杂。为了保持简洁，这里提供空实现。
"""

from utils.logger import log


class RoiOverlay:
    """ROI 覆盖框 (Linux 空实现)"""

    def __init__(self, window_manager):
        self._wm = window_manager
        self._thread = None
        self._running = False
        log.info("[Overlay] Linux 环境下不支持透明覆盖窗口")

    def start(self):
        """启动覆盖框 (Linux 空实现)"""
        pass

    def stop(self):
        """停止覆盖框 (Linux 空实现)"""
        pass

    def _update_position(self):
        """更新位置 (Linux 空实现)"""
        pass