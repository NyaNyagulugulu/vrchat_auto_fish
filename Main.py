import cv2
import numpy as np
import subprocess
import re
import time
import mss
import os
from typing import Optional, Tuple


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.5) -> np.ndarray:
    """应用伽马校正增强对比度"""
    # 构建查找表
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                     for i in np.arange(0, 256)]).astype("uint8")

    # 应用查找表
    return cv2.LUT(image, table)


def to_grayscale_with_gamma(image: np.ndarray, gamma: float = 1.5) -> np.ndarray:
    """转换为灰度并应用伽马校正"""
    # 转换为灰度
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 应用伽马校正
    return apply_gamma_correction(gray, gamma)


class KalmanFilter:
    """卡尔曼滤波器，用于平滑跟踪"""

    def __init__(self):
        self.kalman = cv2.KalmanFilter(4, 2)
        # 状态向量: [x, y, vx, vy]
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0],
                                                  [0, 1, 0, 0]], np.float32)
        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0],
                                                [0, 1, 0, 1],
                                                [0, 0, 1, 0],
                                                [0, 0, 0, 1]], np.float32)
        self.kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.1
        self.kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.1
        self.kalman.errorCovPost = np.eye(4, dtype=np.float32) * 1

    def predict(self):
        """预测下一帧位置"""
        return self.kalman.predict()

    def update(self, measurement):
        """更新滤波器"""
        self.kalman.correct(measurement)

    def get_position(self):
        """获取当前位置 - 返回 (x, y) 元组"""
        pos = self.kalman.statePost[:2]
        return (int(pos[0, 0]), int(pos[1, 0]))


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

        # 卡尔曼滤波器
        self.bar_kalman = KalmanFilter()  # 白色条跟踪
        self.fish_kalman = KalmanFilter()  # 小鱼跟踪
        self.kalman_initialized = False

        # 小鱼模板
        self.fish_templates = []
        
        # 白色条模板
        self.bar_templates = []

        # 加载模板
        self.load_templates()
        self.load_fish_templates()
        self.load_bar_templates()

    def set_window_rect(self, rect: Tuple[int, int, int, int]):
        """设置窗口位置信息"""
        self.window_rect = rect

    def set_window_id(self, window_id: int):
        """设置窗口 ID"""
        self.window_id = window_id

    def load_templates(self):
        """加载模板图片 - 应用灰度和伽马校正"""
        for state_dir in range(1, 6):  # 1-5
            state_path = os.path.join(self.img_dir, str(state_dir))
            if os.path.isdir(state_path):
                self.templates[state_dir] = []
                # 加载该目录下的所有图片
                for filename in os.listdir(state_path):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        filepath = os.path.join(state_path, filename)
                        # 读取彩色图片
                        template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                        if template is not None:
                            # 转换为灰度并应用伽马校正
                            template_gray = to_grayscale_with_gamma(template, gamma=1.5)
                            self.templates[state_dir].append(template_gray)
                            print(f"加载模板: 状态{state_dir}/{filename} (灰度+伽马)")
                print(f"状态{state_dir} 共加载 {len(self.templates[state_dir])} 个模板")
            else:
                print(f"警告: 找不到状态目录 {state_path}")

    def load_fish_templates(self):
        """加载小鱼模板图片 - 使用边缘检测提取轮廓特征"""
        fish_img_dir = os.path.join(self.img_dir, "fish_img")
        if os.path.isdir(fish_img_dir):
            # 加载该目录下的所有图片
            for filename in os.listdir(fish_img_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(fish_img_dir, filename)
                    # 读取彩色图片
                    template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                    if template is not None:
                        # 转换为灰度并应用伽马校正
                        template_gray = to_grayscale_with_gamma(template, gamma=1.5)
                        # 使用Canny边缘检测提取轮廓（突出鱼的黑色轮廓）
                        template_edges = cv2.Canny(template_gray, 50, 150)
                        self.fish_templates.append(template_edges)
                        print(f"加载小鱼模板: {filename} (边缘检测)")
            print(f"小鱼模板共加载 {len(self.fish_templates)} 个")
        else:
            print(f"警告: 找不到小鱼模板目录 {fish_img_dir}")

    def load_bar_templates(self):
        """加载白色条模板图片 - 使用灰度和伽马校正"""
        bar_img_dir = os.path.join(self.img_dir, "bar")
        if os.path.isdir(bar_img_dir):
            # 加载该目录下的所有图片
            for filename in os.listdir(bar_img_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(bar_img_dir, filename)
                    # 读取彩色图片
                    template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                    if template is not None:
                        # 转换为灰度并应用伽马校正
                        template_gray = to_grayscale_with_gamma(template, gamma=1.5)
                        self.bar_templates.append(template_gray)
                        print(f"加载白色条模板: {filename} (灰度+伽马)")
            print(f"白色条模板共加载 {len(self.bar_templates)} 个")
        else:
            print(f"警告: 找不到白色条模板目录 {bar_img_dir}")

    def detect_state(self, frame: np.ndarray) -> Optional[int]:
        """检测当前状态 - 使用灰度+伽马校正的模板匹配"""
        # 转换为灰度并应用伽马校正
        frame_gray = to_grayscale_with_gamma(frame, gamma=1.5)

        best_match = None
        best_score = 0
        threshold = 0.4  # 提高阈值，减少误检测
        state_scores = {}

        frame_height, frame_width = frame_gray.shape[:2]

        for state, templates in self.templates.items():
            if not templates:
                continue

            # 对该状态的所有模板进行匹配
            state_scores_list = []
            for template in templates:
                template_height, template_width = template.shape[:2]

                # 跳过大于图像的模板
                if template_height > frame_height or template_width > frame_width:
                    continue

                # 检查是否是小模板（小于窗口的70%）
                is_small_template = (template_height < frame_height * 0.7 and 
                                    template_width < frame_width * 0.7)

                if is_small_template:
                    # 小模板：在整个窗口中搜索
                    result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    # 检查最佳匹配位置是否合理（不在边缘）
                    x, y = max_loc
                    margin = 10
                    if (x > margin and x < frame_width - template_width - margin and
                        y > margin and y < frame_height - template_height - margin):
                        state_scores_list.append(max_val)
                else:
                    # 大模板：直接匹配
                    result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    state_scores_list.append(max_val)

            if not state_scores_list:
                continue

            # 使用平均值和最大值的加权和
            avg_score = sum(state_scores_list) / len(state_scores_list)
            max_score = max(state_scores_list)
            weighted_score = (avg_score * 0.5 + max_score * 0.5)  # 平衡权重

            state_scores[state] = weighted_score

            # 更新全局最佳匹配
            if weighted_score > best_score:
                best_score = weighted_score
                best_match = state

        # 显示所有状态的匹配分数
        scores_str = ", ".join([f"状态{k}:{v:.3f}" for k, v in sorted(state_scores.items())])
        print(f"模板匹配: {scores_str}")

        if best_score >= threshold:
            print(f"检测到状态: {best_match}")
            return best_match
        else:
            print(f"未检测到状态，最佳匹配分数: {best_score:.3f}")
            return None

    def handle_state(self, state: int, frame: np.ndarray):
        """根据状态执行操作，严格按照1->2->3的顺序"""
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
                # 图2：白色点出现后，左键点击（上钩）
                print("  状态2: 鱼上钩 - 收杆！")
                self.click_left()
                self.expected_state = 3  # 下一个预期状态

            elif state == 3:
                # 图3：控制白色条保持在小鱼图片内
                print("  状态3: 正在收线 - 控制白条位置")
                self.state_start_time = current_time
                self.expected_state = 1  # 循环回状态1

        elif state == 3 and self.expected_state == 3:
            # 状态3需要持续控制白色条位置 - 智能控制
            if current_time - self.state_start_time > 0.05:  # 更快的响应速度
                # 检测白色条和小鱼位置
                bar_pos = self.detect_white_bar(frame)
                fish_pos = self.detect_fish(frame)

                if bar_pos and fish_pos:
                    # 获取小鱼和白色条的垂直位置
                    fish_center_y = fish_pos[1] + fish_pos[3] // 2
                    bar_center_y = bar_pos[1] + bar_pos[3] // 2

                    # 计算垂直距离
                    distance = fish_center_y - bar_center_y

                    print(f"  小鱼相对位置: {distance}px")

                    # 根据相对位置决定操作
                    if distance < -10:  # 小鱼在白色条上方10像素以上
                        # 按住鼠标让小鱼下降
                        print("  小鱼在上方 - 按住")
                        subprocess.run(['xdotool', 'mousedown', '1'], capture_output=True)
                    elif distance > 10:  # 小鱼在白色条下方10像素以上
                        # 松开鼠标让小鱼上升
                        print("  小鱼在下方 - 松开")
                        subprocess.run(['xdotool', 'mouseup', '1'], capture_output=True)
                    else:  # 小鱼在白色条附近
                        # 保持当前状态
                        print("  小鱼在范围内 - 保持")

                    # 自动截图学习（降低频率，避免太多截图）
                    if int(current_time) % 2 == 0:  # 每2秒截图一次
                        self.auto_capture(frame, 3)
                else:
                    # 无法检测到目标，使用默认策略
                    print("  无法检测目标 - 使用默认策略")
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

    def detect_white_bar(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """检测白色条的位置 - 使用模板匹配 + 严格的白色过滤"""
        try:
            if not self.bar_templates:
                print("  未加载白色条模板，使用边缘检测")
                return self._detect_white_bar_by_edges(frame)

            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 宽松的白色范围（检测更多白色区域）
            # H: 0-180 (白色没有色相限制)
            # S: 0-60 (饱和度范围放宽)
            # V: 180-255 (亮度范围放宽)
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 60, 255])

            # 创建白色掩码
            white_mask = cv2.inRange(hsv, lower_white, upper_white)

            # 对掩码进行形态学操作，去除小噪点
            kernel = np.ones((3, 3), np.uint8)
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)

            # 将掩码应用到原始图像，只保留白色区域
            frame_white = cv2.bitwise_and(frame, frame, mask=white_mask)

            # 转换为灰度并应用伽马校正
            frame_gray = to_grayscale_with_gamma(frame_white, gamma=1.5)

            # 对每个白色条模板进行匹配
            best_match = None
            best_score = 0
            threshold = 0.3  # 降低阈值，更容易检测到白色条
            frame_height, frame_width = frame_gray.shape[:2]

            for template in self.bar_templates:
                template_height, template_width = template.shape[:2]

                # 跳过大于图像的模板
                if template_height > frame_height or template_width > frame_width:
                    continue

                # 使用模板匹配
                result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                # 检查最佳匹配位置是否合理（不在边缘）
                x, y = max_loc
                margin = 10
                if (x > margin and x < frame_width - template_width - margin and
                    y > margin and y < frame_height - template_height - margin):
                    if max_val > best_score:
                        best_score = max_val
                        best_match = (x, y, template_width, template_height)

            if best_match and best_score >= threshold:
                x, y, w, h = best_match
                
                # 验证：检查该区域是否真的是白色
                roi = hsv[y:y+h, x:x+w]
                # 计算ROI中白色像素的比例
                white_ratio = np.sum(white_mask[y:y+h, x:x+w] > 0) / (w * h)
                
                # 只有当白色像素比例超过60%时才认为是白色条（降低要求）
                if white_ratio < 0.6:
                    print(f"  [验证失败] 白色像素比例: {white_ratio:.2%} < 60%")
                    return None
                
                # 使用卡尔曼滤波平滑位置
                center_x = x + w // 2
                center_y = y + h // 2
                measurement = np.array([[center_x], [center_y]], dtype=np.float32)

                if not self.kalman_initialized:
                    # 初始化卡尔曼滤波器
                    self.bar_kalman.kalman.statePost = np.array([[center_x], [center_y], [0], [0]], dtype=np.float32)
                    self.kalman_initialized = True
                else:
                    # 更新卡尔曼滤波器
                    self.bar_kalman.predict()
                    self.bar_kalman.update(measurement)

                # 获取滤波后的位置
                filtered_x, filtered_y = self.bar_kalman.get_position()
                filtered_x = int(filtered_x - w // 2)
                filtered_y = int(filtered_y - h // 2)

                print(f"  检测到白色条（模板匹配+白色验证）: x={filtered_x}, y={filtered_y}, w={w}, h={h}, 分数={best_score:.3f}, 白色比例={white_ratio:.2%}")
                return (filtered_x, filtered_y, w, h)

            print(f"  未检测到白色条（模板匹配），最佳匹配分数: {best_score:.3f}")
            return None
        except Exception as e:
            print(f"检测白色条出错: {e}")
            return None

    def _detect_white_bar_by_edges(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """备用方法：使用边缘检测白色条 + 严格的白色过滤"""
        try:
            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 宽松的白色范围
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 60, 255])

            # 创建白色掩码
            white_mask = cv2.inRange(hsv, lower_white, upper_white)

            # 对掩码进行形态学操作，去除小噪点
            kernel = np.ones((3, 3), np.uint8)
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)

            # 搜索整个屏幕（放宽搜索区域）
            frame_height = frame.shape[0]
            search_region_y_start = int(frame_height * 0.1)  # 从10%高度开始
            search_region_y_end = int(frame_height * 0.7)    # 到70%高度结束
            search_region = white_mask[search_region_y_start:search_region_y_end, :]

            # 查找轮廓
            contours, _ = cv2.findContours(search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 找到最大的白色区域（白色条）
            if contours:
                # 筛选符合条件的轮廓
                valid_contours = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    # 调整y坐标到原始图像
                    y = y + search_region_y_start
                    
                    # 检查轮廓的宽高比
                    # 竖直白色条：高度 > 宽度
                    if h > w * 2:  # 高度至少是宽度的2倍
                        # 限制宽度范围（钓鱼白色条通常很窄）
                        if 5 < w < 30:  # 宽度在5-30像素之间
                            # 限制高度范围
                            if 50 < h < 200:  # 高度在50-200像素之间
                                # 检查该区域的白色像素比例
                                roi = hsv[y:y+h, x:x+w]
                                white_ratio = np.sum(white_mask[y:y+h, x:x+w] > 0) / (w * h)
                                
                                # 只有当白色像素比例超过65%时才认为是白色条（降低要求）
                                if white_ratio > 0.65:
                                    valid_contours.append((contour, (x, y, w, h), white_ratio))

                if valid_contours:
                    # 选择白色像素比例最高的
                    largest_contour, (x, y, w, h), white_ratio = max(valid_contours, key=lambda c: c[2])

                    # 使用卡尔曼滤波平滑位置
                    center_x = x + w // 2
                    center_y = y + h // 2
                    measurement = np.array([[center_x], [center_y]], dtype=np.float32)

                    if not self.kalman_initialized:
                        # 初始化卡尔曼滤波器
                        self.bar_kalman.kalman.statePost = np.array([[center_x], [center_y], [0], [0]], dtype=np.float32)
                        self.kalman_initialized = True
                    else:
                        # 更新卡尔曼滤波器
                        self.bar_kalman.predict()
                        self.bar_kalman.update(measurement)

                    # 获取滤波后的位置
                    filtered_x, filtered_y = self.bar_kalman.get_position()
                    filtered_x = int(filtered_x - w // 2)
                    filtered_y = int(filtered_y - h // 2)

                    print(f"  检测到白色条（边缘检测+白色验证）: x={filtered_x}, y={filtered_y}, w={w}, h={h}, 白色比例={white_ratio:.2%}")
                    return (filtered_x, filtered_y, w, h)

            print("  未检测到白色条（边缘检测）")
            return None
        except Exception as e:
            print(f"检测白色条出错: {e}")
            return None

    def detect_fish(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """检测小鱼的位置 - 使用边缘检测和轮廓匹配"""
        try:
            if not self.fish_templates:
                print("  未加载小鱼模板，无法检测")
                return None

            # 转换为灰度并应用伽马校正
            frame_gray = to_grayscale_with_gamma(frame, gamma=1.5)

            # 使用Canny边缘检测提取轮廓（突出鱼的黑色轮廓）
            edges = cv2.Canny(frame_gray, 50, 150)

            frame_height, frame_width = edges.shape[:2]

            # 限制搜索区域：只在白色条附近搜索（避免云上、地上误检）
            # 如果有白色条位置，限制搜索区域
            search_region = edges
            search_offset_y = 0

            if hasattr(self, 'bar_kalman') and self.kalman_initialized:
                # 获取白色条的位置
                bar_pos = self.bar_kalman.get_position()
                bar_y = bar_pos[1]
                # 只搜索白色条上下150像素范围内（扩大范围）
                search_y_start = max(0, bar_y - 150)
                search_y_end = min(frame_height, bar_y + 150)
                search_region = edges[search_y_start:search_y_end, :]
                search_offset_y = search_y_start
                print(f"  限制搜索区域: y={search_y_start}-{search_y_end} (白色条y={bar_y})")
            else:
                print(f"  无白色条位置，搜索全屏")

            # 对每个小鱼模板进行匹配
            best_match = None
            best_score = 0
            threshold = 0.15  # 进一步降低阈值，更容易检测到小鱼

            for template in self.fish_templates:
                # 对模板也进行边缘检测
                template_edges = cv2.Canny(template, 50, 150)

                template_height, template_width = template_edges.shape[:2]

                # 跳过大于图像的模板
                search_height, search_width = search_region.shape[:2]
                if template_height > search_height or template_width > search_width:
                    continue

                # 使用边缘图像进行模板匹配
                result = cv2.matchTemplate(search_region, template_edges, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                # 检查最佳匹配位置是否合理（不在边缘）
                x, y = max_loc
                margin = 10
                if (x > margin and x < search_width - template_width - margin and
                    y > margin and y < search_height - template_height - margin):
                    if max_val > best_score:
                        best_score = max_val
                        # 调整y坐标（加上搜索区域偏移）
                        best_match = (x, y + search_offset_y, template_width, template_height)
                        print(f"  候选匹配: x={x}, y={y+search_offset_y}, 分数={max_val:.3f}")

            if best_match and best_score >= threshold:
                x, y, w, h = best_match
                print(f"  检测到小鱼, 最佳匹配分数: {best_score:.3f}")
                return (x, y, w, h)

            print(f"  未检测到小鱼, 最佳匹配分数: {best_score:.3f}")
            return None
        except Exception as e:
            print(f"检测小鱼出错: {e}")
            return None

    def is_fish_aligned(self, fish_pos: Tuple[int, int, int, int], bar_pos: Tuple[int, int, int, int]) -> bool:
        """判断小鱼是否在白色条区域内"""
        fx, fy, fw, fh = fish_pos
        bx, by, bw, bh = bar_pos

        # 小鱼的垂直中心
        fish_center_y = fy + fh // 2

        # 白色条的垂直范围
        bar_top = by
        bar_bottom = by + bh

        # 判断小鱼是否在白色条的垂直范围内
        return bar_top <= fish_center_y <= bar_bottom

    def auto_capture(self, frame: np.ndarray, state: int):
        """自动截图并保存到对应文件夹"""
        try:
            timestamp = int(time.time() * 1000)
            filename = f"auto_{timestamp}.png"
            filepath = os.path.join(self.img_dir, str(state), filename)
            cv2.imwrite(filepath, frame)
            print(f"自动截图保存: {filepath}")
        except Exception as e:
            print(f"自动截图出错: {e}")


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

            # 检查窗口是否被隐藏或最小化
            if 'IsUnMapped' in result.stdout or 'IsViewable' not in result.stdout:
                print(f"[调试] 窗口可能被隐藏或最小化")
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

            # 添加调试信息
            if frame is None or frame.size == 0:
                print(f"[调试] 捕获的帧为空")
                return None

            # 检查是否全黑
            if np.mean(frame) < 10:
                print(f"[调试] 捕获的帧几乎全黑 (平均值: {np.mean(frame):.2f})")
                print(f"[调试] 窗口位置: x={x}, y={y}, w={width}, h={height}")

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
        print("\n数据收集命令: python collect_data.py")
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
                # 创建用于绘制的副本（彩色图）
                display_frame = frame.copy()

                # 添加测试框（右上角红色框，验证绘制功能）
                cv2.rectangle(display_frame, (display_frame.shape[1] - 60, 10), 
                             (display_frame.shape[1] - 10, 60), (0, 0, 255), 4)
                cv2.putText(display_frame, "TEST", (display_frame.shape[1] - 55, 45), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # 检测当前状态
                state = fish_bot.detect_state(frame)

                if state:
                    # 处理状态，传递 frame 用于智能检测
                    fish_bot.handle_state(state, frame)

                    # 绘制检测结果
                    # 检测小鱼
                    fish_pos = fish_bot.detect_fish(frame)
                    if fish_pos:
                        x, y, w, h = fish_pos
                        # 绘制小鱼边界框（绿色）- 加粗线条
                        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 4)
                        cv2.putText(display_frame, "FISH", (x, y - 15), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 3)
                        print(f"  [绘制] 小鱼框: x={x}, y={y}, w={w}, h={h}")
                    else:
                        # 即使未检测到也显示提示
                        cv2.putText(display_frame, "FISH: NOT FOUND", (10, 70), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        print(f"  [未绘制] 小鱼未检测到")

                    # 检测白色条
                    bar_pos = fish_bot.detect_white_bar(frame)
                    if bar_pos:
                        x, y, w, h = bar_pos
                        # 绘制白色条边界框（蓝色）- 加粗线条
                        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 4)
                        cv2.putText(display_frame, "BAR", (x, y - 15), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 3)
                        print(f"  [绘制] 白色条框: x={x}, y={y}, w={w}, h={h}")
                    else:
                        # 即使未检测到也显示提示
                        cv2.putText(display_frame, "BAR: NOT FOUND", (10, 95), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        print(f"  [未绘制] 白色条未检测到")

                    # 状态3时绘制相对位置
                    if state == 3 and fish_pos and bar_pos:
                        fish_center_y = fish_pos[1] + fish_pos[3] // 2
                        bar_center_y = bar_pos[1] + bar_pos[3] // 2
                        distance = fish_center_y - bar_center_y

                        # 绘制中心线（白色条中心）
                        cv2.line(display_frame, (bar_pos[0], bar_center_y), 
                                (bar_pos[0] + bar_pos[2], bar_center_y), (255, 0, 0), 1)
                        
                        # 绘制小鱼中心线
                        cv2.line(display_frame, (fish_pos[0], fish_center_y), 
                                (fish_pos[0] + fish_pos[2], fish_center_y), (0, 255, 0), 1)

                        # 绘制相对距离
                        mid_x = (fish_pos[0] + bar_pos[0] + bar_pos[2]) // 2
                        mid_y = (fish_center_y + bar_center_y) // 2
                        direction = "UP" if distance < -10 else "DOWN" if distance > 10 else "OK"
                        cv2.putText(display_frame, f"{direction} {distance:.1f}px", 
                                   (mid_x - 50, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                    # 绘制当前状态信息
                    cv2.putText(display_frame, f"State: {state}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    # 未检测到状态，显示提示
                    cv2.putText(display_frame, "No State Detected", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # 显示捕获的图像
                cv2.imshow('VRChat Capture', display_frame)

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