from pathlib import Path
import style
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPainter, QPen, QCloseEvent
from PyQt6.QtWidgets import (
	QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
	QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
	QVBoxLayout, QWidget, QMenu
)

class LoadingSpinner(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._angle = 0
		self.setFixedSize(44, 44)
		self._timer = QTimer(self)
		self._timer.timeout.connect(self._rotate)
		self._timer.start(40)

	def _rotate(self):
		self._angle = (self._angle + 30) % 360
		self.update()

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		painter.translate(self.width() / 2, self.height() / 2)
		painter.rotate(self._angle)
		for index in range(8):
			painter.save()
			painter.rotate(index * 45)
			pen = QPen(Qt.GlobalColor.white, 4)
			pen.setCapStyle(Qt.PenCapStyle.RoundCap)
			pen.setColor(Qt.GlobalColor.white)
			painter.setPen(pen)
			painter.drawLine(0, -16, 0, -7)
			painter.restore()


class MainWindow(QMainWindow):
	chatRequested = pyqtSignal(str)
	loadFriendListRequested = pyqtSignal(str)
	addFriendRequested = pyqtSignal(str)
	deleteFriendRequested = pyqtSignal(str)

	def __init__(self, friend_list = None):
		super().__init__()
		self._friends = []
		self._friend_online_status = {}
		self._chat_previews = {}
		self._chat_unread = set()
		self._pending_friend = ""
		self._add_timer = QTimer(self)
		self._add_timer.setSingleShot(True)
		self._add_timer.setInterval(4000)
		self._add_timer.timeout.connect(self._handle_add_timeout)
		self.setWindowTitle("联系人")
		self.setMinimumSize(840, 560)
		self.resize(960, 620)
		self._build_ui()
		self._loading_overlay = None
		if friend_list is None:
			self._show_loading()
		else:
			self.set_friend_list(friend_list)

	def _build_ui(self):
		self.setStyleSheet(style.MainWindow_style)
		root = QWidget()
		root_layout = QHBoxLayout(root)
		root_layout.setContentsMargins(0, 0, 0, 0)
		root_layout.setSpacing(0)
		self.setCentralWidget(root)

		sidebar = QFrame(objectName="sidebar")
		sidebar.setFixedWidth(210)
		side_layout = QVBoxLayout(sidebar)
		side_layout.setContentsMargins(20, 28, 20, 20)
		side_layout.addWidget(QLabel("Q  联系人", objectName="brand"))
		side_layout.addWidget(QLabel("在线 · 今天也要保持联系", objectName="account"))
		side_layout.addSpacing(34)
		side_layout.addWidget(QLabel("工作台", objectName="sectionTitle"))
		self.contacts_button = QPushButton("  好友列表", objectName="navButton")
		self.add_button = QPushButton("  添加好友", objectName="navButton")
		for button in (self.contacts_button, self.add_button):
			button.setCheckable(True)
			side_layout.addWidget(button)
		self.contacts_button.setChecked(True)
		side_layout.addStretch()
		side_layout.addWidget(QLabel("安全连接 · 本地联系人", objectName="account"))
		root_layout.addWidget(sidebar)

		content = QWidget()
		content_layout = QVBoxLayout(content)
		content_layout.setContentsMargins(38, 30, 38, 30)
		content_layout.setSpacing(16)
		header = QHBoxLayout()
		title_box = QVBoxLayout()
		title_box.addWidget(QLabel("好友", objectName="pageTitle"))
		title_box.addWidget(QLabel("选择一个好友，开始新的聊天", objectName="hint"))
		header.addLayout(title_box)
		header.addStretch()
		self.count_label = QLabel(objectName="hint")
		header.addWidget(self.count_label, alignment=Qt.AlignmentFlag.AlignBottom)
		content_layout.addLayout(header)
		self.stack = QStackedWidget()
		self.stack.addWidget(self._build_contacts_page())
		self.stack.addWidget(self._build_add_page())
		content_layout.addWidget(self.stack)
		root_layout.addWidget(content, 1)
		self.contacts_button.clicked.connect(lambda: self._switch_page(0))
		self.add_button.clicked.connect(lambda: self._switch_page(1))

	def _show_loading(self):
		self._loading_overlay = QWidget(self.centralWidget())
		self._loading_overlay.setStyleSheet("background-color: rgba(32, 43, 60, 235);")
		layout = QVBoxLayout(self._loading_overlay)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		spinner = LoadingSpinner()
		label = QLabel("正在加载好友列表...")
		label.setStyleSheet("color: white; font-size: 14px;")
		layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
		self._loading_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
		self._loading_overlay.show()
		self._loading_overlay.raise_()

	def resizeEvent(self, event):
		super().resizeEvent(event)
		if self._loading_overlay is not None:
			self._loading_overlay.setGeometry(self.centralWidget().rect())

	def _build_contacts_page(self):
		page = QWidget()
		layout = QVBoxLayout(page)
		layout.setContentsMargins(0, 4, 0, 0)
		self.friend_search = QLineEdit(objectName="searchBox")
		self.friend_search.setPlaceholderText("搜索好友或群聊")
		self.friend_search.textChanged.connect(self._filter_friends)
		layout.addWidget(self.friend_search)
		self.friend_list = QListWidget()
		self.friend_list.itemClicked.connect(self._friend_clicked)
		self.friend_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.friend_list.customContextMenuRequested.connect(self._show_friend_context_menu)
		layout.addWidget(self.friend_list)
		return page

	def _build_add_page(self):
		page = QWidget()
		layout = QVBoxLayout(page)
		layout.setContentsMargins(0, 4, 0, 0)
		search = QHBoxLayout()
		self.add_search = QLineEdit(objectName="searchBox")
		self.add_search.setPlaceholderText("输入好友昵称或账号")
		self.add_search.returnPressed.connect(self._search_friend)
		search_button = QPushButton("搜索", objectName="primaryButton")
		search_button.clicked.connect(self._search_friend)
		search.addWidget(self.add_search)
		search.addWidget(search_button)
		layout.addLayout(search)
		layout.addWidget(QLabel("搜索结果", objectName="sectionTitle"))
		self.result_frame = QFrame(objectName="resultFrame")
		result_layout = QHBoxLayout(self.result_frame)
		self.result_label = QLabel("输入关键词搜索用户")
		result_layout.addWidget(self.result_label, 1)
		self.add_result_button = QPushButton("添加", objectName="secondaryButton")
		self.add_result_button.hide()
		self.add_result_button.clicked.connect(self._request_add_friend)
		result_layout.addWidget(self.add_result_button)
		layout.addWidget(self.result_frame)
		self.result_list = QListWidget()
		self.result_list.hide()
		self.result_list.itemClicked.connect(self._select_result_friend)
		layout.addWidget(self.result_list)
		layout.addStretch()
		return page

	def set_friend_list(self, friends):
		self._friends = [self._text_value(friend) for friend in friends]
		self._friends = [friend for friend in self._friends if friend]
		self._filter_friends(self.friend_search.text())
		self.count_label.setText("%d 位联系人" % len(self._friends))
		if self._loading_overlay is not None:
			self._loading_overlay.deleteLater()
			self._loading_overlay = None

	def remove_friend(self, friend_name):
		friend_name = self._text_value(friend_name)
		if not friend_name:
			return
		self._friends = [friend for friend in self._friends if friend != friend_name]
		self._friend_online_status.pop(friend_name, None)
		self._chat_previews.pop(friend_name, None)
		self._chat_unread.discard(friend_name)
		self._filter_friends(self.friend_search.text())
		self.count_label.setText("%d 位联系人" % len(self._friends))

	def set_friend_online(self, friend_name, is_online):
		friend_name = str(friend_name).strip()
		if not friend_name:
			return
		self._friend_online_status[friend_name] = bool(is_online)
		self._filter_friends(self.friend_search.text())

	def update_chat_preview(self, friend_name, message, unread=True):
		friend_name = self._text_value(friend_name)
		if not friend_name:
			return
		self._chat_previews[friend_name] = self._text_value(message).replace("\n", " ")
		if unread:
			self._chat_unread.add(friend_name)
		else:
			self._chat_unread.discard(friend_name)
		self._filter_friends(self.friend_search.text())

	@staticmethod
	def _text_value(value):
		if isinstance(value, bytes):
			return value.decode("utf-8", errors="replace").strip()
		return str(value or "").strip()

	def _filter_friends(self, text):
		keyword = text.strip().lower()
		self.friend_list.clear()
		for friend in self._friends:
			if keyword in friend.lower():
				is_online = self._friend_online_status.get(friend, False)
				item = QListWidgetItem()
				item.setData(Qt.ItemDataRole.UserRole, friend)
				item.setData(Qt.ItemDataRole.UserRole + 1, is_online)
				self.friend_list.addItem(item)
				row = QWidget()
				row_layout = QVBoxLayout(row)
				row_layout.setContentsMargins(0, 0, 0, 0)
				row_layout.setSpacing(2)
				title_layout = QHBoxLayout()
				title_layout.setContentsMargins(0, 0, 0, 0)
				name_label = QLabel(friend)
				name_label.setStyleSheet("font-weight: 600;")
				title_layout.addWidget(name_label)
				title_layout.addStretch()
				if friend in self._chat_unread:
					unread_label = QLabel("●")
					unread_label.setStyleSheet("color: #e5484d; font-size: 14px;")
					title_layout.addWidget(unread_label)
				row_layout.addLayout(title_layout)
				preview = self._chat_previews.get(friend, "")
				preview_label = QLabel(preview)
				preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
				preview_label.setStyleSheet("color: #8b96a8; font-size: 12px;")
				preview_label.setMaximumHeight(20)
				row_layout.addWidget(preview_label)
				item.setSizeHint(row.sizeHint().expandedTo(row.minimumSizeHint()))
				item.setSizeHint(item.sizeHint().expandedTo(QSize(0, 52)))
				self.friend_list.setItemWidget(item, row)

	def _friend_clicked(self, item):
		friend_name = item.data(Qt.ItemDataRole.UserRole)
		self._chat_unread.discard(friend_name)
		self._filter_friends(self.friend_search.text())
		self.chatRequested.emit(friend_name)

	def _show_friend_context_menu(self, position):
		item = self.friend_list.itemAt(position)
		if item is None:
			return
		friend_name = item.data(Qt.ItemDataRole.UserRole)
		menu = QMenu(self.friend_list)
		delete_action = menu.addAction("删除好友")
		if menu.exec(self.friend_list.mapToGlobal(position)) == delete_action:
			self.remove_friend(friend_name)
			self.deleteFriendRequested.emit(friend_name)

	def _switch_page(self, page_index):
		self.stack.setCurrentIndex(page_index)
		self.contacts_button.setChecked(page_index == 0)
		self.add_button.setChecked(page_index == 1)

	def _search_friend(self):
		keyword = self.add_search.text().strip().lower()
		if not keyword:
			self.result_label.setText("请输入好友昵称或账号")
			self.add_result_button.hide()
			return
		self.loadFriendListRequested.emit(keyword)	

	def _select_result_friend(self, item):
		if item is None:
			return
		self._pending_friend = item.data(Qt.ItemDataRole.UserRole)
		self.result_label.setText("●  " + self._pending_friend)
		self.add_result_button.show()

	def load_friend_search_result(self, firendNameList: list):
		friends = [str(name).strip() for name in firendNameList if str(name).strip()]
		self.result_list.clear()
		self.result_list.hide()
		self.add_result_button.hide()
		self._pending_friend = ""
		if not friends:
			self.result_label.setText("未找到好友")
			return

		for friend in friends:
			item = QListWidgetItem("●  " + friend)
			item.setData(Qt.ItemDataRole.UserRole, friend)
			self.result_list.addItem(item)

		self.result_list.show()
		self.result_label.setText("请选择要添加的好友")
		if self.result_list.count() > 0:
			self.result_list.setCurrentRow(0)
			self._select_result_friend(self.result_list.currentItem())

	def _request_add_friend(self):
		if not self._pending_friend:
			return
		self._add_timer.start()
		self.add_result_button.setEnabled(False)
		self.result_label.setText("正在请求添加 %s ..." % self._pending_friend)
		self.addFriendRequested.emit(self._pending_friend)

	def _handle_add_timeout(self):
		self.add_result_button.setEnabled(True)
		QMessageBox.warning(self, "请求超时", "服务器超时，请重试")
		self.result_label.setText("服务器超时，请重试")

	def handle_add_friend_result(self, found, message=""):
		if not self._add_timer.isActive():
			return
		self._add_timer.stop()
		self.add_result_button.setEnabled(True)
		if found:
			result_text = str(message).strip() if str(message).strip() else "已发送好友申请：" + self._pending_friend
			self.result_label.setText(result_text)
			self.add_result_button.hide()
			self.result_list.hide()
		else:
			self.result_label.setText(str(message) if str(message).strip() else "添加好友失败")


if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	app.setFont(QFont("Microsoft YaHei UI", 10))
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
