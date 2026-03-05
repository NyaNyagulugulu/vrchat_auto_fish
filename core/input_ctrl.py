"""
输入控制模块
============
使用 X11/XTest 进行鼠标控制 + OSC 摇头
"""

import subprocess
import time

from utils.logger import log


class InputController:
    """XTest 鼠标控制器 + OSC 摇头"""

    def __init__(self, window_mgr):
        self.wm = window_mgr
        self.mouse_is_down = False
        self._click_x = 400
        self._click_y = 400

    # ────────────────── 内部工具 ──────────────────

    def _update_click_pos(self):
        region = self.wm.get_region()
        if region:
            self._click_x = region[0] + region[2] // 2
            self._click_y = region[1] + region[3] // 2

    def _mouse_move(self, x, y):
        """移动鼠标到指定位置"""
        try:
            subprocess.run(
                ['xdotool', 'mousemove', str(int(x)), str(int(y))],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            log.warning(f"移动鼠标失败: {e}")

    def _mouse_click(self, button=1):
        """鼠标点击"""
        try:
            subprocess.run(
                ['xdotool', 'click', str(button)],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            log.warning(f"鼠标点击失败: {e}")

    def _mouse_down(self, button=1):
        """鼠标按下"""
        try:
            subprocess.run(
                ['xdotool', 'mousedown', str(button)],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            log.warning(f"鼠标按下失败: {e}")

    def _mouse_up(self, button=1):
        """鼠标松开"""
        try:
            subprocess.run(
                ['xdotool', 'mouseup', str(button)],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            log.warning(f"鼠标松开失败: {e}")

    # ────────────────── 聚焦 ──────────────────

    def focus_game(self) -> bool:
        ok = self.wm.focus()
        if ok:
            self._update_click_pos()
        else:
            log.warning("无法聚焦 VRChat 窗口")
        return ok

    def move_to_game_center(self):
        """移动鼠标到游戏窗口中心"""
        self._update_click_pos()
        self._mouse_move(self._click_x, self._click_y)

    def ensure_cursor_in_game(self):
        """确保鼠标在游戏窗口内"""
        region = self.wm.get_region()
        if region:
            # 简单检查：将鼠标移到窗口中心
            self._update_click_pos()
            self._mouse_move(self._click_x, self._click_y)

    # ────────────────── 鼠标操作 ──────────────────

    def click(self, focus: bool = False):
        """点击鼠标"""
        if focus:
            self.focus_game()
            time.sleep(0.1)
        self._update_click_pos()
        self._mouse_move(self._click_x, self._click_y)
        time.sleep(0.05)
        self._mouse_click(1)

    def click_rapid(self):
        """快速点击"""
        self._mouse_click(1)

    def mouse_down(self):
        """按下鼠标"""
        if not self.mouse_is_down:
            self._mouse_down(1)
            self.mouse_is_down = True

    def mouse_up(self):
        """松开鼠标"""
        if self.mouse_is_down:
            self._mouse_up(1)
            self.mouse_is_down = False

    # ────────────────── 摇头 (OSC) ──────────────────

    def shake_head(self):
        """抛竿前摇头: 右→左，对称两步，始终通过 OSC。"""
        import config as _cfg
        t = getattr(_cfg, "SHAKE_HEAD_TIME", 0.01)
        if t <= 0:
            return
        try:
            from pythonosc import udp_client
            osc = udp_client.SimpleUDPClient("127.0.0.1", 9000)
        except Exception:
            return
        try:
            osc.send_message("/input/LookRight", 1)
            time.sleep(t)
            osc.send_message("/input/LookRight", 0)
            time.sleep(0.05)

            osc.send_message("/input/LookLeft", 1)
            time.sleep(t)
            osc.send_message("/input/LookLeft", 0)
            time.sleep(0.05)
        except Exception:
            pass

    # ────────────────── 安全 ──────────────────

    def safe_release(self):
        """安全释放鼠标"""
        try:
            if self.mouse_is_down:
                self._mouse_up(1)
        except Exception:
            pass
        self.mouse_is_down = False