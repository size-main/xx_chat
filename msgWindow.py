from pathlib import Path
import style
from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
	QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
	QTextEdit, QVBoxLayout, QWidget, QApplication, QFileDialog, QProgressBar
)
from history import HistoryWorker

class MsgWindow(QDialog):
	sendMessage = pyqtSignal(str, str)
	sendFileRequested = pyqtSignal(str)
	userNameChanged = pyqtSignal(str)
	loadHistoryRequested = pyqtSignal(str)
	saveHistoryRequested = pyqtSignal(str, list)
	appendHistoryRequested = pyqtSignal(str, str, str)
	_HISTORY_PAGE_SIZE = 30

	def __init__(self, friend_account=None):
		super().__init__()
		self.friend_account = ""
		self._friend_online_status = {}
		self._friend_online = False
		self.user_name = ""
		self.history_path = None
		self._messages = []
		self._history_offset = 0
		self._loading_history = False
		self._history_ready = False
		self._pending_messages = []
		self._selected_file_path = ""
		self._history_thread = QThread(self)
		self._history_worker = HistoryWorker()
		self._history_worker.moveToThread(self._history_thread)
		self.userNameChanged.connect(self._history_worker.set_user_name)
		self.loadHistoryRequested.connect(self._history_worker.load_history)
		self._history_worker.historyLoaded.connect(self._on_history_loaded)
		self.saveHistoryRequested.connect(self._history_worker.save_history)
		self.appendHistoryRequested.connect(self._history_worker.append_message)
		self._history_thread.start()
		self.setMinimumSize(460, 560)
		self.resize(520, 680)
		self._build_ui()
		if friend_account is not None:
			self.openMsg(friend_account)

	def set_user_name(self, user_name):
		self.user_name = str(user_name).strip()
		self.userNameChanged.emit(self.user_name)

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
		self.loadHistoryRequested.emit(self.friend_account)
		self.show()
		self.raise_()
		self.activateWindow()

	def _build_ui(self):
		self.setStyleSheet(style.msg_window_style)
		root_layout = QVBoxLayout(self)
		root_layout.setContentsMargins(22, 18, 22, 20)
		root_layout.setSpacing(12)

		header = QHBoxLayout()
		self.account_label = QLabel(objectName="friendAccount")
		header.addWidget(self.account_label, alignment=Qt.AlignmentFlag.AlignLeft)
		self.online_status_label = QLabel(objectName="onlineStatus")
		header.addWidget(self.online_status_label, alignment=Qt.AlignmentFlag.AlignLeft)
		header.addStretch()
		root_layout.addLayout(header)

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
		root_layout.addWidget(self.message_area, 1)

		self.input_box = QTextEdit()
		self.input_box.setPlaceholderText("输入消息...")
		self.input_box.setFixedHeight(78)
		self.input_box.textChanged.connect(self._update_send_button)
		root_layout.addWidget(self.input_box)

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
		root_layout.addLayout(send_row)

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

if __name__ == "__main__ ":
    import sys
    app = QApplication(sys.argv)
    window = MsgWindow("hello")
    window.openMsg("hello")
    sys.exit(app.exec())