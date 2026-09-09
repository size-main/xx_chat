from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QPoint, QSize, QRect
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QToolButton, QHBoxLayout, QMessageBox, QStyle, QStyleOption, QGraphicsDropShadowEffect, QLabel
from PyQt6.QtGui import QMouseEvent, QIcon, QPixmap, QRegion, QPainter, QBitmap, QImage, QPainterPath, QColor
from PyQt6.QtCore import QObject
from register import RegisterWindow
import res
import ui_load

class load(QMainWindow):
    loadSignal = pyqtSignal(str, str)
    registerSignal = pyqtSignal(str, str)
    def __init__(self):
        super().__init__()
        self.ui = ui_load.Ui_Loading()
        self.ui.setupUi(self)
        self.m_bDragging = False
        self.m_pointDragPos = QPoint()
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(Qt.GlobalColor.gray)
        shadow.setOffset(0, 0)
        self.ShowPass = QToolButton(self.ui.passworldlineEdit)
        self.register_window = RegisterWindow(self)
        self.register_window.registerRequested.connect(lambda userName, password: self.registerSignal.emit(userName, password))
        self.register_window.getloadingWindowRequested.connect(lambda: self.show())

        self.status_label = QLabel(self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #fff7d6; font-size: 12px; background: rgba(0,0,0,0.18); border-radius: 8px; padding: 2px 10px; font-weight: 600;")
        self.status_label.hide()
        self.status_label.setObjectName("reconnectLabel")
        self.status_label.setContentsMargins(0, 0, 0, 0)
        self.status_label.resize(self.width() - 40, 22)
        self.status_label.move(20, self.ui.center_widget.y() + self.ui.center_widget.height() + 24)
        self.status_label.raise_()
        self._reconnect_active = False

        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = 0
        self._spinner_base_text = "正在重连"
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(120)
        self._spinner_timer.timeout.connect(self._tick_spinner)
        self._login_widgets = [
            self.ui.loading,
            self.ui.toolButton,
            self.ui.morebutton,
            self.ui.radioButton,
            self.ui.passworldlineEdit,
            self.ShowPass,
            self.ui.ssidlineEdit,
        ]
        self.initLoadWindow()
        self.ui.passworldlineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.setFixedSize(QSize(307, 469))
        self.ShowPass.clicked.connect(self.showButton_solts_Handler)
        self.ui.radioButton.clicked.connect(lambda: self.ui.loading.setEnabled(self.ui.radioButton.isChecked()))
        self.ui.loading.clicked.connect(self.on_loading_clicked_handler)
        self.ui.toolButton.clicked.connect(self.on_toolButton_clicked_handler)
        self.ui.morebutton.clicked.connect(self.on_register_clicked)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)
        p.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.m_bDragging = True
            self.m_pointDragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (self.m_bDragging and (event.buttons() == Qt.MouseButton.LeftButton)):
            newPos = event.globalPosition().toPoint() - self.m_pointDragPos
            self.move(newPos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.m_bDragging = False
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self._reconnect_active:
            self.status_label.show()
            self.status_label.raise_()
        else:
            self.status_label.hide()

    def _tick_spinner(self):
        if not hasattr(self, "status_label"):
            return
        if self.status_label.isVisible():
            self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
            self.status_label.setText(f"{self._spinner_frames[self._spinner_index]} {self._spinner_base_text}...")
            self.status_label.setStyleSheet("color: #fff7d6; font-size: 12px; background: rgba(0,0,0,0.18); border-radius: 8px; padding: 2px 10px; letter-spacing: 1px; font-weight: 600;")

    def _make_round_pixmap(self, pixmap: QPixmap, size: int = 88):
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if pixmap.isNull():
            painter.end()
            return rounded

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)

        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        offset_x = (size - scaled.width()) // 2
        offset_y = (size - scaled.height()) // 2
        painter.drawPixmap(offset_x, offset_y, scaled)
        painter.end()
        return rounded

    def _set_avatar_gray(self, enabled: bool):
        if not hasattr(self, "_avatar_original_pixmap"):
            return
        pixmap = self._avatar_original_pixmap if enabled else self._to_grayscale(self._avatar_original_pixmap)
        self.ui.portrait.setPixmap(self._make_round_pixmap(pixmap, 88))

    def _to_grayscale(self, pixmap: QPixmap):
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                gray = int((color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000)
                image.setPixelColor(x, y, QColor(gray, gray, gray, color.alpha()))
        return QPixmap.fromImage(image)

    def _set_login_controls_enabled(self, enabled: bool):
        for widget in self._login_widgets:
            widget.setEnabled(enabled)

    def set_reconnect_state(self, reconnecting: bool, message: str = ""):
        if reconnecting == self._reconnect_active and (
            (reconnecting and self.status_label.isVisible()) or
            (not reconnecting and not self.status_label.isVisible())
        ):
            return

        self._reconnect_active = reconnecting
        if reconnecting:
            self._spinner_base_text = "正在重连" if not message else message.replace("...", "")
            self.status_label.setText(f"{self._spinner_frames[0]} {self._spinner_base_text}...")
            self.status_label.setStyleSheet("color: #fff7d6; font-size: 12px; background: rgba(0,0,0,0.18); border-radius: 8px; padding: 2px 10px; letter-spacing: 1px; font-weight: 600;")
            if self.isVisible():
                self.status_label.show()
                self.status_label.raise_()
            if not self._spinner_timer.isActive():
                self._spinner_timer.start()
            self._set_avatar_gray(False)
            self._set_login_controls_enabled(False)
            self.ui.closebutton.setEnabled(True)
        else:
            self.status_label.hide()
            self._spinner_timer.stop()
            self.status_label.setText("")
            self._set_avatar_gray(True)
            self._set_login_controls_enabled(True)
            self.ui.closebutton.setEnabled(True)

    def on_closebutton_clicked(self):
        self.close()

    def on_toolButton_clicked_handler(self):
        QMessageBox.information(self, "提示", "功能正在开发中...")

    def on_register_clicked(self):
        self.hide()
        self.register_window.show()
        self.register_window.raise_()
        self.register_window.activateWindow()

    def register_result(self, success: bool, message: str = ""):
        self.register_window.register_result(success, message)

    def on_loading_clicked_handler(self):
        userName = self.ui.ssidlineEdit.text()
        password = self.ui.passworldlineEdit.text()
        if userName == "" or password == "":
            QMessageBox.warning(self, "提示", "密码和账号不能为空")
            return
        self.loadSignal.emit(userName, password)

    def initLoadWindow(self):
        toolicon = QIcon()
        toolicon.addFile(":/face_setting_btn_normal.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ui.toolButton.setIcon(toolicon)

        closeicon = QIcon()
        closeicon.addFile(":/sysbtn_close_normal.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ui.closebutton.setIcon(closeicon)

        self._avatar_original_pixmap = QPixmap(":/logo.ico")
        self.ui.portrait.setPixmap(self._make_round_pixmap(self._avatar_original_pixmap, 88))
        self.ui.portrait.setScaledContents(False)
        self.ui.portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.portrait.setStyleSheet("background: transparent; border: none;")
        self.ui.portrait.setMask(QRegion())

        ShowBgtnICon = QIcon()
        ShowBgtnICon.addFile(":/eyes.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ShowPass.setIcon(ShowBgtnICon)
        self.ShowPass.setCursor(Qt.CursorShape.CustomCursor)
        self.ShowPass.setStyleSheet("QToolButton{border: 0px;}")

        self.ui.passworldlineEdit.setTextMargins(0, 0, 20, 0)
        layout = QHBoxLayout(self.ui.passworldlineEdit)
        layout.addStretch()
        layout.addWidget(self.ShowPass)
        layout.setContentsMargins(0, 0, 5, 0)
    def showButton_solts_Handler(self):
        ShowBgtnICon = QIcon()
        if (self.ui.passworldlineEdit.echoMode() == QLineEdit.EchoMode.Password): 
            ShowBgtnICon.addFile(":/eyesshow.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
            self.ShowPass.setIcon(ShowBgtnICon)
            self.ui.passworldlineEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            ShowBgtnICon.addFile(":/eyes.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
            self.ShowPass.setIcon(ShowBgtnICon)
            self.ui.passworldlineEdit.setEchoMode(QLineEdit.EchoMode.Password)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = load()
    window.show()
    sys.exit(app.exec())