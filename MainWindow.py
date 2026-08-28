from pathlib import Path
import style
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QCloseEvent
from PyQt6.QtWidgets import (
	QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
	QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
	QVBoxLayout, QWidget
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
	addFriendRequested = pyqtSignal(str)

	def __init__(self, friend_list = None):
		super().__init__()
		self._friends = []
		self._pending_friend = ""
		self._add_timer = QTimer(self)
		self._add_timer.setSingleShot(True)
		self._add_timer.setInterval(2000)
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
		self.result_label = QLabel("输入关键词搜索本地好友")
		result_layout.addWidget(self.result_label, 1)
		self.add_result_button = QPushButton("添加", objectName="secondaryButton")
		self.add_result_button.hide()
		self.add_result_button.clicked.connect(self._request_add_friend)
		result_layout.addWidget(self.add_result_button)
		layout.addWidget(self.result_frame)
		layout.addStretch()
		return page

	def set_friend_list(self, friends):
		self._friends = [str(friend) for friend in friends if str(friend).strip()]
		self._filter_friends(self.friend_search.text())
		self.count_label.setText("%d 位联系人" % len(self._friends))
		if self._loading_overlay is not None:
			self._loading_overlay.deleteLater()
			self._loading_overlay = None

	def _filter_friends(self, text):
		keyword = text.strip().lower()
		self.friend_list.clear()
		for friend in self._friends:
			if keyword in friend.lower():
				item = QListWidgetItem("●  " + friend)
				item.setData(Qt.ItemDataRole.UserRole, friend)
				self.friend_list.addItem(item)

	def _friend_clicked(self, item):
		self.chatRequested.emit(item.data(Qt.ItemDataRole.UserRole))

	def _switch_page(self, page_index):
		self.stack.setCurrentIndex(page_index)
		self.contacts_button.setChecked(page_index == 0)
		self.add_button.setChecked(page_index == 1)

	def _search_friend(self):
		# keyword = self.add_search.text().strip().lower()
		# if not keyword:
		# 	self.result_label.setText("请输入好友昵称或账号")
		# 	self.add_result_button.hide()
		# 	return
		# matches = [friend for friend in self._friends if keyword in friend.lower()]
		# if matches:
		# 	self._pending_friend = matches[0]
		# 	self.result_label.setText("●  " + self._pending_friend)
		# 	self.add_result_button.show()
		# else:
		# 	self._pending_friend = ""
		# 	self.result_label.setText("没有找到匹配的好友")
		# 	self.add_result_button.hide()
		pass
	
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
			self.result_label.setText("已找到好友：" + self._pending_friend)
			self.add_result_button.hide()
		else:
			self.result_label.setText(str(message))


if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	app.setFont(QFont("Microsoft YaHei UI", 10))
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
