#!/usr/bin/env python3
"""
VRChat 窗口捕获器
使用 mss 库捕获 Linux 桌面上的 VRChat 窗口
支持窗口拖动后自动更新位置
"""

import cv2
import numpy as np
import subprocess
import re
import time
import mss
from typing import Optional, Tuple


class X11WindowCapture:
    """X11 窗口捕获类"""

    def __init__(self, window_name: str = "VRChat", update_interval: int = 10):
        self.window_name = window_name
        self.window_id: Optional[int] = None
        self.window_rect: Optional[Tuple[int, int, int, int]] = None
        self.sct = mss.mss()
        self.update_interval = update_interval  # 每 N 帧更新一次窗口位置
        self.frame_count = 0

    def find_window(self) -> bool:
        """查找 VRChat 窗口并获取窗口 ID"""
        try:
            # 使用 xwininfo 查找窗口（不使用 -root）
            result = subprocess.run(
                ['xwininfo', '-name', self.window_name],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"未找到窗口: {self.window_name}")
                print("可用的窗口列表:")
                self._list_windows()
                return False

            # 解析窗口 ID
            match = re.search(r'Window id: (0x[0-9a-fA-F]+)', result.stdout)
            if match:
                self.window_id = int(match.group(1), 16)
                print(f"找到窗口 ID: {hex(self.window_id)}")

                # 获取窗口位置和大小
                self._get_window_geometry()
                return True
            else:
                print("无法解析窗口 ID")
                return False

        except Exception as e:
            print(f"查找窗口时出错: {e}")
            return False

    def _get_window_geometry(self) -> bool:
        """获取窗口的几何信息（位置和大小）"""
        try:
            result = subprocess.run(
                ['xwininfo', '-id', str(self.window_id)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False

            # 解析窗口几何信息
            x = y = width = height = 0

            x_match = re.search(r'Absolute upper-left X:\s+(\d+)', result.stdout)
            y_match = re.search(r'Absolute upper-left Y:\s+(\d+)', result.stdout)
            width_match = re.search(r'Width:\s+(\d+)', result.stdout)
            height_match = re.search(r'Height:\s+(\d+)', result.stdout)

            if x_match:
                x = int(x_match.group(1))
            if y_match:
                y = int(y_match.group(1))
            if width_match:
                width = int(width_match.group(1))
            if height_match:
                height = int(height_match.group(1))

            self.window_rect = (x, y, width, height)
            # print(f"窗口位置和大小: x={x}, y={y}, width={width}, height={height}")
            return True

        except Exception as e:
            print(f"获取窗口几何信息时出错: {e}")
            return False

    def _list_windows(self):
        """列出所有可用的窗口"""
        try:
            result = subprocess.run(
                ['wmctrl', '-l'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(result.stdout)
            else:
                print("需要安装 wmctrl 来查看窗口列表")
                print("可以运行: sudo apt install wmctrl")

        except Exception as e:
            print(f"列出窗口时出错: {e}")

    def capture(self) -> Optional[np.ndarray]:
        """捕获窗口内容"""
        # 定期更新窗口位置（支持窗口拖动）
        self.frame_count += 1
        if self.frame_count % self.update_interval == 0:
            self._update_window_position()

        if not self.window_id or not self.window_rect:
            if not self.find_window():
                return None

        try:
            x, y, width, height = self.window_rect

            # 使用 mss 直接捕获屏幕区域
            monitor = {"top": y, "left": x, "width": width, "height": height}
            screenshot = self.sct.grab(monitor)

            # 转换为 numpy 数组并调整颜色顺序 (BGRA -> BGR)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            return frame

        except Exception as e:
            print(f"捕获窗口时出错: {e}")
            return None

    def _update_window_position(self):
        """更新窗口位置"""
        if self.window_id:
            self._get_window_geometry()


def main():
    """主函数"""
    print("VRChat 窗口捕获器")
    print("=" * 50)

    # 创建捕获器实例（每 10 帧更新一次窗口位置）
    capturer = X11WindowCapture("VRChat", update_interval=10)

    # 查找窗口
    if not capturer.find_window():
        print("\n提示:")
        print("1. 确保 VRChat 正在运行")
        print("2. 检查窗口名称是否为 'VRChat'")
        print("3. 可以尝试修改 window_name 参数匹配实际窗口名称")
        print("\n安装必要的工具:")
        print("sudo apt install x11-utils")
        print("pip install mss opencv-python")
        return

    print("\n开始捕获窗口...")

    try:
        while True:
            # 捕获窗口
            frame = capturer.capture()

            if frame is not None:
                # 显示捕获的图像
                cv2.imshow('VRChat Capture', frame)

                # 按 'q' 键退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("捕获失败，重试中...")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n用户中断")

    except Exception as e:
        print(f"\n发生错误: {e}")

    finally:
        cv2.destroyAllWindows()
        print("程序结束")


if __name__ == "__main__":
    main()