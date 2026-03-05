"""
窗口管理模块
============
- 查找 VRChat 窗口（标题模糊匹配）
- 支持 X11 (Linux) 和 Wayland (Linux)
"""

import os
import subprocess
import time

from utils.logger import log


class WindowManager:
    """VRChat 窗口管理器 (Linux 版本)"""

    def __init__(self, title_keyword: str = "VRChat"):
        self.title_keyword = title_keyword
        self.window_id = None
        self._title = ""
        self._rect = None  # (x, y, w, h)
        self._display = None
        self._x11_available = self._check_x11()

    def _check_x11(self):
        """检查是否使用 X11"""
        try:
            return 'DISPLAY' in os.environ and os.environ['DISPLAY']
        except Exception:
            return False

    def _get_window_info_x11(self):
        """使用 xdotool 获取窗口信息"""
        try:
            result = subprocess.run(
                ['xdotool', 'search', '--name', self.title_keyword],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                window_ids = result.stdout.strip().split('\n')
                # 排除可能的自身窗口
                for wid in window_ids:
                    title_result = subprocess.run(
                        ['xdotool', 'getwindowname', wid],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if title_result.returncode == 0:
                        title = title_result.stdout.strip()
                        # 排除包含自动钓鱼关键字的窗口
                        exclude_keywords = ["自动钓鱼", "auto-fish", "auto fish", "Fishing"]
                        if not any(kw.lower() in title.lower() for kw in exclude_keywords):
                            # 获取窗口位置和大小
                            geom_result = subprocess.run(
                                ['xdotool', 'getwindowgeometry', wid],
                                capture_output=True,
                                text=True,
                                timeout=1
                            )
                            if geom_result.returncode == 0:
                                # 解析几何信息
                                lines = geom_result.stdout.split('\n')
                                pos_line = [l for l in lines if 'Position' in l]
                                size_line = [l for l in lines if 'Geometry' in l]

                                if pos_line and size_line:
                                    # Position: 100,200 (screen 0) or Position: 100,200
                                    # 提取坐标部分
                                    pos_text = pos_line[0].split(':')[1].strip()
                                    # 移除括号中的screen信息
                                    if '(' in pos_text:
                                        pos_text = pos_text.split('(')[0].strip()
                                    pos = pos_text.split(',')
                                    if len(pos) >= 2:
                                        x = int(pos[0].strip())
                                        y = int(pos[1].strip())

                                        # Geometry: 1920x1080
                                        size = size_line[0].split(':')[1].strip().split('x')
                                        w = int(size[0].strip())
                                        h = int(size[1].strip())

                                        return wid, title, (x, y, w, h)
                return None, None, None
            return None, None, None
        except FileNotFoundError:
            log.warning("xdotool 未安装，请运行: sudo apt install xdotool")
            return None, None, None
        except subprocess.TimeoutExpired:
            log.warning("获取窗口信息超时")
            return None, None, None
        except Exception as e:
            log.warning(f"获取窗口信息失败: {e}")
            return None, None, None

    def _get_window_info_wayland(self):
        """使用 wl-clipboard 或其他工具获取窗口信息 (Wayland)"""
        # Wayland 的窗口管理比较复杂，这里提供一个基本实现
        # 实际使用可能需要更复杂的解决方案
        log.warning("Wayland 支持有限，建议使用 X11 会话")
        return None, None, None

    def find(self) -> bool:
        """
        查找 VRChat 窗口
        """
        if self._x11_available:
            wid, title, rect = self._get_window_info_x11()
            if wid:
                self.window_id = wid
                self._title = title
                self._rect = rect
                log.info(f"找到窗口: \"{self._title}\" (ID={self.window_id})")
                return True

        log.warning(f"未找到包含 \"{self.title_keyword}\" 的窗口")
        self.window_id = None
        return False

    def focus(self) -> bool:
        """
        聚焦 VRChat 窗口
        """
        if not self.is_valid():
            if not self.find():
                return False

        try:
            if self._x11_available and self.window_id:
                subprocess.run(
                    ['xdotool', 'windowactivate', self.window_id],
                    capture_output=True,
                    timeout=2
                )
                time.sleep(0.1)
                return True
        except Exception as e:
            log.warning(f"聚焦窗口失败: {e}")
            return False

        return False

    def get_region(self):
        """
        获取窗口在屏幕上的区域 (x, y, w, h)
        """
        if not self.is_valid():
            if not self.find():
                return None

        if self._rect:
            x, y, w, h = self._rect
            if w > 0 and h > 0:
                return (x, y, w, h)

        return None

    def is_valid(self) -> bool:
        """检查窗口是否有效"""
        if not self.window_id:
            return False

        try:
            if self._x11_available:
                result = subprocess.run(
                    ['xdotool', 'getwindowname', self.window_id],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                return result.returncode == 0
        except Exception:
            return False

        return False

    def is_foreground(self) -> bool:
        """检查窗口是否在前台"""
        if not self.is_valid():
            return False

        try:
            if self._x11_available:
                result = subprocess.run(
                    ['xdotool', 'getactivewindow'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    active_wid = result.stdout.strip()
                    return active_wid == self.window_id
        except Exception:
            return False

        return False

    @property
    def title(self) -> str:
        return self._title

    @property
    def hwnd(self):
        """为了兼容性保留 hwnd 属性"""
        return self.window_id