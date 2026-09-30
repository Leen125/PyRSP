import json
import os
import queue
import random
import sys
import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "3.1.0"
STUDENTS_FILE = "students.txt"
DATA_FILE = "rsp_data.json"

ACCENT = "#7C6CFF"
ACCENT_HOVER = "#9082FF"

COMMENT_TEMPLATES = [
    "{names}，命运的天平今天偏向了你！",
    "恭喜 {names}，被概率之神选中，请开始你的表演。",
    "大数据显示：{names} 今天气场全开。",
    "{names}，躲是躲不掉的，这波属于是天选之人。",
    "算法已算尽一切，答案就是 {names}。",
    "{names}，别看手机了，说的就是你。",
    "量子纠缠完毕，波函数坍缩到 {names} 身上。",
    "{names}，欧气爆棚，建议立刻去买彩票。",
]

# ---------- 离线语音播报（可选依赖 pyttsx3） ----------
try:
    import pyttsx3

    HAS_TTS = True
except ImportError:
    HAS_TTS = False


class TTSSpeaker:
    """单线程队列式 TTS：引擎只初始化一次，避免频繁 init 导致的 COM 冲突。"""

    def __init__(self):
        self._queue = queue.Queue()
        self._engine = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                if self._engine is None:
                    self._engine = pyttsx3.init()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                # 引擎损坏时重建一次，下次再试
                self._engine = None

    def speak(self, text):
        if HAS_TTS:
            self._queue.put(text)

    def stop(self):
        self._queue.put(None)


_tts_speaker = TTSSpeaker() if HAS_TTS else None


def speak_async(text):
    """在后台朗读文本，不阻塞 UI。"""
    if _tts_speaker is not None:
        _tts_speaker.speak(text)

DARK_QSS = f"""
* {{
    font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', 'Segoe UI', sans-serif;
}}
QMainWindow, QDialog {{ background-color: #12141C; }}
QLabel#HeaderTitle {{ color: #FFFFFF; font-size: 24px; font-weight: 700; background: transparent; }}
QLabel#HeaderSub {{ color: #8B90A8; font-size: 12px; background: transparent; }}
QFrame#Card {{
    background-color: #1B1E2B;
    border-radius: 16px;
    border: 1px solid #232739;
}}
QLabel#DisplayName {{ color: #FFFFFF; background: transparent; }}
QLabel#StatusTip {{ color: #8B90A8; font-size: 13px; background: transparent; }}
QLabel#PoolInfo {{ color: #6E7390; font-size: 12px; background: transparent; }}
QPushButton#PrimaryButton {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 13px 28px;
    font-size: 16px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#PrimaryButton:pressed {{ background-color: #6A5BE8; }}
QPushButton#PrimaryButton:disabled {{ background-color: #3A3D52; color: #767A93; }}
QPushButton#GhostButton {{
    background-color: #1B1E2B;
    color: #C9CDE3;
    border: 1px solid #2A2E40;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
}}
QPushButton#GhostButton:hover {{ border-color: {ACCENT}; color: #FFFFFF; }}
QPushButton#GhostButton:disabled {{ color: #4A4E63; }}
QCheckBox {{ color: #C9CDE3; font-size: 13px; spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 9px;
    background: #262A3B; border: 1px solid #343A50;
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QSpinBox {{
    background-color: #1B1E2B; color: #E8EAF2;
    border: 1px solid #2A2E40; border-radius: 10px;
    padding: 8px 10px; font-size: 14px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; }}
QListWidget, QTextEdit, QTableWidget {{
    background-color: #1B1E2B; color: #E8EAF2;
    border: 1px solid #2A2E40; border-radius: 10px;
    padding: 6px; font-size: 14px;
}}
QTableWidget {{ gridline-color: #232739; }}
QHeaderView::section {{
    background-color: #232739; color: #C9CDE3;
    border: none; padding: 6px; font-size: 13px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #343A50; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QMessageBox {{ background-color: #1B1E2B; }}
QMessageBox QLabel {{ color: #E8EAF2; font-size: 14px; }}
QDialog QPushButton {{ background-color: #262A3B; color: #E8EAF2; border: 1px solid #343A50; border-radius: 8px; padding: 7px 16px; font-size: 13px; }}
QDialog QPushButton:hover {{ border-color: {ACCENT}; }}
"""

LIGHT_QSS = f"""
* {{
    font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', 'Segoe UI', sans-serif;
}}
QMainWindow, QDialog {{ background-color: #F4F5FA; }}
QLabel#HeaderTitle {{ color: #1F2333; font-size: 24px; font-weight: 700; background: transparent; }}
QLabel#HeaderSub {{ color: #6B7185; font-size: 12px; background: transparent; }}
QFrame#Card {{
    background-color: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #E6E8F0;
}}
QLabel#DisplayName {{ color: #1F2333; background: transparent; }}
QLabel#StatusTip {{ color: #6B7185; font-size: 13px; background: transparent; }}
QLabel#PoolInfo {{ color: #9BA0B5; font-size: 12px; background: transparent; }}
QPushButton#PrimaryButton {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 13px 28px;
    font-size: 16px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#PrimaryButton:pressed {{ background-color: #6A5BE8; }}
QPushButton#PrimaryButton:disabled {{ background-color: #C9CCDA; color: #F0F1F6; }}
QPushButton#GhostButton {{
    background-color: #FFFFFF;
    color: #4A4F66;
    border: 1px solid #E1E4EE;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
}}
QPushButton#GhostButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#GhostButton:disabled {{ color: #B9BdCd; }}
QCheckBox {{ color: #4A4F66; font-size: 13px; spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 9px;
    background: #EEF0F6; border: 1px solid #D5D9E6;
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QSpinBox {{
    background-color: #FFFFFF; color: #1F2333;
    border: 1px solid #E1E4EE; border-radius: 10px;
    padding: 8px 10px; font-size: 14px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; }}
QListWidget, QTextEdit, QTableWidget {{
    background-color: #FFFFFF; color: #2A2E40;
    border: 1px solid #E1E4EE; border-radius: 10px;
    padding: 6px; font-size: 14px;
}}
QTableWidget {{ gridline-color: #EEF0F6; }}
QHeaderView::section {{
    background-color: #F4F5FA; color: #4A4F66;
    border: none; padding: 6px; font-size: 13px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #D5D9E6; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QMessageBox {{ background-color: #FFFFFF; }}
QMessageBox QLabel {{ color: #2A2E40; font-size: 14px; }}
QDialog QPushButton {{ background-color: #FFFFFF; color: #4A4F66; border: 1px solid #E1E4EE; border-radius: 8px; padding: 7px 16px; font-size: 13px; }}
QDialog QPushButton:hover {{ border-color: {ACCENT}; }}
"""


def get_base_dir():
    """返回 exe/脚本所在目录，用于存放可读写文件（students.txt、rsp_data.json）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """返回资源文件目录，用于读取打包进 exe 的文件（如 icon.png）"""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()
STUDENTS_PATH = os.path.join(BASE_DIR, STUDENTS_FILE)
DATA_PATH = os.path.join(BASE_DIR, DATA_FILE)


def load_students():
    if not os.path.exists(STUDENTS_PATH):
        return []
    try:
        with open(STUDENTS_PATH, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        return []


def save_students(names):
    with open(STUDENTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(names) + "\n")


class AppData:
    """统计数据 / 设置的本地持久化（rsp_data.json）"""

    def __init__(self):
        self.stats = {}          # name -> 被抽中次数
        self.absent = []         # 缺席名单
        self.no_repeat = True    # 防重复模式
        self.weighted = False    # 智能公平加权
        self.tts = True          # 语音播报
        self.dark = True         # 深色主题
        self.history = []        # [(时间, 描述), ...]
        self.load()

    def load(self):
        if not os.path.exists(DATA_PATH):
            return
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.stats = d.get("stats", {})
            self.absent = d.get("absent", [])
            self.no_repeat = d.get("no_repeat", True)
            self.weighted = d.get("weighted", False)
            self.tts = d.get("tts", True)
            self.dark = d.get("dark", True)
            self.history = d.get("history", [])
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "stats": self.stats,
                        "absent": self.absent,
                        "no_repeat": self.no_repeat,
                        "weighted": self.weighted,
                        "tts": self.tts,
                        "dark": self.dark,
                        "history": self.history[-100:],
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError:
            pass


class Card(QDialog):
    """带确认/取消按钮的通用对话框基类"""

    def __init__(self, parent, title, width=420, height=380):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(width, height)

    def add_buttons(self, layout, ok_text, on_ok):
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        ok = QPushButton(ok_text)
        ok.clicked.connect(on_ok)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)


class NameEditorDialog(Card):
    def __init__(self, parent, names):
        super().__init__(parent, "编辑名单", 440, 480)
        layout = QVBoxLayout(self)
        tip = QLabel("每行一个名字，保存后立即生效：")
        layout.addWidget(tip)
        self.editor = QTextEdit()
        self.editor.setPlainText("\n".join(names))
        layout.addWidget(self.editor, 1)
        self.add_buttons(layout, "保存", self.accept)

    def get_names(self):
        return [n.strip() for n in self.editor.toPlainText().splitlines() if n.strip()]


class AbsentDialog(Card):
    def __init__(self, parent, names, absent):
        super().__init__(parent, "缺席管理（勾选为缺席）", 400, 480)
        layout = QVBoxLayout(self)
        self.listw = QListWidget()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name not in absent else Qt.CheckState.Unchecked
            )
            self.listw.addItem(item)
        layout.addWidget(self.listw)
        self.add_buttons(layout, "保存", self.accept)

    def get_present(self):
        return [
            self.listw.item(i).text()
            for i in range(self.listw.count())
            if self.listw.item(i).checkState() == Qt.CheckState.Checked
        ]


class HistoryDialog(Card):
    def __init__(self, parent, history):
        super().__init__(parent, "抽取历史（最近 100 条）", 420, 480)
        layout = QVBoxLayout(self)
        self.listw = QListWidget()
        if history:
            for ts, text in reversed(history):
                self.listw.addItem(f"{ts}   {text}")
        else:
            self.listw.addItem("（暂无记录）")
        layout.addWidget(self.listw)
        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        layout.addLayout(btns)


class StatsDialog(Card):
    def __init__(self, parent, stats):
        super().__init__(parent, "抽取统计", 420, 460)
        layout = QVBoxLayout(self)
        tip = QLabel("被抽中次数排行（公平性一目了然）：")
        layout.addWidget(tip)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["姓名", "次数"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rows = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)
        self.table.setRowCount(len(rows))
        for r, (name, cnt) in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setItem(r, 1, QTableWidgetItem(str(cnt)))
        layout.addWidget(self.table, 1)
        btns = QHBoxLayout()
        reset = QPushButton("清空统计")
        reset.setObjectName("GhostButton")
        self._confirm_reset = False
        reset.clicked.connect(self._on_reset)
        btns.addWidget(reset)
        btns.addStretch(1)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        layout.addLayout(btns)
        self.new_stats = dict(stats)

    def _on_reset(self):
        if self._confirm_reset:
            self.new_stats = {}
            self.accept()
        else:
            self._confirm_reset = True
            self.sender().setText("再点一次确认清空")


class RandomSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = AppData()
        self.students = load_students()
        self.drawn_pool = []  # 防重复模式下已抽中的名单
        self.rolling = False
        self.roll_delay = 40
        self.pending_count = 1

        self.init_ui()
        self.apply_theme()
        self.refresh_status()

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle("随机点人")
        self.setWindowIcon(QIcon(os.path.join(RESOURCE_DIR, "icon.png")))
        self.setMinimumSize(560, 660)
        self.resize(580, 720)

        root = QVBoxLayout()
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # 顶部标题栏
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("随机点人")
        title.setObjectName("HeaderTitle")
        sub = QLabel(f"公平抽取 · 防重复 · v{APP_VERSION}")
        sub.setObjectName("HeaderSub")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch(1)
        self.theme_button = QPushButton("浅色模式")
        self.theme_button.setObjectName("GhostButton")
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        root.addLayout(header)

        # 中央展示卡片
        from PyQt6.QtWidgets import QFrame

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(10)

        self.status_tip = QLabel("按 空格键 或点击下方按钮开始")
        self.status_tip.setObjectName("StatusTip")
        self.status_tip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.display = QLabel("准备就绪")
        self.display.setObjectName("DisplayName")
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setWordWrap(True)
        f = self.display.font()
        f.setPixelSize(48)
        f.setBold(True)
        self.display.setFont(f)
        self.display.setMinimumHeight(140)

        self.pool_info = QLabel("")
        self.pool_info.setObjectName("PoolInfo")
        self.pool_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.comment_label = QLabel("")
        self.comment_label.setObjectName("StatusTip")
        self.comment_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comment_label.setWordWrap(True)
        self.comment_label.setStyleSheet(f"color: {ACCENT};")

        card_layout.addStretch(1)
        card_layout.addWidget(self.status_tip)
        card_layout.addWidget(self.display)
        card_layout.addStretch(1)
        card_layout.addWidget(self.comment_label)
        card_layout.addWidget(self.pool_info)
        root.addWidget(card, 1)

        # 主按钮独占一行，保证文字完整显示
        self.draw_button = QPushButton("开始抽取")
        self.draw_button.setObjectName("PrimaryButton")
        self.draw_button.setMinimumHeight(48)
        self.draw_button.clicked.connect(lambda: self.start_draw(self.count_spin.value()))
        root.addWidget(self.draw_button)

        # 抽取设置行：人数 + 三个开关
        row = QHBoxLayout()
        row.setSpacing(12)
        count_label = QLabel("抽取人数")
        count_label.setObjectName("PoolInfo")
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(1)
        self.count_spin.setFixedHeight(34)
        self.no_repeat_check = QCheckBox("不重复")
        self.no_repeat_check.setChecked(self.data.no_repeat)
        self.no_repeat_check.setToolTip("一轮之内不重复抽中同一人，抽完全员自动开新轮")
        self.no_repeat_check.toggled.connect(self._on_no_repeat_toggle)
        self.weight_check = QCheckBox("智能加权")
        self.weight_check.setChecked(self.data.weighted)
        self.weight_check.setToolTip("AI 公平算法：被抽中越少的学生，下次被抽中的概率越高")
        self.weight_check.toggled.connect(self._on_weighted_toggle)
        self.tts_check = QCheckBox("语音播报")
        self.tts_check.setChecked(self.data.tts and HAS_TTS)
        self.tts_check.setEnabled(HAS_TTS)
        if not HAS_TTS:
            self.tts_check.setToolTip("未安装 pyttsx3，运行 pip install pyttsx3 后重启程序即可启用")
        self.tts_check.toggled.connect(self._on_tts_toggle)
        row.addWidget(count_label)
        row.addWidget(self.count_spin)
        row.addStretch(1)
        row.addWidget(self.no_repeat_check)
        row.addWidget(self.weight_check)
        row.addWidget(self.tts_check)
        root.addLayout(row)

        # 功能按钮行
        tools = QHBoxLayout()
        tools.setSpacing(10)
        for text, slot in (
            ("名单", self.edit_names),
            ("缺席", self.edit_absent),
            ("历史", self.show_history),
            ("统计", self.show_stats),
            ("关于", self.show_about),
        ):
            b = QPushButton(text)
            b.setObjectName("GhostButton")
            b.clicked.connect(slot)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tools.addWidget(b)
        root.addLayout(tools)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        # 滚动动画定时器
        self.roll_timer = QTimer(self)
        self.roll_timer.timeout.connect(self._roll_tick)

        # 结果弹出动画
        self.pop_anim = QVariantAnimation(self)
        self.pop_anim.setDuration(380)
        self.pop_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.pop_anim.setStartValue(0.0)
        self.pop_anim.setEndValue(1.0)
        self.pop_anim.valueChanged.connect(self._on_pop)

        # 快捷键
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.on_space)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.edit_names)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.show_history)

    # ---------- 主题 ----------
    def apply_theme(self):
        app = QApplication.instance()
        app.setStyleSheet(DARK_QSS if self.data.dark else LIGHT_QSS)
        self.theme_button.setText("浅色模式" if self.data.dark else "深色模式")

    def toggle_theme(self):
        self.data.dark = not self.data.dark
        self.data.save()
        self.apply_theme()

    # ---------- 状态 ----------
    def available_pool(self):
        pool = [s for s in self.students if s not in self.data.absent]
        if self.data.no_repeat:
            pool = [s for s in pool if s not in self.drawn_pool]
        return pool

    def refresh_status(self, note=None):
        if not self.students:
            self.display.setText("暂无名单")
            self.status_tip.setText("点击「名单」添加学生（每行一个名字）")
            self.pool_info.setText("")
            self.draw_button.setEnabled(False)
            return
        self.draw_button.setEnabled(True and not self.rolling)
        present = [s for s in self.students if s not in self.data.absent]
        pool = self.available_pool()
        mode = "不重复" if self.data.no_repeat else "自由"
        if self.data.weighted:
            mode += "+智能加权"
        if self.data.no_repeat and not pool and present:
            note = note or "本轮已抽完全员，自动开启新一轮"
            self.drawn_pool = []
            pool = present
        info = f"共 {len(self.students)} 人 · 到场 {len(present)} 人 · 可抽 {len(pool)} 人 · {mode}"
        if self.data.absent:
            info += f" · 缺席 {len(self.data.absent)} 人"
        self.pool_info.setText(info)
        if note:
            self.status_tip.setText(note)

    def _on_no_repeat_toggle(self, checked):
        self.data.no_repeat = checked
        self.drawn_pool = []
        self.data.save()
        self.refresh_status()

    def _on_weighted_toggle(self, checked):
        self.data.weighted = checked
        self.data.save()
        self.refresh_status(
            "智能加权已开启：少被抽中的同学概率更高" if checked else "智能加权已关闭"
        )

    def _on_tts_toggle(self, checked):
        self.data.tts = checked
        self.data.save()

    # ---------- 抽取流程 ----------
    def on_space(self):
        if self.draw_button.isEnabled():
            self.start_draw(self.count_spin.value())

    def start_draw(self, count):
        if self.rolling or not self.students:
            return
        present = [s for s in self.students if s not in self.data.absent]
        if not present:
            self.status_tip.setText("没有可抽的学生，请检查名单或缺席设置")
            return
        self.rolling = True
        self.draw_button.setEnabled(False)
        self.pending_count = count
        self.status_tip.setText("抽取中…")
        self.roll_delay = 40
        self.display.setStyleSheet(f"color: {ACCENT};")
        self.roll_timer.start(self.roll_delay)

    def _roll_tick(self):
        # 名字快速滚动，逐步减速
        candidates = [s for s in self.students if s not in self.data.absent] or self.students
        self.display.setText(random.choice(candidates))
        self.roll_delay = self.roll_delay * 1.15
        if self.roll_delay > 200:
            self.roll_timer.stop()
            self.finish_draw()
        else:
            self.roll_timer.setInterval(int(self.roll_delay))

    def finish_draw(self):
        self.rolling = False
        pool = self.available_pool()
        if self.data.no_repeat and not pool:
            # 一轮抽完，重置
            self.drawn_pool = []
            pool = [s for s in self.students if s not in self.data.absent]

        count = min(self.pending_count, len(pool))
        if count:
            results = self._weighted_sample(pool, count) if self.data.weighted else random.sample(pool, count)
        else:
            results = []
        self.drawn_pool.extend(results)

        now = datetime.now().strftime("%m-%d %H:%M:%S")
        if len(results) == 1:
            self.display.setText(results[0])
            record = f"抽中：{results[0]}"
        elif results:
            self.display.setText("、".join(results))
            record = f"连抽 {len(results)} 人：{'、'.join(results)}"
        else:
            self.display.setText("无")
            record = "无可抽学生"

        for name in results:
            self.data.stats[name] = self.data.stats.get(name, 0) + 1
        self.data.history.append((now, record))
        self.data.save()

        # AI 风格趣味点评
        if results:
            names_text = "、".join(results[:3]) + ("…" if len(results) > 3 else "")
            self.comment_label.setText(random.choice(COMMENT_TEMPLATES).format(names=names_text))
            # 语音播报
            if HAS_TTS and self.data.tts:
                if len(results) == 1:
                    speech = f"抽中，{results[0]}"
                else:
                    speech = f"抽中 {len(results)} 人，" + "，".join(results)
                speak_async(speech)
        else:
            self.comment_label.setText("")

        self.display.setStyleSheet("")
        self.pop_anim.stop()
        self.pop_anim.start()
        self.draw_button.setEnabled(True)
        note = "按 空格键 再来一次" if len(results) == 1 else "按 空格键 再来一组"
        self.refresh_status()

    def _weighted_sample(self, pool, count):
        """智能公平加权抽取：被抽中次数越少，权重越高（w = 1/(1+已抽次数)）"""
        remaining = list(pool)
        picked = []
        for _ in range(count):
            weights = [1.0 / (1 + self.data.stats.get(n, 0)) for n in remaining]
            chosen = random.choices(remaining, weights=weights, k=1)[0]
            picked.append(chosen)
            remaining.remove(chosen)
        return picked

    def _on_pop(self, v):
        f = self.display.font()
        f.setPixelSize(int(30 + 34 * v))
        self.display.setFont(f)

    # ---------- 对话框 ----------
    def edit_names(self):
        dlg = NameEditorDialog(self, self.students)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            names = dlg.get_names()
            if names:
                self.students = names
                save_students(names)
                # 清理已不存在的学生数据
                valid = set(names)
                self.data.stats = {k: v for k, v in self.data.stats.items() if k in valid}
                self.data.absent = [a for a in self.data.absent if a in valid]
                self.drawn_pool = [p for p in self.drawn_pool if p in valid]
                self.data.save()
                self.refresh_status("名单已更新")
            else:
                QMessageBox.warning(self, "提示", "名单不能为空，未保存。")

    def edit_absent(self):
        if not self.students:
            QMessageBox.information(self, "提示", "请先添加名单。")
            return
        dlg = AbsentDialog(self, self.students, self.data.absent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            present = set(dlg.get_present())
            self.data.absent = [s for s in self.students if s not in present]
            self.drawn_pool = [p for p in self.drawn_pool if p not in self.data.absent]
            self.data.save()
            self.refresh_status("缺席名单已更新")

    def show_history(self):
        HistoryDialog(self, self.data.history).exec()

    def show_stats(self):
        dlg = StatsDialog(self, self.data.stats)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.new_stats != self.data.stats:
            self.data.stats = dlg.new_stats
            self.data.save()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于",
            f"<b>随机点人 v{APP_VERSION}</b><br><br>"
            "现代抽取体验：滚动动画 · 连抽 · 防重复<br>"
            "智能加权 · 语音播报 · 缺席管理 · 历史记录 · 统计面板<br><br>"
            "作者：Leen125 & 杰哥<br>"
            "Copyright © 2026 Leen125 & 杰哥<br>"
            "PyQt6 · 一切数据保存在本地",
        )

    def closeEvent(self, event):
        self.data.save()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    selector = RandomSelector()
    selector.show()
    sys.exit(app.exec())
