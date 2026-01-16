import sys
import random
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QMenu, 
                             QSystemTrayIcon, QInputDialog, QLineEdit,
                             QVBoxLayout, QPushButton, QHBoxLayout,
                             QDialog, QTextEdit, QScrollArea, QMessageBox, QComboBox)
from PyQt6.QtCore import (Qt, QTimer, QPoint, QRect, QSize, QThread, pyqtSignal, QPropertyAnimation)
from PyQt6.QtGui import (QPixmap, QPainter, QAction, QIcon, QMouseEvent, 
                         QColor, QFont, QPen, QFontMetrics)
import requests

# -----------------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------------
SPRITE_WIDTH = 32
SPRITE_HEIGHT = 32
WINDOW_WIDTH = 120
WINDOW_HEIGHT = 160 # 包含气泡的空间
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"

# -----------------------------------------------------------------------------
# AI 对话线程
# -----------------------------------------------------------------------------
class AIWorker(QThread):
    """异步处理 AI 请求的线程"""
    finished = pyqtSignal(str)

    def __init__(self, api_url, api_key, model, prompt, messages):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.messages = messages

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建对话内容
            full_messages = [{"role": "system", "content": self.prompt}] + self.messages
            
            payload = {
                "model": self.model,
                "messages": full_messages,
                "stream": False
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                self.finished.emit(content)
            else:
                try:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                except:
                    error_msg = response.text
                self.finished.emit(f"API错误({response.status_code}): {error_msg[:50]}...")
        except Exception as e:
            self.finished.emit(f"网络异常: {str(e)[:50]}...")

# -----------------------------------------------------------------------------
# 历史对话查看器
# -----------------------------------------------------------------------------
class HistoryDialog(QDialog):
    """显示完整历史对话的窗口"""
    def __init__(self, parent=None, history=None, pet_name="桌宠"):
        super().__init__(parent)
        self.setWindowTitle(f"与 {pet_name} 的对话记录")
        self.resize(400, 500)
        
        layout = QVBoxLayout()
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        
        # 格式化历史记录
        content = ""
        for msg in history or []:
            role = "我" if msg["role"] == "user" else pet_name
            content += f"【{role}】: {msg['content']}\n\n"
            
        self.text_area.setPlainText(content)
        # 滚动到底部
        self.text_area.moveCursor(self.text_area.textCursor().MoveOperation.End)
        
        layout.addWidget(self.text_area)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

# -----------------------------------------------------------------------------
# 配置对话框
# -----------------------------------------------------------------------------
from PyQt6.QtWidgets import QComboBox, QMessageBox

class ConfigDialog(QDialog):
    """配置 AI API 和 Prompt 的对话框"""
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("AI 桌宠配置")
        self.setFixedSize(450, 400)
        self.config = config or {}
        
        layout = QVBoxLayout()
        
        # API URL
        layout.addWidget(QLabel("API Endpoint (OpenAI 兼容):"))
        self.api_url_input = QLineEdit(self.config.get("api_url", ""))
        self.api_url_input.setPlaceholderText("https://api.openai.com/v1/chat/completions")
        layout.addWidget(self.api_url_input)
        
        # API Key
        layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_key_input)
        
        # Model Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型选择:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        # 初始加载已有模型
        saved_model = self.config.get("model", "gpt-3.5-turbo")
        self.model_combo.addItem(saved_model)
        self.model_combo.setCurrentText(saved_model)
        
        fetch_btn = QPushButton("拉取模型列表")
        fetch_btn.clicked.connect(self.fetch_models)
        
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(fetch_btn)
        layout.addLayout(model_layout)
        
        # Prompt
        layout.addWidget(QLabel("角色提示词 (System Prompt):"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlainText(self.config.get("prompt", "你是一个可爱的桌宠。"))
        layout.addWidget(self.prompt_input)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def fetch_models(self):
        """尝试从 API 获取模型列表"""
        api_url = self.api_url_input.text().strip()
        api_key = self.api_key_input.text().strip()
        
        if not api_url or not api_key:
            QMessageBox.warning(self, "错误", "请先填写 API URL 和 Key")
            return
            
        try:
            # 更加健壮的 URL 转换逻辑
            # 标准: https://api.xxx.com/v1/chat/completions -> https://api.xxx.com/v1/models
            if "/chat/completions" in api_url:
                models_url = api_url.split("/chat/completions")[0] + "/models"
            elif "/v1" in api_url:
                models_url = api_url.split("/v1")[0] + "/v1/models"
            else:
                # 去掉末尾斜杠
                base_url = api_url.rstrip("/")
                models_url = f"{base_url}/models"
                
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(models_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # 兼容不同厂商的返回格式 (有些是 list, 有些是 object 里的 data 列表)
                if isinstance(data, list):
                    models_data = data
                else:
                    models_data = data.get("data", [])
                    
                models = [m["id"] for m in models_data if isinstance(m, dict) and "id" in m]
                
                if models:
                    self.model_combo.clear()
                    self.model_combo.addItems(sorted(models))
                    QMessageBox.information(self, "成功", f"成功获取 {len(models)} 个模型")
                else:
                    QMessageBox.warning(self, "提示", "获取到数据，但未找到模型 ID 列表")
            else:
                try:
                    err_info = response.json().get("error", {}).get("message", response.text)
                except:
                    err_info = response.text
                QMessageBox.warning(self, "错误", f"请求失败 ({response.status_code}):\n{err_info[:200]}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接异常: {str(e)}")

    def get_config(self):
        """获取配置并自动修正可能错误的 Chat URL"""
        url = self.api_url_input.text().strip()
        
        # 自动补全/修正逻辑
        if url:
            # 如果结尾是 /models，替换为 /chat/completions
            if url.endswith("/models"):
                url = url.replace("/models", "/chat/completions")
            # 如果不含 /chat/completions，尝试智能拼接
            elif "/chat/completions" not in url:
                if not url.endswith("/"):
                    url += "/"
                if "v1" in url and not url.endswith("v1/"):
                    # 处理 https://api.xxx.com/v1 这种情况
                    pass 
                
                # 如果是基础 API 路径，通常需要加上 v1/chat/completions 或 chat/completions
                if not url.endswith("chat/completions"):
                    # 检查是否已经有 v1
                    if "v1/" in url:
                        url += "chat/completions"
                    else:
                        url += "v1/chat/completions"

        return {
            "api_url": url,
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_combo.currentText(),
            "prompt": self.prompt_input.toPlainText()
        }

# -----------------------------------------------------------------------------
# 主窗口：小桌宠
# -----------------------------------------------------------------------------
class DesktopPet(QWidget):
    """AI 小桌宠主类"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()
        self.init_tray()
        
        # 计时器：动画更新
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(200) # 每 200ms 更新一帧
        
        # 计时器：随机漫步逻辑
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.random_move_logic)
        self.move_timer.start(100)
        
        # 状态
        self.is_walking = True
        self.current_direction = 0 # 0:前, 1:左, 2:右, 3:后
        self.anim_frame = 1 # 0, 1, 2
        self.move_step = 2
        self.target_pos = None
        self.is_dragging = False
        self.drag_pos = QPoint()
        self.drag_start_pos = QPoint()
        
        # 对话状态
        self.is_thinking = False
        self.bubble_text = ""
        self.scroll_offset = 0 # 文字滚动偏移
        self.chat_history = self.load_history()

    def init_ui(self):
        """初始化窗口属性"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # 加载素材
        sprite_path = os.path.join(os.getcwd(), "assets", "sprite.png")
        if not os.path.exists(sprite_path):
            print(f"Error: Sprite not found at {sprite_path}")
            sys.exit(1)
            
        self.full_sprite = QPixmap(sprite_path)
        
        # 初始位置：屏幕中心
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2, screen.height() // 2)
        
        # 控制布局容器 (底部)
        self.bottom_widget = QWidget(self)
        self.bottom_widget.setGeometry(5, WINDOW_HEIGHT - 35, WINDOW_WIDTH - 10, 30)
        bottom_layout = QHBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)
        
        # 历史按钮 (时钟小图标)
        self.hist_btn = QPushButton("🕒")
        self.hist_btn.setFixedSize(25, 25)
        self.hist_btn.setToolTip("查看历史对话")
        self.hist_btn.setStyleSheet("background: white; border-radius: 5px; font-size: 14px;")
        self.hist_btn.clicked.connect(self.show_history_dialog)
        
        # 对话输入框
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("聊聊...")
        self.input_box.setFixedHeight(25)
        self.input_box.returnPressed.connect(self.send_message)
        
        bottom_layout.addWidget(self.hist_btn)
        bottom_layout.addWidget(self.input_box)
        self.bottom_widget.hide()

    def init_data(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "api_url": "",
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "pet_name": "",
                "prompt": "你的名字是{char}，是一个文静害羞的史莱姆娘。请保证你的对话口语化简洁化。"
            }
        
        # 如果没有名字，提示取名
        if not self.config.get("pet_name"):
            name, ok = QInputDialog.getText(self, "取名时刻", "给你的小家伙取个名字吧：")
            if ok and name.strip():
                self.config["pet_name"] = name.strip()
            else:
                self.config["pet_name"] = "萌萌"
            self.save_config()

    def init_tray(self):
        """初始化系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        # 制作一个简单的托盘图标（或者用 sprite 的第一帧）
        self.tray_icon.setIcon(QIcon(self.get_frame_pixmap(0, 1)))
        
        menu = QMenu()
        
        rename_action = QAction("修改昵称", self)
        rename_action.triggered.connect(self.rename_pet)
        
        config_action = QAction("配置 AI", self)
        config_action.triggered.connect(self.show_config_dialog)
        
        clear_history_action = QAction("清除对话历史", self)
        clear_history_action.triggered.connect(self.clear_history)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        menu.addAction(rename_action)
        menu.addAction(config_action)
        menu.addAction(clear_history_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def get_frame_pixmap(self, row, col):
        """从精灵图中提取特定帧并放大"""
        # copy 参数: x, y, width, height
        frame = self.full_sprite.copy(col * SPRITE_WIDTH, row * SPRITE_HEIGHT, 
                                     SPRITE_WIDTH, SPRITE_HEIGHT)
        # 放大显示（例如放大到 64x64）
        return frame.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)

    def paintEvent(self, event):
        """绘制桌宠和对话气泡"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 中心位置计算
        sprite_x = (WINDOW_WIDTH - 64) // 2
        sprite_y = 60 # 留出顶部气泡空间
        
        # 1. 绘制对话气泡
        if self.bubble_text or self.is_thinking:
            display_text = "..." if self.is_thinking else self.bubble_text
            
            # 画气泡背景
            rect = QRect(5, 5, WINDOW_WIDTH - 10, 50)
            painter.setBrush(QColor(255, 255, 255, 220))
            painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
            painter.drawRoundedRect(rect, 10, 10)
            
            # 使用带偏移的文字绘制逻辑（实现垂直滚动）
            painter.setPen(Qt.GlobalColor.black)
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            
            # 剪裁区域，防止文字超出气泡
            painter.setClipRect(rect.adjusted(5, 5, -5, -5))
            
            # 计算文字总高度，如果太长则滚动
            text_rect = painter.boundingRect(rect.adjusted(5, 5, -5, -5), 
                                           Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, 
                                           display_text)
            
            if text_rect.height() > 40 and not self.is_thinking:
                # 文字过长，增加动画偏移
                draw_rect = rect.adjusted(5, 5 - self.scroll_offset, -5, 500)
                painter.drawText(draw_rect, Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, display_text)
            else:
                painter.drawText(rect.adjusted(5, 5, -5, -5), 
                                 Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                                 display_text)
            painter.setClipping(False)

        # 2. 绘制桌宠
        current_pixmap = self.get_frame_pixmap(self.current_direction, self.anim_frame)
        painter.drawPixmap(sprite_x, sprite_y, current_pixmap)
        
        # 3. 如果点击了且弹出 "?"
        if self.input_box.isVisible() and not self.bubble_text and not self.is_thinking:
            painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            painter.setPen(Qt.GlobalColor.red)
            painter.drawText(sprite_x + 20, sprite_y - 10, "?")

    def update_animation(self):
        """更新动画帧和文字滚动"""
        if self.is_walking:
            self.anim_frame = (self.anim_frame + 1) % 3
        else:
            self.anim_frame = 1
            
        # 气泡文字滚动逻辑
        if self.bubble_text and not self.is_thinking:
            # 计算文字总高度，确定是否需要继续滚动
            font = QFont("Microsoft YaHei", 9)
            metrics = QFontMetrics(font)
            # 这里的宽度要和 paintEvent 里的 rect 减去边距一致 (120 - 10 - 10 = 100)
            rect = metrics.boundingRect(0, 0, WINDOW_WIDTH - 20, 1000, 
                                      Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, 
                                      self.bubble_text)
            text_height = rect.height()
            max_scroll = max(0, text_height - 40) # 40 是显示区域高度
            
            if max_scroll > 0:
                if self.scroll_offset < max_scroll:
                    self.scroll_offset += 1 # 稍微减慢滚动速度更易读
                elif not hasattr(self, "bubble_timer_started") or not self.bubble_timer_started:
                    # 滚到底了，开启 5 秒倒计时准备关闭
                    self.bubble_timer_started = True
                    QTimer.singleShot(5000, self.clear_bubble)
            else:
                # 文字很短不需要滚动，直接由 on_ai_finished 的初始定时器处理，
                # 或者如果还没有定时器，这里也加一个保护
                if not hasattr(self, "bubble_timer_started") or not self.bubble_timer_started:
                    self.bubble_timer_started = True
                    QTimer.singleShot(5000, self.clear_bubble)
                
        self.update()

    def random_move_logic(self):
        """随机漫步逻辑"""
        if self.is_dragging or self.input_box.isVisible() or self.is_thinking:
            self.is_walking = False
            return

        # 如果没有目标位置，随机产生一个
        if self.target_pos is None:
            # 20% 概率开始移动
            if random.random() < 0.05:
                screen = QApplication.primaryScreen().geometry()
                tx = random.randint(0, screen.width() - WINDOW_WIDTH)
                ty = random.randint(0, screen.height() - WINDOW_HEIGHT)
                self.target_pos = QPoint(tx, ty)
                self.is_walking = True
                
                # 决定方向
                dx = tx - self.x()
                dy = ty - self.y()
                if abs(dx) > abs(dy):
                    self.current_direction = 2 if dx > 0 else 1
                else:
                    self.current_direction = 0 if dy > 0 else 3
            else:
                self.is_walking = False
                return

        # 移动向目标
        curr = self.pos()
        dx = self.target_pos.x() - curr.x()
        dy = self.target_pos.y() - curr.y()
        dist = (dx**2 + dy**2)**0.5
        
        if dist < self.move_step:
            self.move(self.target_pos)
            self.target_pos = None
            self.is_walking = False
        else:
            vx = int(self.move_step * dx / dist)
            vy = int(self.move_step * dy / dist)
            self.move(curr.x() + vx, curr.y() + vy)

    # --- 鼠标事件 ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            # 记录按下时的全局坐标和窗口内偏置
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if Qt.MouseButton.LeftButton and self.is_dragging:
            # 更新窗口位置
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            # 拖拽时重置漫步目标，防止松开瞬间发生逻辑跳变
            self.target_pos = None
            self.is_walking = False
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # 计算移动距离，如果移动距离很小则视为“点击”
            release_pos = event.globalPosition().toPoint()
            distance = (release_pos - self.drag_start_pos).manhattanLength()
            
            self.is_dragging = False
            
            if distance < 5:  # 阈值 5 像素，视为点击
                self.toggle_input()
            else:
                # 拖拽结束，清空目标，等待下一轮漫步逻辑选取新目标
                self.target_pos = None
                self.is_walking = False
            event.accept()

    def toggle_input(self):
        """显示/隐藏输入框，并让桌宠看向屏幕"""
        if self.bottom_widget.isVisible():
            self.bottom_widget.hide()
            self.bubble_text = ""
        else:
            self.bubble_text = ""
            self.bottom_widget.show()
            self.input_box.setFocus()
            
            # --- 新增功能：立刻切换为向前站立 ---
            self.is_walking = False
            self.current_direction = 0  
            self.anim_frame = 1         
            self.target_pos = None      
            
        self.update()

    def send_message(self):
        """发送消息给 AI"""
        text = self.input_box.text().strip()
        if not text:
            return
            
        if not self.config.get("api_key") or not self.config.get("api_url"):
            self.bubble_text = "请先在托盘设置 API！"
            self.bottom_widget.hide()
            self.update()
            return

        self.input_box.clear()
        self.bottom_widget.hide()
        self.is_thinking = True
        self.bubble_text = ""
        self.scroll_offset = 0
        self.bubble_timer_started = False # 重置定时器状态
        self.update()
        
        # 添加到历史
        self.chat_history.append({"role": "user", "content": text})
        
        # 准备 Prompt（替换 {char} 占位符）
        raw_prompt = self.config.get("prompt", "你是一个可爱的桌宠。")
        pet_name = self.config.get("pet_name", "桌宠")
        final_prompt = raw_prompt.replace("{char}", pet_name)

        # 启动线程
        self.worker = AIWorker(self.config["api_url"], 
                               self.config["api_key"], 
                               self.config.get("model", "gpt-3.5-turbo"),
                               final_prompt, 
                               self.chat_history[-10:]) # 取最近 10 条
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.start()

    def on_ai_finished(self, response):
        """AI 处理完成"""
        self.is_thinking = False
        self.bubble_text = response
        self.scroll_offset = 0
        self.bubble_timer_started = False
        self.chat_history.append({"role": "assistant", "content": response})
        self.save_history()
        self.update()
        
        # 定时器会在 update_animation 中根据是否滚动完来智能触发

    def clear_bubble(self):
        if not self.is_thinking:
            self.bubble_text = ""
            self.scroll_offset = 0
            self.bubble_timer_started = False
            self.update()

    # --- 配置与历史 ---
    def rename_pet(self):
        """修改桌宠昵称"""
        old_name = self.config.get("pet_name", "萌萌")
        name, ok = QInputDialog.getText(self, "修改昵称", "输入新的名字：", text=old_name)
        if ok and name.strip():
            self.config["pet_name"] = name.strip()
            self.save_config()
            self.bubble_text = f"以后我就叫 {name.strip()} 啦！"
            self.update()
            QTimer.singleShot(3000, self.clear_bubble)

    def show_history_dialog(self):
        """弹出历史对话窗口"""
        dialog = HistoryDialog(self, self.chat_history, self.config.get("pet_name", "桌宠"))
        dialog.exec()

    def show_config_dialog(self):
        dialog = ConfigDialog(self, self.config)
        if dialog.exec():
            self.config = dialog.get_config()
            self.save_config()

    def save_config(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.chat_history[-50:], f, indent=4) # 保留最后 50 条

    def clear_history(self):
        self.chat_history = []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        self.bubble_text = "历史已清除"
        self.update()
        QTimer.singleShot(2000, self.clear_bubble)

# -----------------------------------------------------------------------------
# 程序入口
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 确保 assets 目录存在
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
