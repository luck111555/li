import sys
import serial
import serial.tools.list_ports
import datetime
import os
import re
import struct
import csv
import json
from collections import deque
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QComboBox, QPushButton, QTextBrowser,
                               QLineEdit, QLabel, QMessageBox, QCheckBox, QSpinBox,
                               QGroupBox, QSplitter, QFileDialog, QFrame, QTabWidget,
                               QScrollArea, QGridLayout, QSizePolicy, QStackedWidget)
from PySide6.QtGui import QPixmap, QIcon, QColor, QTextCursor, QTextBlockFormat
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QSize
import pyqtgraph as pg

DEFAULT_CHANNEL_COUNT = 2
CHANNEL_COUNT_OPTIONS = [2, 4, 8, 12, 16]
MAX_LOG_BLOCKS = 2000
MAX_TEXT_BUFFER_CHARS = 8192
MAX_RECORD_POINTS = 100000  # Set to 0 for unlimited recording in memory.


# --- 通道配置对话框 ---
class ChannelConfigDialog(QWidget):
    """通道配置对话框"""
    config_changed = Signal(dict)

    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("通道配置")
        self.setWindowFlags(Qt.Window)
        self.resize(600, 500)

        self.current_config = current_config or {
            'channel_count': DEFAULT_CHANNEL_COUNT,
            'channel_names': [f"Ch {i+1}" for i in range(16)],
            'channel_visible': [True] * 16,
            'channel_colors': ['#fd79a8', '#0984e3', '#00b894', '#e17055',
                               '#fdcb6e', '#6c5ce7', '#00cec9', '#ff7675',
                               '#fab1a0', '#a29bfe', '#55efc4', '#ffeaa7',
                               '#dfe6e9', '#b2bec3', '#ff6b6b', '#4ecdc4']
        }

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 通道数量选择
        count_group = QGroupBox("🔢 通道数量")
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("选择通道数量:"))

        self.count_combo = QComboBox()
        self.count_combo.addItems([f"{count}通道" for count in CHANNEL_COUNT_OPTIONS])
        current_count = self.current_config['channel_count']
        current_index = CHANNEL_COUNT_OPTIONS.index(current_count) if current_count in CHANNEL_COUNT_OPTIONS else 0
        self.count_combo.setCurrentIndex(current_index)

        self.count_combo.currentIndexChanged.connect(self.on_count_changed)
        count_layout.addWidget(self.count_combo)
        count_layout.addStretch()
        count_group.setLayout(count_layout)

        # 通道配置表格
        config_group = QGroupBox("⚙️ 通道设置")
        config_layout = QVBoxLayout()

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.grid_layout = QGridLayout(scroll_widget)

        # 表头
        headers = ["通道", "显示", "名称", "颜色"]
        for col, header in enumerate(headers):
            lbl = QLabel(f"<b>{header}</b>")
            lbl.setStyleSheet("padding: 5px; background-color: #f0f2f5;")
            lbl.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, col)

        # 创建通道配置控件
        self.channel_widgets = []
        for i in range(16):  # 最多16个通道
            row_widgets = self.create_channel_row(i)
            self.channel_widgets.append(row_widgets)

        scroll.setWidget(scroll_widget)
        config_layout.addWidget(scroll)
        config_group.setLayout(config_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("✓ 应用")
        btn_apply.setObjectName("primaryBtn")
        btn_apply.clicked.connect(self.apply_config)

        btn_reset = QPushButton("↻ 重置")
        btn_reset.clicked.connect(self.reset_config)

        btn_cancel = QPushButton("✕ 取消")
        btn_cancel.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_cancel)

        main_layout.addWidget(count_group)
        main_layout.addWidget(config_group)
        main_layout.addLayout(btn_layout)

        # 初始显示
        self.on_count_changed(self.count_combo.currentIndex())

    def create_channel_row(self, index):
        """创建一行通道配置控件"""
        row = index + 1

        # 通道标签
        ch_label = QLabel(f"通道 {index + 1}")
        ch_label.setAlignment(Qt.AlignCenter)
        ch_label.setStyleSheet("padding: 5px;")
        self.grid_layout.addWidget(ch_label, row, 0)

        # 显示复选框
        ch_visible = QCheckBox()
        ch_visible.setChecked(self.current_config['channel_visible'][index])
        ch_visible.setStyleSheet("margin-left: 20px;")
        self.grid_layout.addWidget(ch_visible, row, 1)

        # 名称输入框
        ch_name = QLineEdit()
        ch_name.setText(self.current_config['channel_names'][index])
        ch_name.setPlaceholderText(f"Ch {index + 1}")
        self.grid_layout.addWidget(ch_name, row, 2)

        # 颜色选择按钮
        ch_color_btn = QPushButton()
        ch_color_btn.setFixedSize(60, 25)
        color = self.current_config['channel_colors'][index]
        ch_color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ddd;")
        ch_color_btn.clicked.connect(lambda checked, idx=index: self.choose_color(idx))
        self.grid_layout.addWidget(ch_color_btn, row, 3)

        return {
            'label': ch_label,
            'visible': ch_visible,
            'name': ch_name,
            'color_btn': ch_color_btn,
            'color': color
        }

    def on_count_changed(self, index):
        """通道数量改变"""
        channel_count = CHANNEL_COUNT_OPTIONS[index]

        # 显示/隐藏对应数量的通道
        for i in range(16):
            visible = i < channel_count
            for widget_name in ['label', 'visible', 'name', 'color_btn']:
                self.channel_widgets[i][widget_name].setVisible(visible)

    def choose_color(self, index):
        """选择颜色"""
        from PySide6.QtWidgets import QColorDialog
        current_color = QColor(self.channel_widgets[index]['color'])
        color = QColorDialog.getColor(current_color, self, "选择颜色")

        if color.isValid():
            color_hex = color.name()
            self.channel_widgets[index]['color'] = color_hex
            self.channel_widgets[index]['color_btn'].setStyleSheet(
                f"background-color: {color_hex}; border: 1px solid #ddd;"
            )

    def apply_config(self):
        """应用配置"""
        channel_count = CHANNEL_COUNT_OPTIONS[self.count_combo.currentIndex()]

        config = {
            'channel_count': channel_count,
            'channel_names': [w['name'].text() or f"Ch {i+1}" for i, w in enumerate(self.channel_widgets)],
            'channel_visible': [w['visible'].isChecked() for w in self.channel_widgets],
            'channel_colors': [w['color'] for w in self.channel_widgets]
        }

        self.config_changed.emit(config)
        # 使用非阻塞提示
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("成功")
        msg_box.setText(f"通道配置已更新\n当前通道数: {channel_count}")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.show()
        QTimer.singleShot(0, self.close)  # 非阻塞关闭对话框

    def reset_config(self):
        """重置为默认配置（非阻塞）"""
        # 使用非阻塞确认对话框
        reply_box = QMessageBox(self)
        reply_box.setWindowTitle("确认")
        reply_box.setText("是否重置为默认配置？")
        reply_box.setIcon(QMessageBox.Question)
        reply_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        def handle_reply(result):
            if reply_box.result() == QMessageBox.Yes:
                default_config = {
                    'channel_count': DEFAULT_CHANNEL_COUNT,
                    'channel_names': [f"Ch {i+1}" for i in range(16)],
                    'channel_visible': [True] * 16,
                    'channel_colors': ['#fd79a8', '#0984e3', '#00b894', '#e17055',
                                       '#fdcb6e', '#6c5ce7', '#00cec9', '#ff7675',
                                       '#fab1a0', '#a29bfe', '#55efc4', '#ffeaa7',
                                       '#dfe6e9', '#b2bec3', '#ff6b6b', '#4ecdc4']
                }

                for i in range(16):
                    self.channel_widgets[i]['name'].setText(default_config['channel_names'][i])
                    self.channel_widgets[i]['visible'].setChecked(default_config['channel_visible'][i])
                    self.channel_widgets[i]['color'] = default_config['channel_colors'][i]
                    self.channel_widgets[i]['color_btn'].setStyleSheet(
                        f"background-color: {default_config['channel_colors'][i]}; border: 1px solid #ddd;"
                    )

                default_index = CHANNEL_COUNT_OPTIONS.index(default_config['channel_count']) if default_config['channel_count'] in CHANNEL_COUNT_OPTIONS else 0
                self.count_combo.setCurrentIndex(default_index)

        reply_box.finished.connect(handle_reply)
        reply_box.show()  # 非阻塞显示


# --- 核心逻辑层 ---
class SerialWorker(QThread):
    data_received = Signal(bytes)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.running = False
        self._buffer = bytearray()

    def open_port(self, port, baudrate, bytesize=8, parity='N', stopbits=1, retry=False):
        """
        打开串口（增强版 - 智能错误处理）
        :param port: 端口名称
        :param baudrate: 波特率
        :param bytesize: 数据位 (5, 6, 7, 8)
        :param parity: 校验位 ('N', 'E', 'O', 'M', 'S')
        :param stopbits: 停止位 (1, 1.5, 2)
        :param retry: 是否自动重试
        """
        # 先确保之前的连接已完全关闭
        if self.ser is not None:
            print("检测到残留串口对象，正在清理...")
            self.close_port()

        try:
            # 检查端口是否在可用端口列表中
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            if port not in available_ports:
                return False, f"❌ 端口 {port} 不存在或未连接！\n\n请检查设备连接并刷新端口列表。"

            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=0.05,
                write_timeout=1.0
            )
            self.running = True
            self.start()
            return True, "连接成功喵！"

        except PermissionError as e:
            # 串口被占用的专门处理
            error_msg = f"❌ 串口 {port} 被占用，无法访问！\n\n"
            error_msg += "📌 可能原因：\n"
            error_msg += "1️⃣ 其他程序正在使用该串口\n"
            error_msg += "   （如：Arduino IDE、串口调试助手、其他PaperCat实例）\n"
            error_msg += "2️⃣ 上次连接未正常关闭\n"
            error_msg += "3️⃣ 设备驱动异常\n\n"
            error_msg += "💡 解决方案：\n"
            error_msg += "✓ 关闭其他可能使用该串口的程序\n"
            error_msg += "✓ 拔出设备后重新插入\n"
            error_msg += "✓ 重启计算机\n"
            error_msg += "✓ 检查设备管理器中的串口状态\n\n"
            error_msg += f"🔍 详细错误: {str(e)}"
            return False, error_msg

        except serial.SerialException as e:
            error_str = str(e).lower()

            # 串口不存在
            if "could not open port" in error_str or "does not exist" in error_str:
                error_msg = f"❌ 串口 {port} 不存在！\n\n"
                error_msg += "📌 可能原因：\n"
                error_msg += "1️⃣ 设备未连接或已断开\n"
                error_msg += "2️⃣ 驱动未正确安装\n"
                error_msg += "3️⃣ USB线缆损坏\n\n"
                error_msg += "💡 解决方案：\n"
                error_msg += "✓ 检查设备是否已插入\n"
                error_msg += "✓ 重新插拔USB设备\n"
                error_msg += "✓ 在设备管理器中查看串口列表\n"
                error_msg += "✓ 安装/更新USB驱动程序"

            # 访问被拒绝
            elif "access is denied" in error_str or "permission" in error_str:
                error_msg = f"❌ 拒绝访问串口 {port}！\n\n"
                error_msg += "📌 可能原因：\n"
                error_msg += "1️⃣ 串口被其他程序占用\n"
                error_msg += "2️⃣ 权限不足\n\n"
                error_msg += "💡 解决方案：\n"
                error_msg += "✓ 以管理员身份运行程序\n"
                error_msg += "✓ 关闭占用串口的其他程序"

            else:
                error_msg = f"❌ 串口错误: {str(e)}\n\n"
                error_msg += "💡 建议：\n"
                error_msg += "✓ 检查串口设置是否正确\n"
                error_msg += "✓ 尝试更换其他串口或USB接口"

            return False, error_msg

        except ValueError as e:
            error_msg = f"❌ 参数配置错误！\n\n"
            error_msg += f"🔍 详细信息: {str(e)}\n\n"
            error_msg += "💡 建议：\n"
            error_msg += "✓ 检查波特率、数据位、校验位、停止位设置\n"
            error_msg += "✓ 参考设备说明书确认正确的串口参数"
            return False, error_msg

        except Exception as e:
            error_msg = f"❌ 未知错误: {str(e)}\n\n"
            error_msg += "💡 建议：\n"
            error_msg += "✓ 重启程序后重试\n"
            error_msg += "✓ 检查设备连接状态\n"
            error_msg += "✓ 联系技术支持"
            return False, error_msg

    def close_port(self):
        """关闭串口（真正非阻塞版 - 不等待）"""
        # 1. 立即停止接收线程
        self.running = False

        # 2. 不等待，直接强制终止线程（非阻塞）
        if self.isRunning():
            self.terminate()
            # 不等待terminate完成，让它在后台完成

        # 3. 快速关闭串口（不等待）
        if self.ser:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except:
                pass
            finally:
                self.ser = None

        # 4. 清空内部缓冲区
        self._buffer.clear()

        # 注意：不再使用任何time.sleep()，完全非阻塞

    def run(self):
        """优化的数据接收循环"""
        while self.running and self.ser and self.ser.is_open:
            try:
                # 批量读取提高效率
                bytes_available = self.ser.in_waiting
                if bytes_available > 0:
                    # 一次最多读取4096字节
                    chunk_size = min(bytes_available, 4096)
                    data = self.ser.read(chunk_size)
                    if data:
                        self.data_received.emit(data)
                else:
                    self.msleep(5)  # 减少CPU占用
            except serial.SerialException:
                # 串口异常，退出循环
                break
            except Exception:
                # 其他异常，继续尝试
                self.msleep(10)

    def send(self, data):
        """发送数据，带错误处理"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(data)
                return True
            except serial.SerialTimeoutException:
                return False
            except Exception:
                return False
        return False


# --- UI 表现层 (PaperCat v4.4 - 上下左右全自由版) ---
class PaperCatSerial(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = SerialWorker()
        self.worker.data_received.connect(self.handle_rx)

        self.rx_count = 0
        self.tx_count = 0
        self.auto_send_timer = QTimer()
        self.auto_send_timer.timeout.connect(self.send_data)

        # 使用 deque 提高性能
        self.max_points = 300
        self.max_channels = 16  # 扩展到16通道
        self.current_channel_count = DEFAULT_CHANNEL_COUNT  # 当前启用的通道数
        self.auto_channel_count = True  # 自动匹配通道数量
        self.auto_channel_up_threshold = 2
        self.auto_channel_down_threshold = 5
        self._auto_channel_last_detected = None
        self._auto_channel_stable_count = 0
        self.plot_data_buffer = [deque(maxlen=self.max_points) for _ in range(self.max_channels)]

        # 性能优化计数器
        self.update_counter = 0  # 用于降低统计更新频率
        self.stats_update_interval = 10  # 每10次数据更新才更新一次统计显示

        # 画图间隔控制
        self.plot_update_counter = 0  # 画图更新计数器
        self.plot_update_interval = 1  # 画图更新间隔（每接收N次数据才更新一次图表）默认1=实时更新

        # X轴时间轴相关
        self.use_time_axis = True  # 是否使用时间轴
        self.time_resolution = 10  # 时间分辨率（毫秒）
        self.data_start_time = None  # 数据开始时间
        self.time_buffer = [deque(maxlen=self.max_points) for _ in range(self.max_channels)]  # 时间戳缓冲区
        self.auto_follow_x = True  # X轴自动跟随
        self._last_x_range = None
        self._x_follow_padding_ratio = 0.02
        self._x_follow_min_span = 1

        self.curves = []
        self.last_port_list = []
        self.is_display_paused = False

        # 正则表达式缓存
        self._regex_cache = {}
        self._compiled_pattern = None
        self._last_pattern_text = ""

        # JustFloat 协议缓冲区
        self._justfloat_buffer = bytearray()
        self._justfloat_tail = b'\x00\x00\x80\x7f'  # float +inf

        # FireWater 协议缓冲区
        self._firewater_buffer = ""
        self._firewater_channels = {}

        # 文本显示缓冲区（用于按行显示）
        self._text_display_buffer = ""
        self.max_log_blocks = MAX_LOG_BLOCKS
        self.max_text_buffer_chars = MAX_TEXT_BUFFER_CHARS
        self.max_record_points = MAX_RECORD_POINTS

        # 数据录制
        self.is_recording = False
        self.record_data = deque(maxlen=self.max_record_points) if self.max_record_points else []
        self.record_start_time = None

        # 通道配置（支持16个通道）
        self.channel_visible = [True] * self.max_channels
        self.channel_colors = ['#fd79a8', '#0984e3', '#00b894', '#e17055',
                               '#fdcb6e', '#6c5ce7', '#00cec9', '#ff7675',
                               '#fab1a0', '#a29bfe', '#55efc4', '#ffeaa7',
                               '#dfe6e9', '#b2bec3', '#ff6b6b', '#4ecdc4']
        self.channel_names = [f"Ch {i+1}" for i in range(self.max_channels)]

        # 统计数据
        self.channel_stats = {
            'min': [float('inf')] * self.max_channels,
            'max': [float('-inf')] * self.max_channels,
            'sum': [0.0] * self.max_channels,
            'count': [0] * self.max_channels,
            'current': [0.0] * self.max_channels
        }

        # 通道配置对话框
        self.channel_config_dialog = None

        # 响应式缩放配置
        self.base_width = 1200  # 基准宽度
        self.base_height = 850  # 基准高度
        self.base_font_size = 13  # 基准字体大小
        self.current_scale = 1.0  # 当前缩放比例
        self.last_scale_update = 1.0  # 上次更新样式时的比例
        self.scale_threshold = 0.05  # 缩放阈值（5%变化才更新）
        self.style_update_timer = QTimer()  # 样式更新定时器
        self.style_update_timer.setSingleShot(True)
        self.style_update_timer.timeout.connect(self._update_scaled_styles)

        self.setWindowTitle("PaperCat Serial v5.3 - 完美拉伸版")
        self.resize(1200, 850)
        self.setMinimumSize(900, 650)  # 增加最小宽度以适应侧边栏控件

        # 应用初始样式（1.0 缩放）
        self._apply_scaled_stylesheet(1.0)

        self.init_ui()
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.smart_scan_ports)
        self.scan_timer.start(2000)  # 优化：2秒扫描一次，减少CPU占用
        self.smart_scan_ports()

        # 显示优化状态日志
        if self.opengl_enabled:
            self.append_system_log("🚀 OpenGL 硬件加速已启用")
        else:
            self.append_system_log("⚠️ OpenGL 未启用，使用软件渲染")

    def init_ui(self):
        # 创建中心widget作为容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # 保持纯色背景，避免背景图片渲染造成卡顿

        # 最外层：水平分割 (左边栏 vs 右边主区)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(5)  # 设置分割线宽度
        central_layout.addWidget(main_splitter)

        # === 左侧边栏 (Sidebar) ===
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(15)

        cfg_group = QGroupBox("🔗 硬件连接")
        cfg_layout = QGridLayout()  # 使用网格布局精确控制
        cfg_layout.setVerticalSpacing(12)  # 行间距
        cfg_layout.setHorizontalSpacing(8)  # 列间距
        cfg_layout.setContentsMargins(15, 20, 15, 15)  # 内边距

        row = 0

        # 端口选择
        port_label = QLabel("端口:")
        port_label.setFixedHeight(20)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(32)
        self.port_combo.setMaximumHeight(32)
        cfg_layout.addWidget(port_label, row, 0, 1, 2)
        row += 1
        cfg_layout.addWidget(self.port_combo, row, 0, 1, 2)
        row += 1

        # 波特率
        baud_label = QLabel("波特率:")
        baud_label.setFixedHeight(20)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "38400", "19200", "57600", "4800", "2400"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setMinimumHeight(32)
        self.baud_combo.setMaximumHeight(32)
        cfg_layout.addWidget(baud_label, row, 0, 1, 2)
        row += 1
        cfg_layout.addWidget(self.baud_combo, row, 0, 1, 2)
        row += 1

        # 数据位
        databit_label = QLabel("数据位:")
        databit_label.setFixedHeight(20)
        self.databit_combo = QComboBox()
        self.databit_combo.addItems(["8", "7", "6", "5"])
        self.databit_combo.setCurrentText("8")
        self.databit_combo.setMinimumHeight(32)
        self.databit_combo.setMaximumHeight(32)
        cfg_layout.addWidget(databit_label, row, 0, 1, 2)
        row += 1
        cfg_layout.addWidget(self.databit_combo, row, 0, 1, 2)
        row += 1

        # 校验位
        parity_label = QLabel("校验位:")
        parity_label.setFixedHeight(20)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self.parity_combo.setCurrentText("None")
        self.parity_combo.setMinimumHeight(32)
        self.parity_combo.setMaximumHeight(32)
        cfg_layout.addWidget(parity_label, row, 0, 1, 2)
        row += 1
        cfg_layout.addWidget(self.parity_combo, row, 0, 1, 2)
        row += 1

        # 停止位
        stopbit_label = QLabel("停止位:")
        stopbit_label.setFixedHeight(20)
        self.stopbit_combo = QComboBox()
        self.stopbit_combo.addItems(["1", "1.5", "2"])
        self.stopbit_combo.setCurrentText("1")
        self.stopbit_combo.setMinimumHeight(32)
        self.stopbit_combo.setMaximumHeight(32)
        cfg_layout.addWidget(stopbit_label, row, 0, 1, 2)
        row += 1
        cfg_layout.addWidget(self.stopbit_combo, row, 0, 1, 2)
        row += 1

        # 添加一些垂直空白
        row += 1

        # 连接按钮
        self.action_btn = QPushButton("打开串口喵")
        self.action_btn.setObjectName("primaryBtn")
        self.action_btn.setCheckable(True)
        self.action_btn.setMinimumHeight(40)
        self.action_btn.setMaximumHeight(40)
        self.action_btn.toggled.connect(self.toggle_connection)
        cfg_layout.addWidget(self.action_btn, row, 0, 1, 2)

        # 设置行拉伸因子，让最后一行占据剩余空间
        cfg_layout.setRowStretch(row + 1, 1)

        cfg_group.setLayout(cfg_layout)

        filter_group = QGroupBox("📉 波形协议")
        filter_layout = QVBoxLayout()
        self.parse_mode_combo = QComboBox()
        self.parse_mode_combo.addItems([
            "🚀 自动抓数字",
            "🛡️ 逗号分隔 (,)",
            "📦 空格分隔 ( )",
            "🧙‍♂️ 正则表达式",
            "⚡ JustFloat",
            "🔥 FireWater"
        ])
        self.parse_mode_combo.currentIndexChanged.connect(self.on_parse_mode_change)
        self.custom_regex_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_regex_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_pattern = QLineEdit()
        self.txt_pattern.setText(r"[-+]?\d*\.\d+|\d+")
        custom_layout.addWidget(QLabel("正则规则:"))
        custom_layout.addWidget(self.txt_pattern)
        self.custom_regex_widget.setVisible(False)
        filter_layout.addWidget(QLabel("解析规则:"))
        filter_layout.addWidget(self.parse_mode_combo)
        filter_layout.addWidget(self.custom_regex_widget)
        filter_group.setLayout(filter_layout)

        # 通道设置按钮
        channel_btn_group = QGroupBox("⚙️ 通道设置")
        channel_btn_layout = QVBoxLayout()
        self.btn_channel_config = QPushButton("🎛️ 配置通道")
        self.btn_channel_config.clicked.connect(self.open_channel_config)
        self.btn_channel_config.setMinimumHeight(35)
        channel_btn_layout.addWidget(self.btn_channel_config)
        channel_btn_group.setLayout(channel_btn_layout)

        sidebar_layout.addWidget(cfg_group)
        sidebar_layout.addWidget(filter_group)
        sidebar_layout.addWidget(channel_btn_group)
        sidebar_layout.addStretch()

        # === 中间主操作区 (Center Panel) ===
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)  # 贴边
        center_layout.setSpacing(0)

        # ✨✨✨ 新增：垂直分割器 (Vertical Splitter) ✨✨✨
        # 用它来分割 [上部分：显示] 和 [下部分：控制台]
        right_splitter = QSplitter(Qt.Vertical)

        # --- 上半部分容器 (Top Container) ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 10, 10, 0)  # 底部留白给分割线
        top_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tab_chat = QWidget()
        chat_layout = QVBoxLayout(self.tab_chat)
        chat_layout.setContentsMargins(5, 5, 5, 5)
        self.display_area = QTextBrowser()
        self.display_area.setOpenExternalLinks(False)
        self.display_area.setUndoRedoEnabled(False)
        self.display_area.document().setMaximumBlockCount(self.max_log_blocks)
        # 统一终端行样式（对齐由块格式控制）
        self.display_area.document().setDefaultStyleSheet(
            ".rx-line { color: #2d3436; }\n"
            ".tx-line { color: #0984e3; }\n"
            ".sys-left { color: #6c5ce7; font-size: 11px; text-align: left; display: block; width: 100%; }\n"
            ".sys-center { color: #6c5ce7; font-size: 11px; text-align: center; display: block; width: 100%; }\n"
        )
        chat_layout.addWidget(self.display_area)

        self.tab_plot = QWidget()
        plot_layout = QVBoxLayout(self.tab_plot)

        # 启用 OpenGL 硬件加速（大幅提升性能）
        self.opengl_enabled = False
        try:
            pg.setConfigOptions(antialias=True, background='w', foreground='k', useOpenGL=True)
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')  # 纯白色背景，避免阴影
            self.opengl_enabled = True
        except Exception as e:
            # 如果 OpenGL 不可用，回退到普通模式
            pg.setConfigOptions(antialias=True, background='w', foreground='k')
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')
            print(f"OpenGL 不可用，使用软件渲染: {e}")

        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', '数值')
        self.plot_widget.setLabel('bottom', '时间 (毫秒)')  # 默认使用毫秒

        # 设置右键菜单为中文
        self._setup_plot_context_menu()

        # 创建最大通道的曲线
        for i in range(self.max_channels):
            pen = pg.mkPen(color=self.channel_colors[i], width=2)
            curve = self.plot_widget.plot(name=self.channel_names[i], pen=pen)
            self.curves.append(curve)

        plot_layout.addWidget(self.plot_widget)
        self.tabs.addTab(self.tab_chat, "💬 交互终端")
        self.tabs.addTab(self.tab_plot, "📈 实时示波器")

        # Toolbar（使用StackedWidget实现分tab切换）
        self.toolbar_stack = QStackedWidget()

        # === 工具栏 1: 交互终端工具栏 ===
        terminal_toolbar_frame = QFrame()
        terminal_toolbar_frame.setStyleSheet("background-color: #ffffff; border-radius: 6px; border: 1px solid #e1e4e8;")
        terminal_toolbar_layout = QHBoxLayout(terminal_toolbar_frame)
        terminal_toolbar_layout.setContentsMargins(10, 5, 10, 5)
        terminal_toolbar_layout.setSpacing(8)

        self.btn_clear_terminal = QPushButton("🗑️ 清空终端")
        self.btn_clear_terminal.clicked.connect(self.clear_logs)
        self.btn_clear_terminal.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_clear_terminal.setMinimumWidth(90)

        self.btn_pause = QPushButton("⏸ 暂停显示")
        self.btn_pause.setObjectName("pauseBtn")
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self.toggle_display_pause)
        self.btn_pause.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_pause.setMinimumWidth(90)

        self.check_auto_scroll = QCheckBox("自动滚屏")
        self.check_auto_scroll.setChecked(True)
        self.check_auto_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.check_time_show = QCheckBox("时间戳")
        self.check_time_show.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 添加分隔符
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setStyleSheet("color: #dfe6e9;")

        self.lbl_rx_cnt = QLabel("RX: 0")
        self.lbl_tx_cnt = QLabel("TX: 0")
        self.lbl_rx_cnt.setStyleSheet("color: #00b894; font-weight: bold;")
        self.lbl_tx_cnt.setStyleSheet("color: #0984e3; font-weight: bold;")
        self.lbl_rx_cnt.setMinimumWidth(80)
        self.lbl_tx_cnt.setMinimumWidth(80)
        self.lbl_rx_cnt.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.lbl_tx_cnt.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        btn_reset_cnt = QPushButton("计数清零")
        btn_reset_cnt.clicked.connect(self.reset_counters)
        btn_reset_cnt.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        terminal_toolbar_layout.addWidget(self.btn_clear_terminal)
        terminal_toolbar_layout.addWidget(self.btn_pause)
        terminal_toolbar_layout.addSpacing(5)
        terminal_toolbar_layout.addWidget(self.check_auto_scroll)
        terminal_toolbar_layout.addWidget(self.check_time_show)
        terminal_toolbar_layout.addStretch(1)
        terminal_toolbar_layout.addWidget(separator1)
        terminal_toolbar_layout.addSpacing(5)
        terminal_toolbar_layout.addWidget(self.lbl_rx_cnt)
        terminal_toolbar_layout.addWidget(self.lbl_tx_cnt)
        terminal_toolbar_layout.addWidget(btn_reset_cnt)

        # === 工具栏 2: 示波器工具栏 ===
        oscilloscope_toolbar_frame = QFrame()
        oscilloscope_toolbar_frame.setStyleSheet("background-color: #ffffff; border-radius: 6px; border: 1px solid #e1e4e8;")
        oscilloscope_toolbar_layout = QVBoxLayout(oscilloscope_toolbar_frame)
        oscilloscope_toolbar_layout.setContentsMargins(10, 5, 10, 5)
        oscilloscope_toolbar_layout.setSpacing(4)
        osc_toolbar_row1 = QHBoxLayout()
        osc_toolbar_row1.setSpacing(8)
        osc_toolbar_row2 = QHBoxLayout()
        osc_toolbar_row2.setSpacing(8)

        self.btn_clear_plot_toolbar = QPushButton("🗑️ 清空波形")
        self.btn_clear_plot_toolbar.clicked.connect(self.clear_logs)
        self.btn_clear_plot_toolbar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_clear_plot_toolbar.setMinimumWidth(90)

        self.btn_pause_osc = QPushButton("⏸ 暂停显示")
        self.btn_pause_osc.setObjectName("pauseBtn")
        self.btn_pause_osc.setCheckable(True)
        self.btn_pause_osc.clicked.connect(self.toggle_display_pause)
        self.btn_pause_osc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_pause_osc.setMinimumWidth(90)

        self.btn_record = QPushButton("⏺ 开始录制")
        self.btn_record.setCheckable(True)
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_record.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_record.setMinimumWidth(90)

        self.btn_export = QPushButton("📁 导出CSV")
        self.btn_export.clicked.connect(self.export_to_csv)
        self.btn_export.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_export.setMinimumWidth(90)

        self.btn_y_auto = QPushButton("📏 Y轴自适应")
        self.btn_y_auto.setCheckable(True)
        self.btn_y_auto.setChecked(True)
        self.btn_y_auto.clicked.connect(self.toggle_y_auto_scale)
        self.btn_y_auto.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_y_auto.setMinimumWidth(100)

        self.btn_x_follow = QPushButton("↔ X轴跟随")
        self.btn_x_follow.setCheckable(True)
        self.btn_x_follow.setChecked(True)
        self.btn_x_follow.clicked.connect(self.toggle_x_follow)
        self.btn_x_follow.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_x_follow.setMinimumWidth(100)
        self.btn_x_follow.setToolTip("开启后X轴自动跟随最新数据\n关闭后可手动缩放和拖动")

        self.btn_auto_center = QPushButton("🎯 Auto对齐")
        self.btn_auto_center.clicked.connect(self.auto_center_waveform)
        self.btn_auto_center.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_auto_center.setMinimumWidth(100)
        self.btn_auto_center.setToolTip("自动对齐波形到屏幕中心\n适合快速定位和观察波形")

        self.lbl_rx_cnt_osc = QLabel("RX: 0")
        self.lbl_tx_cnt_osc = QLabel("TX: 0")
        self.lbl_rx_cnt_osc.setStyleSheet("color: #00b894; font-weight: bold;")
        self.lbl_tx_cnt_osc.setStyleSheet("color: #0984e3; font-weight: bold;")
        self.lbl_rx_cnt_osc.setMinimumWidth(80)
        self.lbl_tx_cnt_osc.setMinimumWidth(80)
        self.lbl_rx_cnt_osc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.lbl_tx_cnt_osc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        btn_reset_cnt_osc = QPushButton("计数清零")
        btn_reset_cnt_osc.clicked.connect(self.reset_counters)
        btn_reset_cnt_osc.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        osc_toolbar_row1.addWidget(self.btn_clear_plot_toolbar)
        osc_toolbar_row1.addWidget(self.btn_pause_osc)
        osc_toolbar_row1.addWidget(self.btn_record)
        osc_toolbar_row1.addWidget(self.btn_export)
        osc_toolbar_row1.addWidget(self.btn_y_auto)
        osc_toolbar_row1.addWidget(self.btn_x_follow)
        osc_toolbar_row1.addWidget(self.btn_auto_center)
        osc_toolbar_row1.addStretch(1)

        osc_toolbar_row2.addStretch(1)
        osc_toolbar_row2.addWidget(self.lbl_rx_cnt_osc)
        osc_toolbar_row2.addWidget(self.lbl_tx_cnt_osc)
        osc_toolbar_row2.addWidget(btn_reset_cnt_osc)

        oscilloscope_toolbar_layout.addLayout(osc_toolbar_row1)
        oscilloscope_toolbar_layout.addLayout(osc_toolbar_row2)

        # 将两个工具栏添加到StackedWidget
        self.toolbar_stack.addWidget(terminal_toolbar_frame)  # 索引 0
        self.toolbar_stack.addWidget(oscilloscope_toolbar_frame)  # 索引 1

        top_layout.addWidget(self.tabs)
        top_layout.addWidget(self.toolbar_stack)

        # --- 下半部分容器 (Bottom Container: 控制台) ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(10, 0, 10, 10)
        bottom_layout.setSpacing(0)

        # 使用 QStackedWidget 来管理两种控制面板
        self.control_stack = QStackedWidget()

        # === 面板 1: 交互终端控制面板 ===
        terminal_panel = QWidget()
        terminal_layout = QVBoxLayout(terminal_panel)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.setSpacing(10)

        # 发送控制台
        deck_group = QGroupBox("🚀 指挥控制台")
        deck_layout = QVBoxLayout()
        send_row = QHBoxLayout()
        self.input_box = QComboBox()
        self.input_box.setEditable(True)
        self.input_box.setMinimumHeight(40)
        self.input_box.lineEdit().setPlaceholderText("在此输入指令... (支持 Enter 发送)")
        self.input_box.lineEdit().returnPressed.connect(self.send_data)
        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("sendBigBtn")
        self.send_btn.setFixedSize(100, 40)
        self.send_btn.clicked.connect(self.send_data)
        send_row.addWidget(self.input_box, 1)
        send_row.addWidget(self.send_btn)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(15)
        ctrl_row.addWidget(QLabel("👀 接收:"))
        self.combo_rx_mode = QComboBox()
        self.combo_rx_mode.addItems(["UTF-8", "GBK", "HEX", "DEC", "BIN"])
        self.combo_rx_mode.setFixedWidth(80)
        ctrl_row.addWidget(self.combo_rx_mode)
        ctrl_row.addWidget(QLabel("|  📤 发送:"))
        self.combo_tx_mode = QComboBox()
        self.combo_tx_mode.addItems(["UTF-8", "GBK", "HEX"])
        self.combo_tx_mode.setFixedWidth(80)
        ctrl_row.addWidget(self.combo_tx_mode)
        self.check_add_newline = QCheckBox("加换行(\\r\\n)")
        self.check_add_newline.setChecked(True)
        ctrl_row.addWidget(self.check_add_newline)
        ctrl_row.addStretch()
        self.check_timer_send = QCheckBox("定时循环:")
        self.check_timer_send.stateChanged.connect(self.toggle_auto_send)
        self.spin_timer = QSpinBox()
        self.spin_timer.setRange(10, 100000)
        self.spin_timer.setValue(1000)
        self.spin_timer.setSuffix(" ms")
        self.spin_timer.setFixedWidth(90)
        ctrl_row.addWidget(self.check_timer_send)
        ctrl_row.addWidget(self.spin_timer)
        deck_layout.addLayout(send_row)
        deck_layout.addLayout(ctrl_row)
        deck_group.setLayout(deck_layout)

        # 快捷发送面板
        quick_group = QGroupBox("⚡ 快捷发送")
        quick_layout = QGridLayout()
        quick_layout.setSpacing(5)
        self.quick_btns = []
        self.quick_edits = []
        for i in range(6):  # 6个快捷按钮
            edit = QLineEdit()
            edit.setPlaceholderText(f"指令{i+1}")
            btn = QPushButton(f"发送{i+1}")
            btn.clicked.connect(lambda checked, idx=i: self.send_quick_command(idx))
            self.quick_edits.append(edit)
            self.quick_btns.append(btn)
            quick_layout.addWidget(edit, i // 3, (i % 3) * 2)
            quick_layout.addWidget(btn, i // 3, (i % 3) * 2 + 1)
        quick_group.setLayout(quick_layout)

        terminal_layout.addWidget(deck_group)
        terminal_layout.addWidget(quick_group)

        # === 面板 2: 示波器控制面板 ===
        oscilloscope_panel = QWidget()
        oscilloscope_layout = QVBoxLayout(oscilloscope_panel)
        oscilloscope_layout.setContentsMargins(0, 0, 0, 0)
        oscilloscope_layout.setSpacing(10)

        # 示波器控制组
        osc_control_group = QGroupBox("📊 波形控制")
        osc_control_layout = QGridLayout()
        osc_control_layout.setSpacing(10)

        # 第一行：录制和导出
        self.btn_record_osc = QPushButton("⏺ 开始录制")
        self.btn_record_osc.setCheckable(True)
        self.btn_record_osc.clicked.connect(self.toggle_recording)
        self.btn_record_osc.setMinimumHeight(35)

        self.btn_export_osc = QPushButton("📁 导出CSV")
        self.btn_export_osc.clicked.connect(self.export_to_csv)
        self.btn_export_osc.setMinimumHeight(35)

        osc_control_layout.addWidget(self.btn_record_osc, 0, 0)
        osc_control_layout.addWidget(self.btn_export_osc, 0, 1)

        # 第二行：Y轴控制和清空
        self.btn_y_auto_osc = QPushButton("📏 Y轴自适应")
        self.btn_y_auto_osc.setCheckable(True)
        self.btn_y_auto_osc.setChecked(True)
        self.btn_y_auto_osc.clicked.connect(self.toggle_y_auto_scale)
        self.btn_y_auto_osc.setMinimumHeight(35)

        self.btn_clear_plot = QPushButton("🗑️ 清空波形")
        self.btn_clear_plot.clicked.connect(self.clear_logs)
        self.btn_clear_plot.setMinimumHeight(35)

        osc_control_layout.addWidget(self.btn_y_auto_osc, 1, 0)
        osc_control_layout.addWidget(self.btn_clear_plot, 1, 1)

        # 第三行：X轴跟随开关
        self.btn_x_follow_osc = QPushButton("↔ X轴跟随")
        self.btn_x_follow_osc.setCheckable(True)
        self.btn_x_follow_osc.setChecked(True)
        self.btn_x_follow_osc.clicked.connect(self.toggle_x_follow)
        self.btn_x_follow_osc.setMinimumHeight(35)
        self.btn_x_follow_osc.setToolTip("开启后X轴自动跟随最新数据\n关闭后可手动缩放和拖动")
        osc_control_layout.addWidget(self.btn_x_follow_osc, 2, 0, 1, 2)

        # 第四行：X轴时间分辨率控制
        time_res_label = QLabel("⏱️ X轴分辨率:")
        time_res_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.time_resolution_combo = QComboBox()
        self.time_resolution_combo.addItems([
            "1 ms",    # 1毫秒
            "5 ms",    # 5毫秒
            "10 ms",   # 10毫秒（默认）
            "20 ms",   # 20毫秒
            "50 ms",   # 50毫秒
            "100 ms",  # 100毫秒
            "200 ms",  # 200毫秒
            "500 ms",  # 500毫秒
            "1 s",     # 1秒
        ])
        self.time_resolution_combo.setCurrentIndex(2)  # 默认10ms
        self.time_resolution_combo.setMinimumHeight(35)
        self.time_resolution_combo.setToolTip("设置X轴时间刻度分辨率\n数值越小，时间轴越精细，适合观察快速变化")
        self.time_resolution_combo.currentIndexChanged.connect(self.on_time_resolution_changed)

        osc_control_layout.addWidget(time_res_label, 3, 0)
        osc_control_layout.addWidget(self.time_resolution_combo, 3, 1)

        osc_control_group.setLayout(osc_control_layout)

        # 数据统计面板
        stats_group = QGroupBox("📈 实时统计")
        stats_layout = QVBoxLayout()
        stats_scroll = QScrollArea()
        stats_scroll.setWidgetResizable(True)
        stats_scroll.setMaximumHeight(150)
        stats_widget = QWidget()
        stats_grid = QGridLayout(stats_widget)
        stats_grid.setSpacing(5)

        self.stat_labels = []
        headers = ["通道", "当前值", "最小值", "最大值", "平均值"]
        for col, header in enumerate(headers):
            lbl = QLabel(f"<b>{header}</b>")
            lbl.setStyleSheet("color: #636e72; font-size: 12px; padding: 5px;")
            lbl.setAlignment(Qt.AlignCenter)
            stats_grid.addWidget(lbl, 0, col)

        for i in range(4):  # 显示前4个通道的统计
            labels_row = []
            ch_lbl = QLabel(f"Ch{i+1}")
            ch_lbl.setStyleSheet(f"color: {self.channel_colors[i]}; font-weight: bold; font-size: 12px; padding: 5px;")
            ch_lbl.setAlignment(Qt.AlignCenter)
            stats_grid.addWidget(ch_lbl, i+1, 0)
            labels_row.append(ch_lbl)

            for col in range(1, 5):
                lbl = QLabel("--")
                lbl.setStyleSheet("font-size: 12px; color: #2d3436; padding: 5px;")
                lbl.setAlignment(Qt.AlignCenter)
                stats_grid.addWidget(lbl, i+1, col)
                labels_row.append(lbl)
            self.stat_labels.append(labels_row)

        stats_scroll.setWidget(stats_widget)
        stats_layout.addWidget(stats_scroll)
        stats_group.setLayout(stats_layout)

        oscilloscope_layout.addWidget(osc_control_group)
        oscilloscope_layout.addWidget(stats_group)

        # 将两个面板添加到 StackedWidget
        self.control_stack.addWidget(terminal_panel)  # 索引 0
        self.control_stack.addWidget(oscilloscope_panel)  # 索引 1

        bottom_layout.addWidget(self.control_stack)

        # 连接标签页切换信号
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 将上下两部分加入垂直分割器
        right_splitter.addWidget(top_widget)
        right_splitter.addWidget(bottom_widget)

        # 优化垂直分割器设置（增加流畅度）
        right_splitter.setHandleWidth(5)
        right_splitter.setChildrenCollapsible(False)
        right_splitter.setSizes([500, 300])
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)
        right_splitter.setOpaqueResize(True)  # 实时调整大小，避免卡顿

        # 设置最小尺寸
        top_widget.setMinimumHeight(200)
        bottom_widget.setMinimumHeight(150)

        center_layout.addWidget(right_splitter)

        # === 右侧边栏 (Right Sidebar) ===
        right_sidebar = QWidget()
        right_sidebar_layout = QVBoxLayout(right_sidebar)
        right_sidebar_layout.setContentsMargins(10, 10, 10, 10)
        right_sidebar_layout.setSpacing(15)

        # 吉祥物
        self.mascot_label = QLabel()
        self.mascot_label.setObjectName("mascotLabel")
        self.mascot_label.setFixedHeight(200)
        self.mascot_label.setAlignment(Qt.AlignCenter)
        if os.path.exists("eco.png"):
            self.mascot_label.setPixmap(
                QPixmap("eco.png").scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.mascot_label.setText("缺 eco.png 喵！")
            self.mascot_label.setStyleSheet("border: 2px dashed #a29bfe; border-radius: 10px; color: #a29bfe;")

        right_sidebar_layout.addWidget(self.mascot_label)
        right_sidebar_layout.addStretch()

        # 最外层组装：三栏布局（优化拖动性能）
        # 先创建中间+右侧的水平分割器
        center_right_splitter = QSplitter(Qt.Horizontal)
        center_right_splitter.addWidget(center_panel)
        center_right_splitter.addWidget(right_sidebar)
        center_right_splitter.setHandleWidth(5)
        center_right_splitter.setChildrenCollapsible(False)
        center_right_splitter.setSizes([800, 200])  # 中间区域更大
        center_right_splitter.setStretchFactor(0, 4)  # 中间优先拉伸
        center_right_splitter.setStretchFactor(1, 0)  # 右侧保持宽度
        center_right_splitter.setOpaqueResize(True)  # 实时调整大小

        # 最外层：左侧 + (中间+右侧)
        main_splitter.addWidget(sidebar)
        main_splitter.addWidget(center_right_splitter)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setSizes([240, 960])
        main_splitter.setStretchFactor(0, 0)  # 左侧边栏保持宽度
        main_splitter.setStretchFactor(1, 1)  # 中间+右侧区域拉伸
        main_splitter.setOpaqueResize(True)  # 实时调整大小，避免卡顿

        # 设置侧边栏宽度限制
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(400)
        right_sidebar.setMinimumWidth(200)
        right_sidebar.setMaximumWidth(350)

        # 设置中间面板最小宽度
        center_panel.setMinimumWidth(500)

    # --- 逻辑功能 ---
    def _setup_plot_context_menu(self):
        """设置示波器右键菜单为中文"""
        try:
            # 获取 ViewBox 的菜单
            menu = self.plot_widget.plotItem.vb.menu

            # 中英文对照字典
            translations = {
                'View All': '查看全部',
                'X Axis': 'X轴',
                'Y Axis': 'Y轴',
                'Mouse Mode': '鼠标模式',
                'Export...': '导出...',
                '3 button': '三键模式',
                '1 button': '单键模式',
                'Pan': '平移',
                'Rect': '矩形缩放',
                'Auto Range': '自动范围',
                'Manual Range': '手动范围',
                'Reset': '重置',
                'Transforms': '变换',
                'Downsample': '降采样',
                'Average': '平均',
                'Alpha': '透明度',
                'Points': '点',
                'Grid': '网格',
                'FFT': '快速傅里叶变换'
            }

            # 递归修改菜单项文本
            def translate_menu(menu_obj):
                for action in menu_obj.actions():
                    if action.menu():
                        # 如果是子菜单，递归处理
                        translate_menu(action.menu())

                    # 翻译菜单项文本
                    text = action.text()
                    if text in translations:
                        action.setText(translations[text])

            translate_menu(menu)

        except Exception as e:
            print(f"设置中文菜单失败: {e}")

    def _decode_data(self, data, encoding='utf-8'):
        """统一的数据解码方法"""
        try:
            return data.decode(encoding, errors='replace')
        except (UnicodeDecodeError, LookupError):
            return data.decode('utf-8', errors='replace')

    def _format_display_data(self, data, mode):
        """根据显示模式格式化数据"""
        if mode == 0 or mode == 1:  # UTF-8 或 GBK
            encoding = 'utf-8' if mode == 0 else 'gbk'
            return self._decode_data(data, encoding)
        elif mode == 2:  # HEX
            return data.hex(' ').upper()
        elif mode == 3:  # DEC
            return ' '.join(str(b) for b in data)
        elif mode == 4:  # BIN
            return ' '.join(f'{b:08b}' for b in data)
        return str(data)

    def _get_compiled_regex(self, pattern):
        """获取编译后的正则表达式（带缓存）"""
        if pattern != self._last_pattern_text:
            try:
                self._compiled_pattern = re.compile(pattern)
                self._last_pattern_text = pattern
            except re.error:
                self._compiled_pattern = None
        return self._compiled_pattern

    def toggle_display_pause(self):
        """切换暂停显示（同步两个暂停按钮）"""
        # 获取触发者的状态
        sender = self.sender()
        is_checked = sender.isChecked() if sender else self.btn_pause.isChecked()

        # 同步两个按钮的状态
        self.btn_pause.setChecked(is_checked)
        if hasattr(self, 'btn_pause_osc'):
            self.btn_pause_osc.setChecked(is_checked)

        # 更新显示状态
        self.is_display_paused = is_checked
        if self.is_display_paused:
            self.btn_pause.setText("▶ 继续显示")
            if hasattr(self, 'btn_pause_osc'):
                self.btn_pause_osc.setText("▶ 继续显示")
            self.append_system_log("--- 画面已定格 (数据还在接收中) ---")
        else:
            self.btn_pause.setText("⏸ 暂停显示")
            if hasattr(self, 'btn_pause_osc'):
                self.btn_pause_osc.setText("⏸ 暂停显示")
            self.append_system_log("--- 画面恢复更新 ---")

    def handle_rx(self, data):
        """优化的数据接收处理"""
        self.rx_count += len(data)
        self.update_counters()

        display_mode = self.combo_rx_mode.currentIndex()
        parse_mode = self.parse_mode_combo.currentIndex()

        # 解码数据用于文本处理
        text_decoded = self._decode_data(data, 'utf-8' if display_mode != 1 else 'gbk')

        # 显示数据到终端（按行显示，避免一行显示多次数据）
        if not self.is_display_paused and self.tabs.currentIndex() == 0:
            self._display_data_by_lines(data, display_mode)

        # 根据协议模式解析数值数据
        values = []
        if parse_mode == 4:  # JustFloat
            values = self._parse_justfloat(data)
        elif parse_mode == 5:  # FireWater
            values = self._parse_firewater(text_decoded)
        else:  # 其他文本协议
            values = self._parse_numeric_values(text_decoded)

        if values:
            self.update_plot_data(values)
            # 录制数据
            if self.is_recording:
                self.record_data.append({
                    'time': datetime.datetime.now().timestamp() - self.record_start_time,
                    'values': values.copy()
                })

    def _display_data_by_lines(self, data, display_mode):
        """按行显示数据，确保每条数据占据一行（优化版）"""
        # 对于HEX、DEC、BIN模式，直接显示不分行
        if display_mode in [2, 3, 4]:  # HEX, DEC, BIN
            display_text = self._format_display_data(data, display_mode)
            timestamp = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] " if self.check_time_show.isChecked() else ""
            html = f"<span class='rx-line'>{timestamp}<b>RX:</b> {display_text}</span>"
            self._append_terminal_html(html, Qt.AlignLeft)
            if self.check_auto_scroll.isChecked():
                self.display_area.moveCursor(self.display_area.textCursor().End)
            return

        # 对于文本模式（UTF-8, GBK），按行分割显示
        encoding = 'utf-8' if display_mode == 0 else 'gbk'
        text = self._decode_data(data, encoding)

        # 将新数据添加到缓冲区
        self._text_display_buffer += text
        if len(self._text_display_buffer) > self.max_text_buffer_chars:
            self._text_display_buffer = self._text_display_buffer[-self.max_text_buffer_chars:]

        # 按行分割（支持 \n, \r\n, \r）
        lines = self._text_display_buffer.split('\n')

        # 保留最后一个不完整的行在缓冲区中
        self._text_display_buffer = lines[-1]

        # 显示完整的行
        for line in lines[:-1]:
            # 移除可能的 \r 字符
            line = line.rstrip('\r')

            # 只显示非空行（可选：如果需要显示空行，移除这个判断）
            if line:  # 如果想显示空行，改为 if True:
                timestamp = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] " if self.check_time_show.isChecked() else ""
                # 对特殊字符进行HTML转义
                line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html = f"<span class='rx-line'>{timestamp}<b>RX:</b> {line_escaped}</span>"
                self._append_terminal_html(html, Qt.AlignLeft)

        # 自动滚屏
        if self.check_auto_scroll.isChecked():
            self.display_area.moveCursor(self.display_area.textCursor().End)

    def _parse_numeric_values(self, text):
        """解析文本中的数值"""
        values = []
        try:
            mode = self.parse_mode_combo.currentIndex()
            if mode == 0:  # 自动抓数字
                pattern = self._get_compiled_regex(r"[-+]?\d*\.\d+|\d+")
                if pattern:
                    matches = pattern.findall(text)
                    values = [float(m) for m in matches]
            elif mode == 1:  # 逗号分隔
                parts = text.replace(";", ",").split(",")
                for p in parts:
                    try:
                        values.append(float(p.strip()))
                    except ValueError:
                        continue
            elif mode == 2:  # 空格分隔
                parts = text.split()
                for p in parts:
                    try:
                        values.append(float(p.strip()))
                    except ValueError:
                        continue
            elif mode == 3:  # 自定义正则
                pattern_text = self.txt_pattern.text()
                if pattern_text:
                    pattern = self._get_compiled_regex(pattern_text)
                    if pattern:
                        matches = pattern.findall(text)
                        for m in matches:
                            try:
                                values.append(float(m))
                            except (ValueError, TypeError):
                                continue
        except Exception:
            pass
        return values

    def _parse_justfloat(self, data):
        """解析 JustFloat 协议"""
        values = []
        try:
            self._justfloat_buffer.extend(data)

            # 查找帧尾标识
            while True:
                tail_pos = self._justfloat_buffer.find(self._justfloat_tail)
                if tail_pos == -1:
                    # 限制缓冲区大小，防止内存溢出
                    if len(self._justfloat_buffer) > 1024:
                        self._justfloat_buffer = self._justfloat_buffer[-512:]
                    break

                # 提取一帧数据
                frame_data = self._justfloat_buffer[:tail_pos]

                # 解析 float 数组
                float_count = len(frame_data) // 4
                if float_count > 0:
                    for i in range(float_count):
                        try:
                            float_bytes = frame_data[i*4:(i+1)*4]
                            if len(float_bytes) == 4:
                                value = struct.unpack('<f', float_bytes)[0]
                                # 检查是否为有效数值
                                if not (float('inf') == abs(value) or value != value):  # 排除 inf 和 nan
                                    values.append(value)
                        except struct.error:
                            continue

                # 移除已处理的数据
                self._justfloat_buffer = self._justfloat_buffer[tail_pos + 4:]

                if values:
                    break  # 找到一帧就返回

        except Exception:
            pass

        return values

    def _parse_firewater(self, text):
        """解析 FireWater 协议"""
        values = []
        try:
            self._firewater_buffer += text

            lines = self._firewater_buffer.split('\n')
            self._firewater_buffer = lines[-1]  # 保留不完整的行

            for line in lines[:-1]:
                line = line.strip()
                if ':' in line:
                    try:
                        name, value_str = line.split(':', 1)
                        name = name.strip()
                        value = float(value_str.strip())

                        # 动态管理通道
                        if name not in self._firewater_channels:
                            ch_idx = len(self._firewater_channels)
                            if ch_idx < self.max_channels:
                                self._firewater_channels[name] = ch_idx
                                self.channel_names[ch_idx] = name
                                # 更新图例
                                self.curves[ch_idx].opts['name'] = name

                        # 添加到对应通道
                        ch_idx = self._firewater_channels.get(name)
                        if ch_idx is not None:
                            # 填充到对应位置
                            while len(values) <= ch_idx:
                                values.append(0.0)
                            values[ch_idx] = value

                    except (ValueError, IndexError):
                        continue

        except Exception:
            pass

        return values

    def update_plot_data(self, values):
        """更新波形数据（优化版 - 统一平面显示 + 时间轴）"""
        detected_count = len(values)
        if self.parse_mode_combo.currentIndex() == 5 and self._firewater_channels:
            detected_count = max(detected_count, len(self._firewater_channels))
        if self.auto_channel_count:
            self._auto_adjust_channel_count(detected_count)
        num_channels = min(len(values), self.current_channel_count, self.max_channels)

        # 记录当前时间戳（毫秒）
        if self.data_start_time is None:
            self.data_start_time = datetime.datetime.now()

        current_time = datetime.datetime.now()
        elapsed_ms = (current_time - self.data_start_time).total_seconds() * 1000

        # 根据时间分辨率计算X轴坐标
        if self.time_resolution >= 1000:
            # 使用秒作为单位
            x_value = elapsed_ms / 1000.0
        else:
            # 使用毫秒作为单位
            x_value = elapsed_ms

        for i in range(num_channels):
            value = values[i]
            self.plot_data_buffer[i].append(value)
            self.time_buffer[i].append(x_value)

            # 更新统计数据
            self.channel_stats['current'][i] = value
            self.channel_stats['min'][i] = min(self.channel_stats['min'][i], value)
            self.channel_stats['max'][i] = max(self.channel_stats['max'][i], value)
            self.channel_stats['sum'][i] += value
            self.channel_stats['count'][i] += 1

        # 性能优化：降低统计显示更新频率（每10次更新一次）
        self.update_counter += 1
        if self.update_counter >= self.stats_update_interval:
            self.update_statistics_display()
            self.update_counter = 0

        # 画图间隔控制：只有达到指定间隔才更新图表
        self.plot_update_counter += 1

        # 只在显示波形页面且未暂停时更新图表
        if not self.is_display_paused and self.tabs.currentIndex() == 1:
            # 检查是否达到刷新间隔
            if self.plot_update_counter >= self.plot_update_interval:
                # 重置计数器
                self.plot_update_counter = 0

                # 更新所有可见通道的波形（在统一的Y轴下显示，使用时间作为X轴）
                for i in range(min(self.current_channel_count, self.max_channels)):
                    if self.channel_visible[i] and len(self.plot_data_buffer[i]) > 0:
                        # 使用时间戳作为X轴
                        self.curves[i].setData(
                            list(self.time_buffer[i]),
                            list(self.plot_data_buffer[i])
                        )
                    else:
                        self.curves[i].setData([], [])

                # X轴自动跟随最新数据
                if self.auto_follow_x:
                    self._auto_follow_x_axis(num_channels)

                # Y轴自适应（所有通道共享同一Y轴范围）
                if self.btn_y_auto.isChecked():
                    self._auto_scale_y_axis()

    def smart_scan_ports(self):
        """智能串口扫描（优化性能）"""
        try:
            current_hw_ports = sorted([p.device for p in serial.tools.list_ports.comports()])

            # 总是更新端口列表，即使列表相同（确保断开后能重新检测）
            current_selection = self.port_combo.currentText()
            new_devices = list(set(current_hw_ports) - set(self.last_port_list))

            # 清空并重新添加端口列表
            self.port_combo.clear()
            self.port_combo.addItems(current_hw_ports)

            # 自动选择逻辑
            if new_devices and not self.action_btn.isChecked():
                # 有新设备且未连接时，自动选中新设备
                target = new_devices[0]
                self.port_combo.setCurrentText(target)
                self.append_system_log(f"嗅探到新设备: {target}，已自动选中喵！")
            elif current_selection in current_hw_ports:
                # 保持之前的选择
                self.port_combo.setCurrentText(current_selection)
            elif self.port_combo.count() > 0:
                # 默认选择第一个端口
                self.port_combo.setCurrentIndex(0)

            self.last_port_list = current_hw_ports
        except Exception:
            # 扫描失败时静默处理，避免影响用户体验
            pass

    def _append_terminal_html(self, html, align=Qt.AlignLeft):
        """在终端窗口追加HTML（用块格式强制对齐，避免对齐状态污染）"""
        if not hasattr(self, 'display_area'):
            return
        cursor = self.display_area.textCursor()
        cursor.movePosition(QTextCursor.End)

        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(align)
        block_fmt.setTopMargin(2)
        block_fmt.setBottomMargin(2)

        doc = self.display_area.document()
        is_doc_empty = (doc.blockCount() == 1 and doc.firstBlock().length() <= 1)
        if is_doc_empty:
            cursor.setBlockFormat(block_fmt)
        else:
            cursor.insertBlock(block_fmt)

        cursor.insertHtml(html)
        self.display_area.setTextCursor(cursor)

    def append_system_log(self, text):
        if hasattr(self, 'tabs') and hasattr(self, 'display_area'):
            if self.tabs.currentIndex() == 0:
                stripped = text.strip()
                center_prefixes = (
                    "🚀 OpenGL",
                    "⚠️ OpenGL",
                    "嗅探到新设备",
                    "已连接",
                    "正在断开连接",
                    "✅ 端口已释放",
                )
                is_center_line = stripped.startswith(center_prefixes)
                align = Qt.AlignCenter if is_center_line else Qt.AlignLeft
                if is_center_line:
                    self._append_terminal_html(
                        f"<div style='text-align:center; width:100%; color:#6c5ce7; font-size:11px;'>--- {text} ---</div>",
                        align
                    )
                else:
                    self._append_terminal_html(
                        f"<div style='text-align:left; width:100%; color:#6c5ce7; font-size:11px;'>--- {text} ---</div>",
                        align
                    )

    def on_parse_mode_change(self, index):
        self.custom_regex_widget.setVisible(index == 3)

    def on_tab_changed(self, index):
        """标签页切换时切换对应的工具栏和控制面板"""
        # 切换工具栏
        self.toolbar_stack.setCurrentIndex(index)
        # 切换控制面板
        self.control_stack.setCurrentIndex(index)

        # 同步按钮状态
        if index == 0:  # 切换到交互终端页面
            # 同步暂停按钮状态
            self.btn_pause.setChecked(self.btn_pause_osc.isChecked() if hasattr(self, 'btn_pause_osc') else False)
        elif index == 1:  # 切换到示波器页面
            # 同步暂停按钮状态
            self.btn_pause_osc.setChecked(self.btn_pause.isChecked())
            # 同步录制按钮状态
            self.btn_record_osc.setChecked(self.btn_record.isChecked())
            # 同步Y轴自适应状态
            self.btn_y_auto_osc.setChecked(self.btn_y_auto.isChecked())
            # 同步X轴自动跟随状态
            if hasattr(self, 'btn_x_follow_osc'):
                self.btn_x_follow_osc.setChecked(self.btn_x_follow.isChecked())

    def _get_serial_params(self):
        """获取串口配置参数"""
        # 数据位映射
        bytesize_map = {
            "5": serial.FIVEBITS,
            "6": serial.SIXBITS,
            "7": serial.SEVENBITS,
            "8": serial.EIGHTBITS
        }

        # 校验位映射
        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }

        # 停止位映射
        stopbits_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO
        }

        return {
            'bytesize': bytesize_map[self.databit_combo.currentText()],
            'parity': parity_map[self.parity_combo.currentText()],
            'stopbits': stopbits_map[self.stopbit_combo.currentText()]
        }

    def toggle_connection(self, checked):
        """切换串口连接状态（优化版 - 使用toggled信号）"""
        if checked:
            # === 连接串口 ===
            port = self.port_combo.currentText()
            if not port:
                # 阻止信号触发，避免递归
                self.action_btn.blockSignals(True)
                self.action_btn.setChecked(False)
                self.action_btn.blockSignals(False)
                # 使用非阻塞提示
                self.append_system_log("⚠️ 请先选择串口！")
                return

            baud = int(self.baud_combo.currentText())
            params = self._get_serial_params()

            ok, msg = self.worker.open_port(
                port=port,
                baudrate=baud,
                bytesize=params['bytesize'],
                parity=params['parity'],
                stopbits=params['stopbits']
            )

            if ok:
                self.action_btn.setText("断开")
                self.action_btn.setStyleSheet("")
                # 连接时禁用所有配置控件
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
                self.databit_combo.setEnabled(False)
                self.parity_combo.setEnabled(False)
                self.stopbit_combo.setEnabled(False)

                # 构建连接信息
                parity_name = self.parity_combo.currentText()
                conn_info = f"{port} ({baud},{self.databit_combo.currentText()},{parity_name[0] if parity_name != 'None' else 'N'},{self.stopbit_combo.currentText()})"
                self.append_system_log(f"已连接 {conn_info}")
            else:
                # 连接失败，恢复按钮状态（阻止信号避免递归）
                self.action_btn.blockSignals(True)
                self.action_btn.setChecked(False)
                self.action_btn.setText("打开串口喵")
                self.action_btn.setStyleSheet("")
                self.action_btn.blockSignals(False)

                # 检查是否是权限错误（串口被占用）
                if "被占用" in msg or "拒绝访问" in msg or "PermissionError" in msg:
                    # 使用非阻塞对话框
                    retry_box = QMessageBox(self)
                    retry_box.setWindowTitle("串口连接失败")
                    retry_box.setText(msg)
                    retry_box.setIcon(QMessageBox.Warning)

                    # 添加自定义按钮
                    retry_btn = retry_box.addButton("🔄 重试", QMessageBox.ActionRole)
                    check_btn = retry_box.addButton("🔍 检查占用", QMessageBox.ActionRole)
                    cancel_btn = retry_box.addButton("❌ 取消", QMessageBox.RejectRole)

                    # 使用finished信号处理响应（非阻塞）
                    def handle_retry_response(result):
                        clicked = retry_box.clickedButton()
                        if clicked == retry_btn:
                            # 延迟后重试（使用QTimer，非阻塞）
                            QTimer.singleShot(500, lambda: self._retry_connection(port, baud, params))
                        elif clicked == check_btn:
                            # 检查哪些程序可能占用了串口
                            self.check_port_usage(port)

                    retry_box.finished.connect(handle_retry_response)
                    retry_box.show()  # 非阻塞显示
                else:
                    # 其他错误使用非阻塞对话框
                    error_box = QMessageBox(self)
                    error_box.setWindowTitle("连接失败")
                    error_box.setText(msg)
                    error_box.setIcon(QMessageBox.Critical)
                    error_box.show()  # 非阻塞显示
        else:
            # === 断开串口 ===
            # 立即更新UI，提升用户体验（不等待资源释放）
            self.action_btn.setText("打开串口喵")
            self.action_btn.setStyleSheet("")
            self.action_btn.setEnabled(False)  # 暂时禁用按钮，防止重复点击

            # 停止定时发送
            if self.check_timer_send.isChecked():
                self.check_timer_send.setChecked(False)
                self.toggle_auto_send()

            # 断开时启用所有配置控件
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.databit_combo.setEnabled(True)
            self.parity_combo.setEnabled(True)
            self.stopbit_combo.setEnabled(True)

            self.append_system_log("正在断开连接，释放串口资源...")

            # 使用QTimer异步执行资源释放，避免阻塞UI
            QTimer.singleShot(0, self._async_close_port)

    def _async_close_port(self):
        """异步关闭串口（真正非阻塞版）"""
        # 步骤1：立即关闭串口（现在是非阻塞的，<10ms）
        self.worker.close_port()

        # 步骤2：延迟后刷新端口列表并恢复UI
        # 虽然close_port是非阻塞的，但系统需要时间释放资源
        # 给Windows系统500ms时间来完全释放串口资源
        QTimer.singleShot(500, self._finish_close_port)

    def _finish_close_port(self):
        """完成串口关闭流程的最后步骤（立即恢复）"""
        # 刷新端口列表（确保端口重新可用）
        self.smart_scan_ports()

        # 立即恢复连接按钮
        self.action_btn.setEnabled(True)

        self.append_system_log("✅ 端口已释放，可立即重新连接")

    def _retry_connection(self, port, baud, params):
        """重试连接（非阻塞）"""
        self.action_btn.blockSignals(True)
        self.action_btn.setChecked(True)
        self.action_btn.blockSignals(False)
        # 手动调用连接逻辑
        self.toggle_connection(True)

    def check_port_usage(self, port):
        """检查串口占用情况"""
        try:
            import psutil

            info_text = f"正在检查串口 {port} 的占用情况...\n\n"
            info_text += "🔍 可能占用串口的常见程序：\n\n"

            # 常见的可能占用串口的程序
            common_programs = [
                "arduino", "putty", "teraterm", "minicom", "screen",
                "serial", "com", "sscom", "xcom", "cutecom",
                "papercat", "python", "java"
            ]

            found_programs = []
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    proc_name = proc.info['name'].lower()
                    for program in common_programs:
                        if program in proc_name:
                            found_programs.append(f"• {proc.info['name']} (PID: {proc.info['pid']})")
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if found_programs:
                info_text += "\n".join(found_programs)
                info_text += "\n\n💡 建议：关闭以上程序后重试"
            else:
                info_text += "未检测到常见的串口程序\n\n"
                info_text += "💡 其他可能的原因：\n"
                info_text += "• 设备驱动异常\n"
                info_text += "• 上次连接未正常关闭\n"
                info_text += "• 需要管理员权限\n\n"
                info_text += "建议：拔出设备后重新插入"

            QMessageBox.information(self, "串口占用检查", info_text)

        except ImportError:
            # 如果没有psutil模块，提供基本建议
            info_text = f"⚠️ 串口 {port} 被占用\n\n"
            info_text += "请手动检查并关闭以下可能的程序：\n\n"
            info_text += "• Arduino IDE\n"
            info_text += "• PuTTY / SecureCRT\n"
            info_text += "• 串口调试助手\n"
            info_text += "• 其他 PaperCat 实例\n"
            info_text += "• 其他串口监控工具\n\n"
            info_text += "💡 或者：拔出设备后重新插入"

            QMessageBox.information(self, "串口占用提示", info_text)
        except Exception as e:
            QMessageBox.warning(self, "检查失败", f"无法检查串口占用情况\n\n{str(e)}")

    def send_data(self):
        """发送数据（优化错误处理）"""
        if not self.worker.running:
            return

        raw_text = self.input_box.currentText().strip()
        if not raw_text:
            return

        # 保存到历史记录
        if self.input_box.findText(raw_text) == -1:
            self.input_box.addItem(raw_text)
            # 限制历史记录数量
            if self.input_box.count() > 20:
                self.input_box.removeItem(0)

        try:
            tx_mode = self.combo_tx_mode.currentIndex()
            data_bytes = self._prepare_send_data(raw_text, tx_mode)

            if data_bytes and self.worker.send(data_bytes):
                self.tx_count += len(data_bytes)
                self.update_counters()
                if self.tabs.currentIndex() == 0:
                    disp = data_bytes.hex(' ').upper() if tx_mode == 2 else raw_text
                    self._append_terminal_html(
                        f"<span class='tx-line'><b>TX:</b> {disp}</span>",
                        Qt.AlignLeft
                    )
            else:
                self._append_terminal_html(
                    f"<div style='color:#ff7675; text-align: left;'>⚠️ 发送失败：串口未响应</div>",
                    Qt.AlignLeft
                )
        except ValueError as e:
            self._append_terminal_html(
                f"<div style='color:red; text-align: left;'>❌ 格式错误: {e}</div>",
                Qt.AlignLeft
            )
            self.check_timer_send.setChecked(False)
        except Exception as e:
            self._append_terminal_html(
                f"<div style='color:red; text-align: left;'>❌ 发送失败: {e}</div>",
                Qt.AlignLeft
            )
            self.check_timer_send.setChecked(False)

    def _prepare_send_data(self, text, mode):
        """准备发送数据"""
        if mode == 2:  # HEX 模式
            clean_hex = text.replace(" ", "").replace("\n", "").replace("\r", "")
            if not all(c in '0123456789ABCDEFabcdef' for c in clean_hex):
                raise ValueError("HEX 格式错误，只能包含 0-9, A-F")
            return bytes.fromhex(clean_hex)
        else:  # 文本模式
            content = text
            if self.check_add_newline.isChecked():
                content += "\r\n"
            encoding = 'utf-8' if mode == 0 else 'gbk'
            return content.encode(encoding, errors='replace')

    def toggle_auto_send(self):
        if self.check_timer_send.isChecked():
            self.auto_send_timer.start(self.spin_timer.value())
            self.input_box.setEnabled(False)
        else:
            self.auto_send_timer.stop()
            self.input_box.setEnabled(True)

    def update_counters(self):
        """更新计数显示（同步两个工具栏）"""
        self.lbl_rx_cnt.setText(f"RX: {self.rx_count}")
        self.lbl_tx_cnt.setText(f"TX: {self.tx_count}")
        # 同步示波器工具栏的计数显示
        if hasattr(self, 'lbl_rx_cnt_osc'):
            self.lbl_rx_cnt_osc.setText(f"RX: {self.rx_count}")
            self.lbl_tx_cnt_osc.setText(f"TX: {self.tx_count}")

    def reset_counters(self):
        self.rx_count = 0
        self.tx_count = 0
        self.update_counters()

    def clear_logs(self):
        """清空日志和波形数据"""
        self.display_area.clear()
        # 清空文本显示缓冲区
        self._text_display_buffer = ""
        # 清空所有波形缓冲区
        for buffer in self.plot_data_buffer:
            buffer.clear()
        # 清空时间缓冲区
        for time_buf in self.time_buffer:
            time_buf.clear()
        # 重置数据开始时间
        self.data_start_time = None
        # 清空波形显示
        for curve in self.curves:
            curve.setData([])
        # 重置统计数据
        self.channel_stats = {
            'min': [float('inf')] * self.max_channels,
            'max': [float('-inf')] * self.max_channels,
            'sum': [0.0] * self.max_channels,
            'count': [0] * self.max_channels,
            'current': [0.0] * self.max_channels
        }
        # 重置画图计数器
        self.plot_update_counter = 0
        self._last_x_range = None
        self._auto_channel_last_detected = None
        self._auto_channel_stable_count = 0
        self.update_statistics_display()

    # ========== 新增功能方法 ==========

    def update_statistics_display(self):
        """更新统计数据显示"""
        for i in range(min(4, len(self.stat_labels))):
            if self.channel_stats['count'][i] > 0:
                current = self.channel_stats['current'][i]
                min_val = self.channel_stats['min'][i]
                max_val = self.channel_stats['max'][i]
                avg_val = self.channel_stats['sum'][i] / self.channel_stats['count'][i]

                self.stat_labels[i][1].setText(f"{current:.2f}")
                self.stat_labels[i][2].setText(f"{min_val:.2f}")
                self.stat_labels[i][3].setText(f"{max_val:.2f}")
                self.stat_labels[i][4].setText(f"{avg_val:.2f}")
            else:
                for j in range(1, 5):
                    self.stat_labels[i][j].setText("--")

    def _auto_adjust_channel_count(self, detected_count):
        """根据解析数据自动匹配通道数量"""
        if detected_count <= 0:
            return

        new_count = min(detected_count, self.max_channels)
        if new_count == self.current_channel_count:
            self._auto_channel_last_detected = new_count
            self._auto_channel_stable_count = 0
            return

        if self._auto_channel_last_detected == new_count:
            self._auto_channel_stable_count += 1
        else:
            self._auto_channel_last_detected = new_count
            self._auto_channel_stable_count = 1

        threshold = self.auto_channel_up_threshold if new_count > self.current_channel_count else self.auto_channel_down_threshold
        if self._auto_channel_stable_count < threshold:
            return

        self.current_channel_count = new_count
        self._auto_channel_stable_count = 0

        # 清空超出通道的曲线显示
        for i in range(self.max_channels):
            if i >= self.current_channel_count or not self.channel_visible[i]:
                self.curves[i].setData([], [])

        # 更新图例
        self.plot_widget.plotItem.legend.clear()
        for i in range(self.current_channel_count):
            if self.channel_visible[i]:
                self.plot_widget.plotItem.legend.addItem(self.curves[i], self.channel_names[i])

    def _auto_scale_y_axis(self):
        """Y轴自适应缩放（优化版 - 所有通道统一平面）"""
        all_values = []

        # 收集所有可见通道的数据（只考虑当前启用的通道数量）
        for i in range(min(self.current_channel_count, self.max_channels)):
            if self.channel_visible[i] and len(self.plot_data_buffer[i]) > 0:
                all_values.extend(list(self.plot_data_buffer[i]))

        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)

            # 计算合适的边距
            if max_val != min_val:
                margin = (max_val - min_val) * 0.1  # 上下各留10%边距
            else:
                # 如果所有值相同，设置固定范围
                margin = abs(min_val) * 0.1 if min_val != 0 else 1

            # 设置统一的Y轴范围，所有通道共享同一平面
            self.plot_widget.setYRange(min_val - margin, max_val + margin, padding=0)
        else:
            # 没有数据时，使用默认范围
            self.plot_widget.setYRange(-10, 10, padding=0)

    def _auto_follow_x_axis(self, num_channels):
        """Auto-follow X axis to keep latest data in view."""
        x_min = None
        x_max = None

        for i in range(num_channels):
            if not self.channel_visible[i]:
                continue
            if len(self.time_buffer[i]) == 0:
                continue
            buf = self.time_buffer[i]
            buf_min = buf[0]
            buf_max = buf[-1]
            if x_min is None or buf_min < x_min:
                x_min = buf_min
            if x_max is None or buf_max > x_max:
                x_max = buf_max

        if x_min is None or x_max is None:
            return

        if x_max <= x_min:
            span = self._x_follow_min_span
            new_min = x_min - span
            new_max = x_max + span
        else:
            span = x_max - x_min
            padding = span * self._x_follow_padding_ratio
            new_min = x_min - padding
            new_max = x_max + padding

        last_range = self._last_x_range
        if last_range and abs(new_min - last_range[0]) < 1e-9 and abs(new_max - last_range[1]) < 1e-9:
            return

        self.plot_widget.setXRange(new_min, new_max, padding=0)
        self._last_x_range = (new_min, new_max)

    def toggle_x_follow(self):
        """切换X轴自动跟随（同步两个按钮）"""
        sender = self.sender()
        is_checked = sender.isChecked() if sender else self.btn_x_follow.isChecked()

        self.btn_x_follow.setChecked(is_checked)
        if hasattr(self, 'btn_x_follow_osc'):
            self.btn_x_follow_osc.setChecked(is_checked)

        self.auto_follow_x = is_checked
        if is_checked:
            self._last_x_range = None
            self._auto_follow_x_axis(min(self.current_channel_count, self.max_channels))
            self.append_system_log("X轴自动跟随已开启")
        else:
            self.append_system_log("X轴自动跟随已关闭（可手动缩放）")

    def toggle_y_auto_scale(self):
        """切换Y轴自适应（同步两个按钮）"""
        # 获取触发者的状态
        sender = self.sender()
        is_checked = sender.isChecked() if sender else self.btn_y_auto.isChecked()

        # 同步两个按钮的状态
        self.btn_y_auto.setChecked(is_checked)
        self.btn_y_auto_osc.setChecked(is_checked)

        if is_checked:
            self._auto_scale_y_axis()
            self.append_system_log("Y轴自适应已开启")
        else:
            self.append_system_log("Y轴自适应已关闭")

    def on_plot_interval_changed(self, value):
        """画图间隔改变处理（已废弃，保留兼容性）"""
        pass

    def on_time_resolution_changed(self, index):
        """X轴时间分辨率改变处理"""
        time_values = [1, 5, 10, 20, 50, 100, 200, 500, 1000]  # 毫秒
        self.time_resolution = time_values[index]

        # 更新X轴标签
        if self.time_resolution >= 1000:
            unit_text = "时间 (秒)"
        else:
            unit_text = "时间 (毫秒)"

        self.plot_widget.setLabel('bottom', unit_text)
        self.append_system_log(f"X轴时间分辨率已设置为 {self.time_resolution_combo.currentText()}")

    def auto_center_waveform(self):
        """自动对齐波形到屏幕中心"""
        # 收集所有可见通道的数据
        all_y_values = []
        all_x_values = []

        for i in range(min(self.current_channel_count, self.max_channels)):
            if self.channel_visible[i] and len(self.plot_data_buffer[i]) > 0:
                all_y_values.extend(list(self.plot_data_buffer[i]))
                all_x_values.extend(list(self.time_buffer[i]))

        if not all_y_values or not all_x_values:
            self.append_system_log("⚠️ 没有可见数据，无法对齐")
            return

        # 计算Y轴范围
        y_min = min(all_y_values)
        y_max = max(all_y_values)
        y_margin = (y_max - y_min) * 0.15 if y_max != y_min else abs(y_min) * 0.15 if y_min != 0 else 1

        # 计算X轴范围
        x_min = min(all_x_values)
        x_max = max(all_x_values)
        x_margin = (x_max - x_min) * 0.05 if x_max != x_min else 1

        # 设置显示范围（居中显示，留出边距）
        self.plot_widget.setYRange(y_min - y_margin, y_max + y_margin, padding=0)
        self.plot_widget.setXRange(x_min - x_margin, x_max + x_margin, padding=0)

        self.append_system_log(f"✓ 波形已自动对齐到屏幕中心")

    def toggle_recording(self):
        """切换录制状态（同步两个录制按钮）"""
        # 获取触发者的状态
        sender = self.sender()
        is_checked = sender.isChecked() if sender else self.btn_record.isChecked()

        # 同步两个按钮的状态
        self.btn_record.setChecked(is_checked)
        self.btn_record_osc.setChecked(is_checked)

        if is_checked:
            self.is_recording = True
            self.record_data = deque(maxlen=self.max_record_points) if self.max_record_points else []
            self.record_start_time = datetime.datetime.now().timestamp()
            self.btn_record.setText("⏹ 停止录制")
            self.btn_record.setStyleSheet("background-color: #ff7675; color: white;")
            self.btn_record_osc.setText("⏹ 停止录制")
            self.btn_record_osc.setStyleSheet("background-color: #ff7675; color: white;")
            self.append_system_log("开始录制数据...")
        else:
            self.is_recording = False
            self.btn_record.setText("⏺ 开始录制")
            self.btn_record.setStyleSheet("")
            self.btn_record_osc.setText("⏺ 开始录制")
            self.btn_record_osc.setStyleSheet("")
            count = len(self.record_data)
            self.append_system_log(f"录制停止，共 {count} 个数据点")

    def export_to_csv(self):
        """导出数据到CSV文件"""
        if not self.record_data:
            QMessageBox.warning(self, "提示", "没有录制的数据可导出！\n请先开始录制数据。")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "导出CSV文件",
            f"data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV文件 (*.csv)"
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)

                    # 写入表头
                    header = ['时间(s)'] + [f'{self.channel_names[i]}' for i in range(self.max_channels)]
                    writer.writerow(header)

                    # 写入数据
                    for record in self.record_data:
                        row = [f"{record['time']:.3f}"]
                        values = record['values']
                        for i in range(self.max_channels):
                            if i < len(values):
                                row.append(f"{values[i]:.6f}")
                            else:
                                row.append("")
                        writer.writerow(row)

                QMessageBox.information(self, "成功", f"已导出 {len(self.record_data)} 条数据到:\n{filename}")
                self.append_system_log(f"数据已导出到 {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def send_quick_command(self, index):
        """发送快捷命令"""
        if not self.worker.running:
            QMessageBox.warning(self, "提示", "请先连接串口！")
            return

        command = self.quick_edits[index].text().strip()
        if not command:
            QMessageBox.warning(self, "提示", f"快捷指令{index+1}为空！")
            return

        # 临时保存当前输入框内容
        original_text = self.input_box.currentText()
        self.input_box.setCurrentText(command)
        self.send_data()
        # 恢复原内容
        self.input_box.setCurrentText(original_text)

    def save_config(self):
        """保存配置到文件"""
        config = {
            'serial': {
                'baudrate': self.baud_combo.currentText(),
                'databit': self.databit_combo.currentText(),
                'parity': self.parity_combo.currentText(),
                'stopbit': self.stopbit_combo.currentText(),
            },
            'protocol': {
                'parse_mode': self.parse_mode_combo.currentIndex(),
                'regex_pattern': self.txt_pattern.text(),
            },
            'quick_commands': [edit.text() for edit in self.quick_edits],
            'send_history': [self.input_box.itemText(i) for i in range(self.input_box.count())],
        }

        filename, _ = QFileDialog.getSaveFileName(
            self, "保存配置", "config.json", "JSON文件 (*.json)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", "配置已保存！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

    def load_config(self):
        """从文件加载配置"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载配置", "", "JSON文件 (*.json)"
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 应用串口配置
                if 'serial' in config:
                    self.baud_combo.setCurrentText(config['serial'].get('baudrate', '115200'))
                    self.databit_combo.setCurrentText(config['serial'].get('databit', '8'))
                    self.parity_combo.setCurrentText(config['serial'].get('parity', 'None'))
                    self.stopbit_combo.setCurrentText(config['serial'].get('stopbit', '1'))

                # 应用协议配置
                if 'protocol' in config:
                    self.parse_mode_combo.setCurrentIndex(config['protocol'].get('parse_mode', 0))
                    self.txt_pattern.setText(config['protocol'].get('regex_pattern', ''))

                # 应用快捷命令
                if 'quick_commands' in config:
                    for i, cmd in enumerate(config['quick_commands']):
                        if i < len(self.quick_edits):
                            self.quick_edits[i].setText(cmd)

                # 应用发送历史
                if 'send_history' in config:
                    self.input_box.clear()
                    self.input_box.addItems(config['send_history'])

                QMessageBox.information(self, "成功", "配置已加载！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败:\n{str(e)}")

    def open_channel_config(self):
        """打开通道配置对话框（优化版 - 防止重复弹窗）"""
        # 检查对话框是否已存在且可见
        if self.channel_config_dialog is not None and self.channel_config_dialog.isVisible():
            # 如果已经打开，将其置于前台并激活
            self.channel_config_dialog.raise_()
            self.channel_config_dialog.activateWindow()
            return

        # 创建新的配置对话框
        current_config = {
            'channel_count': self.current_channel_count,
            'channel_names': self.channel_names.copy(),
            'channel_visible': self.channel_visible.copy(),
            'channel_colors': self.channel_colors.copy()
        }

        self.channel_config_dialog = ChannelConfigDialog(self, current_config)
        self.channel_config_dialog.config_changed.connect(self.apply_channel_config)
        self.channel_config_dialog.show()

    def apply_channel_config(self, config):
        """应用通道配置"""
        old_count = self.current_channel_count
        self.current_channel_count = config['channel_count']
        self.channel_names = config['channel_names']
        self.channel_visible = config['channel_visible']
        self.channel_colors = config['channel_colors']

        # 如果通道数量变化，需要重新创建波形曲线
        if old_count != self.current_channel_count:
            self.rebuild_plot_curves()

        # 更新现有曲线的属性
        for i in range(self.max_channels):
            if i < len(self.curves):
                # 更新曲线名称和颜色
                self.curves[i].opts['name'] = self.channel_names[i]
                pen = pg.mkPen(color=self.channel_colors[i], width=2)
                self.curves[i].setPen(pen)

                # 根据可见性更新显示
                if i < self.current_channel_count and self.channel_visible[i]:
                    if len(self.plot_data_buffer[i]) > 0:
                        self.curves[i].setData(list(self.plot_data_buffer[i]))
                else:
                    self.curves[i].setData([])

        # 更新图例
        self.plot_widget.plotItem.legend.clear()
        for i in range(self.current_channel_count):
            if self.channel_visible[i]:
                self.plot_widget.plotItem.legend.addItem(self.curves[i], self.channel_names[i])

        self.append_system_log(f"通道配置已更新：{self.current_channel_count}个通道")

    def rebuild_plot_curves(self):
        """重建波形曲线"""
        # 清除所有曲线
        self.plot_widget.clear()
        self.curves = []

        # 重新创建图例
        self.plot_widget.addLegend()

        # 创建新的曲线
        for i in range(self.max_channels):
            pen = pg.mkPen(color=self.channel_colors[i], width=2)
            curve = self.plot_widget.plot(name=self.channel_names[i], pen=pen)
            self.curves.append(curve)

        # 恢复数据
        for i in range(min(self.current_channel_count, len(self.plot_data_buffer))):
            if self.channel_visible[i] and len(self.plot_data_buffer[i]) > 0:
                self.curves[i].setData(list(self.plot_data_buffer[i]))

    def _apply_scaled_stylesheet(self, scale):
        """应用缩放后的样式表（响应式设计）"""
        # 限制缩放范围
        scale = max(0.7, min(1.3, scale))  # 0.7 - 1.3 倍

        # 计算缩放后的尺寸
        font_size = int(self.base_font_size * scale)
        font_size_large = int(14 * scale)
        padding_small = int(5 * scale)
        padding_medium = int(10 * scale)
        padding_button = f"{int(6 * scale)}px {int(12 * scale)}px"
        padding_tab = f"{int(8 * scale)}px {int(20 * scale)}px"
        border_radius = int(6 * scale)
        min_height = int(22 * scale)
        handle_width = int(4 * scale)

        # 生成动态样式表
        stylesheet = f"""
            QMainWindow {{ background-color: #f5f7fb; }}
            QWidget {{
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: {font_size}px;
                color: #2d3436;
            }}
            QTextBrowser {{
                background-color: rgba(255, 255, 255, 0.85);
                border: 1px solid #e1e4e8;
                border-radius: {border_radius}px;
                padding: {padding_medium}px;
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid #dcdde1;
                border-radius: {int(4 * scale)}px;
                padding: {int(4 * scale)}px {int(8 * scale)}px;
                min-height: {int(32 * scale)}px;
                max-height: {int(32 * scale)}px;
            }}
            QLabel {{
                font-size: {font_size}px;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid #dcdde1;
                border-radius: {int(4 * scale)}px;
                padding: {padding_button};
                color: #2d3436;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{ background-color: rgba(241, 242, 246, 0.95); border-color: #a29bfe; color: #6c5ce7; }}

            QPushButton#pauseBtn {{
                border: 1px solid #ff9f43; color: #ff9f43; background-color: rgba(255, 255, 255, 0.9); font-weight: bold;
            }}
            QPushButton#pauseBtn:hover {{ background-color: rgba(255, 242, 230, 0.95); }}
            QPushButton#pauseBtn:checked {{ background-color: rgba(255, 159, 67, 0.9); color: white; border: 1px solid #e58e26; }}

            QPushButton#primaryBtn {{
                background-color: rgba(162, 155, 254, 0.9); color: white; border: none; font-weight: bold;
                font-size: {font_size}px;
            }}
            QPushButton#primaryBtn:hover {{ background-color: rgba(108, 92, 231, 0.95); }}
            QPushButton#primaryBtn:checked {{ background-color: rgba(255, 118, 117, 0.9); }}

            QPushButton#sendBigBtn {{
                background-color: rgba(9, 132, 227, 0.9); color: white; border: none; font-weight: bold;
                font-size: {font_size_large}px;
            }}
            QPushButton#sendBigBtn:hover {{ background-color: rgba(116, 185, 255, 0.95); }}

            QGroupBox {{
                font-weight: bold; border: 1px solid rgba(225, 228, 232, 0.6); border-radius: {border_radius}px;
                margin-top: {padding_medium}px; padding: {int(18 * scale)}px {int(12 * scale)}px {int(12 * scale)}px {int(12 * scale)}px;
                background-color: rgba(250, 250, 250, 0.75);
                font-size: {font_size}px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: {padding_medium}px; padding: 0 {padding_small}px; color: #636e72; }}

            QFrame {{
                background-color: rgba(255, 255, 255, 0.85);
            }}

            QSplitter::handle {{ background-color: rgba(223, 230, 233, 0.8); }}
            QSplitter::handle:horizontal {{ width: {handle_width}px; }}
            QSplitter::handle:vertical {{ height: {handle_width}px; }}
            QSplitter::handle:hover {{ background-color: rgba(162, 155, 254, 0.8); }}

            QTabWidget::pane {{ border: 1px solid rgba(225, 228, 232, 0.6); background: rgba(255, 255, 255, 0.85); border-radius: {padding_small}px;}}
            QTabBar::tab {{
                background: rgba(223, 230, 233, 0.8); padding: {padding_tab};
                border-top-left-radius: {padding_small}px; border-top-right-radius: {padding_small}px;
                margin-right: 2px;
                font-size: {font_size}px;
            }}
            QTabBar::tab:selected {{ background: rgba(9, 132, 227, 0.9); color: white; }}

            QCheckBox {{ font-size: {font_size}px; background: transparent; }}
        """

        self.setStyleSheet(stylesheet)
        self.current_scale = scale

    def _update_scaled_styles(self):
        """更新缩放样式（定时器触发）"""
        current_width = self.width()
        current_height = self.height()

        # 计算缩放比例（取宽度和高度的平均值）
        scale_x = current_width / self.base_width
        scale_y = current_height / self.base_height
        new_scale = (scale_x + scale_y) / 2

        # 如果变化超过阈值，才更新样式
        if abs(new_scale - self.last_scale_update) > self.scale_threshold:
            self._apply_scaled_stylesheet(new_scale)
            self.last_scale_update = new_scale

    def resizeEvent(self, event):
        """窗口大小改变时更新样式（响应式版本）"""
        super().resizeEvent(event)

        # 延迟更新样式表（避免拖动时频繁更新）
        if hasattr(self, 'style_update_timer'):
            self.style_update_timer.stop()
            self.style_update_timer.start(400)  # 400ms 后更新样式（原300ms）


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaperCatSerial()
    window.show()
    sys.exit(app.exec())
