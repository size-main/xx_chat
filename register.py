from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QIcon, QMouseEvent, QPixmap, QRegion
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
import res
import style

class RegisterWindow(QMainWindow):
    registerRequested = pyqtSignal(str, str)
    getloadingWindowRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_position = None
        self._waiting_for_result = False
        self._spinner_index = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(250)
        self._spinner_timer.timeout.connect(self._update_spinner)
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)
        self._build_ui()
        self.setFixedSize(QSize(307, 500))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

    def _build_ui(self):
        self.setStyleSheet(style.regiseter)
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        title_layout = QHBoxLayout()
        title_layout.addStretch()
        close_button = QToolButton(objectName="closeButton")
        close_button.setText("×")
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        root_layout.addLayout(title_layout)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(30, 8, 30, 30)
        body_layout.setSpacing(12)
        root_layout.addWidget(body)

        portrait = QLabel()
        portrait.setFixedSize(88, 88)
        portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        portrait.setStyleSheet("background: #EAF4FC; border: 4px solid #FFFFFF; border-radius: 44px;")
        portrait.setPixmap(QPixmap(":/logo.ico"))
        portrait.setScaledContents(True)
        portrait.setMask(QRegion(QRect(0, 0, 88, 88), QRegion.RegionType.Ellipse))
        body_layout.addWidget(portrait, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("注册账号")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #167bb5;")
        body_layout.addWidget(title)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("输入账号")
        self.username_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("输入密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("确认密码")
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(self.confirm_edit)

        self.agreement = QCheckBox("已阅读并同意服务协议和隐私保护指引")
        body_layout.addWidget(self.agreement)

        self.register_button = QPushButton("注册", objectName="registerButton")
        self.register_button.clicked.connect(self._on_register_clicked)
        body_layout.addWidget(self.register_button)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        body_layout.addWidget(self.status_label)

        self.back_button = QPushButton("返回登录", objectName="backButton")
        self.back_button.clicked.connect(self._back_to_login)
        body_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def _back_to_login(self):
        self.getloadingWindowRequested.emit()
        self.close()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _on_register_clicked(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "提示", "账号和密码不能为空")
            return
        if password != self.confirm_edit.text():
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return
        if not self.agreement.isChecked():
            QMessageBox.warning(self, "提示", "请先同意服务协议")
            return

        self._waiting_for_result = True
        self._spinner_index = 0
        self.register_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.status_label.setStyleSheet("color: #167bb5;")
        self._update_spinner()
        self._spinner_timer.start()
        self._timeout_timer.start(3000)
        self.registerRequested.emit(username, password)

    def _update_spinner(self):
        if not self._waiting_for_result:
            return
        dots = "." * (self._spinner_index % 4)
        self.status_label.setText(f"正在注册{dots}")
        self._spinner_index += 1

    def _on_timeout(self):
        if not self._waiting_for_result:
            return
        self._waiting_for_result = False
        self._spinner_timer.stop()
        self.register_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self.status_label.setStyleSheet("color: #d9534f;")
        self.status_label.setText("服务器超时，注册失败")

    def register_result(self, success: bool, message: str = ""):
        if not self._waiting_for_result:
            return
        self._waiting_for_result = False
        self._spinner_timer.stop()
        self._timeout_timer.stop()
        self.register_button.setEnabled(True)
        self.back_button.setEnabled(True)
        if success:
            QMessageBox.information(self, "提示", "注册成功")
            self.close()
            self.parent().show()
            self.parent().raise_()
            self.parent().activateWindow()
            return
        self.status_label.setStyleSheet("color: #d9534f;")
        self.status_label.setText(str(message) or "注册失败")
