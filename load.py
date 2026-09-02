from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QPoint, QSize, QRect
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QToolButton, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QMouseEvent, QIcon, QPixmap, QRegion
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
        self.ShowPass = QToolButton(self.ui.passworldlineEdit)
        self.register_window = RegisterWindow(self)
        self.register_window.registerRequested.connect(lambda userName, password: self.registerSignal.emit(userName, password))
        self.register_window.getloadingWindowRequested.connect(lambda: self.show())
        self.initLoadWindow()
        self.ui.passworldlineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.setFixedSize(QSize(307, 469))
        self.ShowPass.clicked.connect(self.showButton_solts_Handler)
        self.ui.radioButton.clicked.connect(lambda: self.ui.loading.setEnabled(self.ui.radioButton.isChecked()))
        self.ui.loading.clicked.connect(self.on_loading_clicked_handler)
        self.ui.toolButton.clicked.connect(self.on_toolButton_clicked_handler)
        self.ui.morebutton.clicked.connect(self.on_register_clicked)

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

        self.ui.portrait.setPixmap(QPixmap(":/logo.ico"))
        self.ui.portrait.setScaledContents(True)
        self.ui.portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.portrait.setMask(QRegion(QRect(0, 0, 88, 88), QRegion.RegionType.Ellipse))
        
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