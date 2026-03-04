#!/usr/bin/env python3
"""
VRChat 窗口捕获器
使用 mss 库捕获 Linux 桌面上的 VRChat 窗口
支持窗口拖动后自动更新位置
支持自动钓鱼功能
"""

import cv2
import numpy as np
import subprocess
import re
import time
import mss
import os
import pyautogui
from typing import Optional, Tuple


class FishAutoBot:
    """自动钓鱼机器人"""

    def __init__(self, img_dir: str = "img"):
        self.img_dir = img_dir
        self.templates = {}
        self.current_state = 1  # 当前检测到的状态
        self.expected_state = 1  # 预期的下一个状态
        self.state_start_time = 0
        self.window_rect = None  # 窗口位置信息
        self.window_id = None  # 窗口 ID
        self.load_templates()

    def set_window_rect(self, rect: Tuple[int, int, int, int]):
        """设置窗口位置信息"""
        self.window_rect = rect

    def set_window_id(self, window_id: int):
        """设置窗口 ID"""
        self.window_id = window_id

    def load_templates(self):
        """加载模板图片"""
        for state_dir in range(1, 6):  # 1-5
            state_path = os.path.join(self.img_dir, str(state_dir))
            if os.path.isdir(state_path):
                self.templates[state_dir] = []
                # 加载该目录下的所有图片
                for filename in os.listdir(state_path):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        filepath = os.path.join(state_path, filename)
                        template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                        if template is not None:
                            self.templates[state_dir].append(template)
                            print(f"加载模板: 状态{state_dir}/{filename}")
                print(f"状态{state_dir} 共加载 {len(self.templates[state_dir])} 个模板")
            else:
                print(f"警告: 找不到状态目录 {state_path}")

    def detect_state(self, frame: np.ndarray) -> Optional[int]:
        """检测当前状态"""
        best_match = None
        best_score = 0
        threshold = 0.5  # 进一步降低阈值
        state_scores = {}

        for state, templates in self.templates.items():
            if not templates:
                continue

            # 对该状态的所有模板进行匹配，取最高分数
            state_best_score = 0
            for template in templates:
                result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if max_val > state_best_score:
                    state_best_score = max_val

            state_scores[state] = state_best_score

            # 更新全局最佳匹配
            if state_best_score > best_score:
                best_score = state_best_score
                best_match = state

        # 显示所有状态的匹配分数
        scores_str = ", ".join([f"状态{k}:{v:.3f}" for k, v in sorted(state_scores.items())])
        print(f"匹配分数: {scores_str}")

        if best_score >= threshold:
            print(f"检测到状态: {best_match}")
            return best_match
        else:
            print(f"未检测到状态，最佳匹配分数: {best_score:.3f}")
            return None

    def handle_state(self, state: int):
        """根据状态执行操作，严格按照1->2->3->4->5的顺序"""
        current_time = time.time()

        # 更新当前检测到的状态
        self.current_state = state

        # 只处理预期的状态
        if state == self.expected_state:
            print(f"执行状态 {state}")

            if state == 1:
                # 图1：左键点击放下鱼钩
                print("  状态1: 空竿 - 放下鱼钩")
                self.click_left()
                self.expected_state = 2  # 下一个预期状态

            elif state == 2:
                # 图2：等待（过渡状态）
                print("  状态2: 正在钓鱼 - 等待...")
                self.expected_state = 3  # 下一个预期状态

            elif state == 3:
                # 图3：白色点出现后，左键点击
                print("  状态3: 鱼上钩 - 收杆！")
                self.click_left()
                self.expected_state = 4  # 下一个预期状态

            elif state == 4:
                # 图4：控制白色条保持中间
                print("  状态4: 正在收线 - 保持平衡")
                self.state_start_time = current_time
                self.expected_state = 5  # 下一个预期状态

            elif state == 5:
                # 图5：等待1秒后左键点击，循环
                print("  状态5: 鱼钓上 - 等待1秒...")
                time.sleep(1)
                self.click_left()
                print("  循环开始...")
                self.expected_state = 1  # 循环回状态1

        elif state == 4 and self.expected_state == 4:
            # 状态4需要持续操作
            if current_time - self.state_start_time > 0.5:
                self.click_left()
                self.state_start_time = current_time

        else:
            # 检测到其他状态，忽略，等待预期状态
            print(f"  等待状态 {self.expected_state}，当前状态: {state}")

    def click_left(self):
        """点击鼠标左键"""
        try:
            # 如果有窗口 ID，先激活窗口
            if hasattr(self, 'window_id') and self.window_id:
                # 激活窗口
                subprocess.run(['xdotool', 'windowactivate', str(self.window_id)], capture_output=True)
                time.sleep(0.2)

            # 按住鼠标左键一段时间（模拟长按）
            print("按下鼠标左键")
            subprocess.run(['xdotool', 'mousedown', '1'], capture_output=True)
            time.sleep(0.2)  # 按住 0.2 秒
            print("释放鼠标左键")
            subprocess.run(['xdotool', 'mouseup', '1'], capture_output=True)
            print("点击完成")
        except Exception as e:
            print(f"点击出错: {e}")


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
    print("VRChat 自动钓鱼器")
    print("=" * 50)

    # 创建自动钓鱼机器人
    fish_bot = FishAutoBot("img")

    # 创建捕获器实例（每 10 帧更新一次窗口位置）
    capturer = X11WindowCapture("VRChat", update_interval=10)

    # 查找窗口
    if not capturer.find_window():
        print("\n提示:")
        print("1. 确保 VRChat 正在运行")
        print("2. 检查窗口名称是否为 'VRChat'")
        print("3. 可以尝试修改 window_name 参数匹配实际窗口名称")
        print("\n安装必要的工具:")
        print("sudo apt install x11-utils xdotool")
        print("pip install mss opencv-python")
        return

    # 设置窗口位置信息给钓鱼机器人
    if capturer.window_rect:
        fish_bot.set_window_rect(capturer.window_rect)
        print(f"窗口位置: {capturer.window_rect}")

    # 设置窗口 ID 给钓鱼机器人
    if capturer.window_id:
        fish_bot.set_window_id(capturer.window_id)
        print(f"窗口 ID: {hex(capturer.window_id)}")

    print("\n开始自动钓鱼...")

    try:
        while True:
            # 捕获窗口
            frame = capturer.capture()

            if frame is not None:
                # 检测当前状态
                state = fish_bot.detect_state(frame)

                if state:
                    # 处理状态
                    fish_bot.handle_state(state)

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