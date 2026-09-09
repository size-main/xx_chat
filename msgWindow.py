from pathlib import Path
import res
import style
from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget, QApplication, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QFrame, QSplitter, QMenu
)
from history import HistoryWorker


class ChatInput(QTextEdit):
    def __init__(self, chat_window):
        super().__init__()
        self.chat_window = chat_window

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                text = self.toPlainText()
                if text and text.rstrip().endswith('\n'):
                    self.chat_window._send_message()
                    event.accept()
                    return
                if text and not text.endswith('\n'):
                    self.chat_window._send_message()
                    event.accept()
                    return
        super().keyPressEvent(event)


class MsgWindow(QDialog):
    sendMessage = pyqtSignal(str, str)
    sendFileRequested = pyqtSignal(str)
    deleteFriendRequested = pyqtSignal(str)
    userNameChanged = pyqtSignal(str)
    loadHistoryRequested = pyqtSignal(str)
    saveHistoryRequested = pyqtSignal(str, list)
    appendHistoryRequested = pyqtSignal(str, str, str)
    _HISTORY_PAGE_SIZE = 30

    @staticmethod
    def _icon_from_resource(resource_name, fallback_symbol, size=20):
        icon = QIcon(resource_name)
        if not icon.isNull():
            return icon
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#4f8df7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Microsoft YaHei UI", max(10, size - 6)))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, fallback_symbol)
        painter.end()
        return QIcon(pixmap)

    def __init__(self, friend_account=None):
        super().__init__()
        self.friend_account = ""
        self._friend_online_status = {}
        self._friend_online = False
        self._dragging = False
        self._drag_position = None
        self._drag_title_bar = False
        self.user_name = ""
        self.history_path = None
        self._messages = []
        self._history_offset = 0
        self._loading_history = False
        self._history_ready = False
        self._pending_messages = []
        self._selected_file_path = ""
        self._friends = []
        self._history_thread = QThread(self)
        self._history_worker = HistoryWorker()
        self._history_worker.moveToThread(self._history_thread)
        self.userNameChanged.connect(self._history_worker.set_user_name)
        self.loadHistoryRequested.connect(self._history_worker.load_history)
        self._history_worker.historyLoaded.connect(self._on_history_loaded)
        self.saveHistoryRequested.connect(self._history_worker.save_history)
        self.appendHistoryRequested.connect(self._history_worker.append_message)
        self._history_thread.start()
        self.setMinimumSize(680, 480)
        self.resize(820, 620)
        msg_icon = self._icon_from_resource(":/msg.svg", "💬", 32)
        if msg_icon.isNull():
            msg_icon = QIcon(":/logo.ico")
        self.setWindowIcon(msg_icon)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setSizeGripEnabled(False)
        self._build_ui()
        if friend_account is not None:
            self.openMsg(friend_account)

    def set_user_name(self, user_name):
        self.user_name = str(user_name).strip()
        self.userNameChanged.emit(self.user_name)

    def set_friend_list(self, friends):
        self._friends = []
        if isinstance(friends, (list, tuple, set)):
            seen = set()
            for friend in friends:
                friend_name = str(friend).strip()
                if friend_name and friend_name not in seen:
                    self._friends.append(friend_name)
                    seen.add(friend_name)
        if hasattr(self, "friend_list"):
            self.friend_list.clear()
            for friend_name in self._friends:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, friend_name)
                self.friend_list.addItem(item)
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(6, 4, 6, 4)
                row_layout.setSpacing(8)
                icon = QLabel()
                icon.setFixedSize(18, 18)
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon.setStyleSheet("background: #dbeafe; border-radius: 9px; color: #1f3d7a; font-size: 10px;")
                icon.setText("●")
                name_label = QLabel(friend_name)
                name_label.setStyleSheet("font-size: 13px; color: #1f2937;")
                row_layout.addWidget(icon)
                row_layout.addWidget(name_label, 1)
                self.friend_list.setItemWidget(item, row)
            if self.friend_account and self.friend_account in self._friends:
                self._select_friend_item(self.friend_account)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() <= 48:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_title_bar = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton and self._drag_title_bar:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        self._drag_title_bar = False
        super().mouseReleaseEvent(event)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        if hasattr(self, "maximize_button"):
            self.maximize_button.setToolTip("最大化" if not self.isMaximized() else "还原")
            icon = self.style().standardIcon(
                self.style().StandardPixmap.SP_TitleBarNormalButton if self.isMaximized() else self.style().StandardPixmap.SP_TitleBarMaxButton
            )
            self.maximize_button.setIcon(icon)

    def _select_friend_item(self, friend_name):
        if not hasattr(self, "friend_list"):
            return
        for index in range(self.friend_list.count()):
            item = self.friend_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole)).strip() == str(friend_name).strip():
                self.friend_list.setCurrentItem(item)
                break

    def set_always_on_top(self, always_on_top):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.show()
        self.raise_()
        self.activateWindow()
        if hasattr(self, "top_button"):
            self.top_button.setChecked(always_on_top)
            icon = self.style().standardIcon(
                self.style().StandardPixmap.SP_ArrowUp if always_on_top else self.style().StandardPixmap.SP_ArrowDown
            )
            self.top_button.setIcon(icon)
            self.top_button.setToolTip("置顶" if always_on_top else "取消置顶")

    def _show_friend_context_menu(self, position):
        item = self.friend_list.itemAt(position)
        if item is None:
            return
        friend_name = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not friend_name:
            return
        menu = QMenu(self.friend_list)
        delete_action = menu.addAction("删除好友")
        if menu.exec(self.friend_list.mapToGlobal(position)) == delete_action:
            self._friends = [name for name in self._friends if name != friend_name]
            self.friend_list.takeItem(self.friend_list.row(item))
            self.deleteFriendRequested.emit(friend_name)

    def _switch_friend_by_sidebar(self, item):
        if item is None:
            return
        friend_name = str(item.data(Qt.ItemDataRole.UserRole) or item.text() or "").strip()
        if friend_name:
            self.openMsg(friend_name)

    def openMsg(self, friendName):
        self.friend_account = str(friendName).strip()
        if not self.friend_account:
            return
        self.setWindowTitle("与 %s 对话" % self.friend_account)
        self.account_label.setText(self.friend_account)
        self._friend_online = self._friend_online_status.get(self.friend_account, False)
        self._update_online_status()
        self._messages = []
        self._history_offset = 0
        self._history_ready = False
        self._pending_messages = []
        self._clear_messages()
        self.input_box.setEnabled(False)
        if hasattr(self, "friend_list"):
            self._select_friend_item(self.friend_account)
        self.loadHistoryRequested.emit(self.friend_account)
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_ui(self):
        self.setStyleSheet(style.msg_window_style)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.friend_sidebar = QFrame(objectName="friendSidebar")
        self.friend_sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self.friend_sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 12)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("好友列表")
        sidebar_title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.friend_list = QListWidget()
        self.friend_list.setAlternatingRowColors(True)
        self.friend_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.friend_list.customContextMenuRequested.connect(self._show_friend_context_menu)
        self.friend_list.itemClicked.connect(self._switch_friend_by_sidebar)
        sidebar_layout.addWidget(self.friend_list, 1)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(22, 18, 22, 20)
        content_layout.setSpacing(12)

        self.title_bar = QWidget()
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(8)
        self.account_label = QLabel(objectName="friendAccount")
        title_bar_layout.addWidget(self.account_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.online_status_label = QLabel(objectName="onlineStatus")
        title_bar_layout.addWidget(self.online_status_label, alignment=Qt.AlignmentFlag.AlignLeft)
        title_bar_layout.addStretch()
        self.top_button = QPushButton()
        self.top_button.setCheckable(True)
        self.top_button.setToolTip("置顶")
        self.top_button.clicked.connect(lambda checked: self.set_always_on_top(checked))
        self.top_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ArrowDown))
        title_bar_layout.addWidget(self.top_button)
        self.minimize_button = QPushButton()
        self.minimize_button.setToolTip("最小化")
        self.minimize_button.setFixedSize(28, 28)
        self.minimize_button.clicked.connect(self.showMinimized)
        minimize_icon = QIcon(":/None.svg")
        if minimize_icon.isNull():
            minimize_icon = self.style().standardIcon(self.style().StandardPixmap.SP_TitleBarMinButton)
        self.minimize_button.setIcon(minimize_icon)
        title_bar_layout.addWidget(self.minimize_button)
        self.maximize_button = QPushButton()
        self.maximize_button.setToolTip("最大化")
        self.maximize_button.setFixedSize(28, 28)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        maximize_icon = QIcon(":/Open.svg")
        if maximize_icon.isNull():
            maximize_icon = self.style().standardIcon(self.style().StandardPixmap.SP_TitleBarMaxButton)
        self.maximize_button.setIcon(maximize_icon)
        title_bar_layout.addWidget(self.maximize_button)
        self.close_button = QPushButton()
        self.close_button.setToolTip("关闭")
        self.close_button.setFixedSize(28, 28)
        self.close_button.clicked.connect(self.close)
        close_icon = QIcon(":/close.svg")
        if close_icon.isNull():
            close_icon = self.style().standardIcon(self.style().StandardPixmap.SP_TitleBarCloseButton)
        self.close_button.setIcon(close_icon)
        title_bar_layout.addWidget(self.close_button)
        content_layout.addWidget(self.title_bar)

        self.message_area = QScrollArea()
        self.message_area.setWidgetResizable(True)
        self.message_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(8, 8, 8, 8)
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch()
        self.message_area.setWidget(self.message_container)
        self.message_area.verticalScrollBar().valueChanged.connect(self._load_when_scrolled)
        content_layout.addWidget(self.message_area, 1)

        self.input_box = ChatInput(self)
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setFixedHeight(78)
        self.input_box.textChanged.connect(self._update_send_button)
        content_layout.addWidget(self.input_box)

        send_row = QHBoxLayout()
        self.add_file_button = QPushButton("添加文件")
        self.add_file_button.clicked.connect(self._select_file)
        send_row.addWidget(self.add_file_button)
        self.file_label = QLabel()
        self.file_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        send_row.addWidget(self.file_label, 1)
        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress.setValue(0)
        self.file_progress.setFixedWidth(120)
        self.file_progress.hide()
        send_row.addWidget(self.file_progress)
        send_row.addStretch()
        self.send_button = QPushButton("发送", objectName="sendButton")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self._send_message)
        send_row.addWidget(self.send_button)
        content_layout.addLayout(send_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.friend_sidebar)
        splitter.addWidget(content_widget)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        root_layout.addWidget(splitter)

    def set_friend_online(self, friend_name, is_online):
        friend_name = str(friend_name).strip()
        if not friend_name:
            return
        self._friend_online_status[friend_name] = bool(is_online)
        if friend_name == self.friend_account:
            self._friend_online = bool(is_online)
            self._update_online_status()

    def _update_online_status(self):
        status_text = "在线" if self._friend_online else "离线"
        self.online_status_label.setText("●  " + status_text)
        self.online_status_label.setProperty("online", self._friend_online)
        self.online_status_label.style().unpolish(self.online_status_label)
        self.online_status_label.style().polish(self.online_status_label)
        self.online_status_label.update()

    def _update_send_button(self):
        self.send_button.setEnabled(bool(
            self.input_box.toPlainText().strip() or self._selected_file_path
        ))

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if not file_path:
            return
        self._selected_file_path = file_path
        self.file_label.setText(file_path)
        self.file_label.setToolTip(file_path)
        self._update_send_button()

    def set_file_send_progress(self, progress):
        progress = max(0, min(100, int(progress)))
        self.file_progress.setValue(progress)
        self.file_progress.setFormat("发送 %d%%" % progress)
        self.file_progress.show()
        if progress >= 100:
            self.file_label.setText("文件发送完成")

    def _send_message(self):
        message = self.input_box.toPlainText().strip()
        if not message and self._selected_file_path:
            file_path = self._selected_file_path
            self._selected_file_path = ""
            self.file_label.clear()
            self._update_send_button()
            self.add_file_message(file_path, is_self=True)
            self.sendFileRequested.emit(file_path)
            return
        if not message:
            return
        self.add_message(message, is_self=True)
        self._save_message("self", message)
        self.input_box.clear()
        self.sendMessage.emit(self.friend_account, message)

    def _clear_messages(self):
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _on_history_loaded(self, friend_account, messages):
        if str(friend_account).strip() != self.friend_account:
            return
        self._messages = messages if isinstance(messages, list) else []
        self._history_offset = 0
        self._history_ready = True
        self._loading_history = False
        self._load_history_page()
        for message_type, sender, message in self._pending_messages:
            is_self = sender in ("self", self.user_name)
            if message_type == "file":
                self.add_file_message(message, is_self=is_self)
            else:
                self.add_message(message, is_self=is_self)
        self._pending_messages.clear()
        self.input_box.setEnabled(True)

    def _load_when_scrolled(self, value):
        if value <= 0 and self._history_ready:
            self._load_history_page()

    def _load_history_page(self):
        if self._loading_history or self._history_offset >= len(self._messages):
            return
        self._loading_history = True
        start = max(0, len(self._messages) - self._history_offset - self._HISTORY_PAGE_SIZE)
        end = len(self._messages) - self._history_offset
        page = self._messages[start:end]
        old_scroll_value = self.message_area.verticalScrollBar().value()
        old_scroll_maximum = self.message_area.verticalScrollBar().maximum()
        items = page if start == 0 else reversed(page)
        for item in items:
            if not isinstance(item, dict):
                continue
            sender = str(item.get("sender", "")).strip()
            message = item.get("message", "")
            index = self.message_layout.count() - 1 if start == 0 else 0
            is_self = sender in ("self", self.user_name)
            if item.get("type") == "file":
                self._insert_file_bubble(message, is_self=is_self, index=index)
            else:
                self._insert_bubble(message, is_self=is_self, index=index)
        self._history_offset += len(page)
        self._loading_history = False
        if start == 0:
            QTimer.singleShot(0, lambda: self.message_area.verticalScrollBar().setValue(
                self.message_area.verticalScrollBar().maximum()
            ))
        else:
            QTimer.singleShot(0, lambda: self.message_area.verticalScrollBar().setValue(
                old_scroll_value + self.message_area.verticalScrollBar().maximum() - old_scroll_maximum
            ))

    def receive_message(self, friend_name, message):
        friend_name = str(friend_name).strip()
        if friend_name != self.friend_account:
            return
        message = str(message)
        if not self._history_ready:
            self._pending_messages.append(("message", friend_name, message))
            return
        self.add_message(message, is_self=False)

    def receive_file(self, friend_name, file_path):
        friend_name = str(friend_name).strip()
        if friend_name != self.friend_account:
            return
        if not self._history_ready:
            self._pending_messages.append(("file", friend_name, file_path))
            return
        self.add_file_message(file_path, is_self=False)

    def _save_message(self, sender, message):
        if not self.friend_account or not self.user_name:
            return
        self.appendHistoryRequested.emit(
            self.friend_account,
            str(sender),
            str(message),
        )

    def add_message(self, message, is_self=False):
        self._insert_bubble(message, is_self)

    def add_file_message(self, file_path, is_self=False):
        self._insert_file_bubble(file_path, is_self)

    def _insert_bubble(self, message, is_self=False, index=None):
        bubble = QLabel(str(message))
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(340)
        if is_self:
            bubble.setStyleSheet(
                "background: #dff3dc; \n"
                "color: #24482b; border-radius: 10px; \n"
                "padding: 9px 12px; \n"
            )
            alignment = Qt.AlignmentFlag.AlignRight
        else:
            bubble.setStyleSheet(
                "background: #cbb3e8; color: #35204d; border-radius: 10px; "
                "padding: 9px 12px;"
            )
            alignment = Qt.AlignmentFlag.AlignLeft
        if index is None:
            self.message_layout.insertWidget(self.message_layout.count() - 1, bubble, 0, alignment)
            self.message_area.verticalScrollBar().setValue(
                self.message_area.verticalScrollBar().maximum()
            )
        else:
            self.message_layout.insertWidget(index, bubble, 0, alignment)

    def _insert_file_bubble(self, file_path, is_self=False, index=None):
        file_path = str(file_path).strip()
        if not file_path:
            return
        file_name = Path(file_path).name or file_path
        bubble = QLabel("文件\n" + file_name)
        bubble.setWordWrap(True)
        bubble.setToolTip(file_path)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(280)
        if is_self:
            bubble.setStyleSheet(
                "background: #dff3dc; color: #24482b; border-radius: 10px; "
                "padding: 10px 14px; font-weight: 600;"
            )
            alignment = Qt.AlignmentFlag.AlignRight
        else:
            bubble.setStyleSheet(
                "background: #cbb3e8; color: #35204d; border-radius: 10px; "
                "padding: 10px 14px; font-weight: 600;"
            )
            alignment = Qt.AlignmentFlag.AlignLeft
        if index is None:
            self.message_layout.insertWidget(self.message_layout.count() - 1, bubble, 0, alignment)
            self.message_area.verticalScrollBar().setValue(
                self.message_area.verticalScrollBar().maximum()
            )
        else:
            self.message_layout.insertWidget(index, bubble, 0, alignment)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MsgWindow("hello")
    window.openMsg("hello")
    sys.exit(app.exec())