import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
    DATA_DIR = os.path.join(os.path.dirname(EXE_DIR), 'DATA')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'DATA')

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QFileDialog,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon

from data_parser import parse_read_excel, parse_fans_excel
from pages.read_overview import ReadOverviewPage
from pages.fans_overview import FansOverviewPage


COLORS = {
    'sidebar_bg':     '#1B2332',
    'sidebar_active': '#2A3A50',
    'sidebar_text':   '#8899AA',
    'sidebar_active_text': '#FFFFFF',
    'content_bg':     '#F0F2F5',
    'card_bg':        '#FFFFFF',
    'primary':        '#3B82F6',
    'text_dark':      '#1F2937',
    'text_secondary': '#6B7280',
    'border':         '#E5E7EB',
    'success':        '#10B981',
    'warning':        '#F59E0B',
    'danger':         '#EF4444',
}

CJK = "Microsoft YaHei"


def make_icon(char, color="#3B82F6", size=32):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.setPen(QColor("white"))
    p.setFont(QFont(CJK, int(size * 0.45), QFont.Bold))
    p.drawText(QRect(0, 0, size, size), Qt.AlignCenter, char)
    p.end()
    return pm


class SidebarButton(QPushButton):
    def __init__(self, text, icon_char, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(make_icon(icon_char, size=20))
        self.setIconSize(QSize(20, 20))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['sidebar_text']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-family: "{CJK}";
                padding: 0 12px 0 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {COLORS['sidebar_active']};
                color: {COLORS['sidebar_active_text']};
            }}
            QPushButton:checked {{
                background: {COLORS['sidebar_active']};
                color: {COLORS['sidebar_active_text']};
            }}
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WeChat Data Analyzer")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)
        self.read_data = None
        self.fans_data = None

        # Set window icon — prefer .ico for taskbar, fallback to .png
        self.app_icon = None
        for ico_name in ['logo.ico', 'logo.png']:
            ico_path = os.path.join(BASE_DIR, ico_name)
            if os.path.exists(ico_path):
                self.app_icon = QIcon(ico_path)
                self.setWindowIcon(self.app_icon)
                break

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"QFrame {{ background: {COLORS['sidebar_bg']}; border: none; }}")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(16, 20, 16, 20)
        sb.setSpacing(4)

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        icon_label = QLabel()
        logo_path = os.path.join(BASE_DIR, 'logo.png')
        if os.path.exists(logo_path):
            logo_pm = QPixmap(logo_path)
            icon_label.setPixmap(logo_pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_label.setPixmap(make_icon("W", "#3B82F6", 48))
        icon_label.setFixedSize(48, 48)
        logo_row.addWidget(icon_label)
        title = QLabel("Data Analyzer")
        title.setStyleSheet(f"color: white; font-size: 17px; font-weight: bold; font-family: '{CJK}';")
        logo_row.addWidget(title)
        logo_row.addStretch()
        sb.addLayout(logo_row)

        sub = QLabel("WeChat Official Account")
        sub.setStyleSheet(f"color: {COLORS['sidebar_text']}; font-size: 11px; font-family: '{CJK}'; padding: 0 0 16px 46px;")
        sb.addWidget(sub)

        # Import button
        self.btn_load = QPushButton("  Import Data")
        self.btn_load.setFixedHeight(44)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setIcon(make_icon("+", "#FFFFFF", 20))
        self.btn_load.setIconSize(QSize(18, 18))
        self.btn_load.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']}; color: white; border: none;
                border-radius: 8px; font-size: 13px; font-family: "{CJK}"; font-weight: bold;
            }}
            QPushButton:hover {{ background: #2563EB; }}
        """)
        self.btn_load.clicked.connect(self.load_data)
        sb.addWidget(self.btn_load)
        sb.addSpacing(16)

        self.btn_read = SidebarButton("  Read Analysis", "R")
        self.btn_fans = SidebarButton("  Fans Analysis", "F")
        self.btn_read.clicked.connect(lambda: self.switch_page(0))
        self.btn_fans.clicked.connect(lambda: self.switch_page(1))
        sb.addWidget(self.btn_read)
        sb.addWidget(self.btn_fans)
        sb.addStretch()

        ver = QLabel("v1.1")
        ver.setStyleSheet(f"color: #556677; font-size: 10px; font-family: '{CJK}';")
        sb.addWidget(ver)
        main_layout.addWidget(sidebar)

        # Content
        content = QFrame()
        content.setStyleSheet(f"QFrame {{ background: {COLORS['content_bg']}; border: none; }}")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 24, 28, 24)

        self.header = QLabel("Welcome to Data Analyzer")
        self.header.setStyleSheet(f"""
            font-size: 22px; font-weight: bold; color: {COLORS['text_dark']};
            font-family: "{CJK}"; padding: 4px 0 12px 0;
        """)
        cl.addWidget(self.header)

        self.stack = QStackedWidget()
        self.page_read = ReadOverviewPage(COLORS)
        self.page_fans = FansOverviewPage(COLORS)
        self.stack.addWidget(self.page_read)
        self.stack.addWidget(self.page_fans)
        cl.addWidget(self.stack)
        main_layout.addWidget(content)

        self.btn_read.setChecked(True)

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        self.btn_read.setChecked(idx == 0)
        self.btn_fans.setChecked(idx == 1)
        headers = [
            "Read Analysis  -  Overview",
            "Fans Analysis  -  Overview",
        ]
        self.header.setText(headers[idx])

    def load_data(self):
        start_dir = DATA_DIR if os.path.isdir(DATA_DIR) else os.path.expanduser('~')
        folder = QFileDialog.getExistingDirectory(self, "Select Data Folder", start_dir)
        if not folder:
            return

        read_files = []
        fans_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                fl = f.lower()
                if not fl.endswith(('.xls', '.xlsx')):
                    continue
                if 'fans' in root.lower() or 'follow' in root.lower() or 'fans' in fl or 'follow' in fl:
                    fans_files.append(full)
                else:
                    read_files.append(full)

        if read_files:
            self.read_data = parse_read_excel(read_files)
            self.page_read.update_data(self.read_data)
            self.switch_page(0)
        if fans_files:
            self.fans_data = parse_fans_excel(fans_files)
            self.page_fans.update_data(self.fans_data)
            self.switch_page(1)

        if not read_files and not fans_files:
            self.header.setText("No valid data files found")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(f"""
        * {{ font-family: "{CJK}", "Segoe UI", sans-serif; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ width: 6px; background: transparent; }}
        QScrollBar::handle:vertical {{ background: #D1D5DB; border-radius: 3px; min-height: 30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
