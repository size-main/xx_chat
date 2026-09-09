import sys
import base64
import binascii
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtNetwork import QTcpSocket
from PyQt6.QtWidgets import QMessageBox
import json
import struct
from pathlib import Path

class Client(QObject):
    messageReceived = pyqtSignal(str, str)
    fileReceived = pyqtSignal(str, str, bytes)
    fileSendProgress = pyqtSignal(int)
    loadStatusChanged = pyqtSignal(bool)
    friendIdReadyChanged = pyqtSignal(list)
    friendReadChanged = pyqtSignal(str)
    loadFriendListRequested = pyqtSignal(list)
    registrationChanged = pyqtSignal(bool, str)
    appendFriendChanged = pyqtSignal(bool, str, str)
    loadAppendFriendChanged = pyqtSignal(str)
    friend_lost_connection = pyqtSignal(str, bool)
    delete_friend_lostChanged = pyqtSignal(str)
    reconnectStatusChanged = pyqtSignal(bool, str)

    HEAD_MARK = 0xA1A2
    TAIL_MARK = 0xB1B2
    HEADER_FIX_LEN = 6
    TAIL_LEN = 2

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = QTcpSocket()
        self._receive_buffer = bytearray()
        self._last_login = ("", "")
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._reconnect_count = 0
        self._is_reconnecting = False
        self._last_reconnect_status = None
        self._last_reconnect_message = ""
        self._reconnect_phase = False
        self._last_socket_state = None
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(3000)
        self._health_timer.timeout.connect(self._health_check)
        self.socket.stateChanged.connect(self._on_socket_state_changed)
        self.socket.connected.connect(self._on_socket_connected)
        self.socket.readyRead.connect(self.receive_message)
        self.socket.disconnected.connect(self._on_socket_disconnected)
        self.socket.errorOccurred.connect(self._on_socket_error)
        self._health_timer.start()
        self._connect_socket()
        self.type_handler = {
            "load": lambda json_data: self.loadStatusChanged.emit(json_data.get("status") == "enable"),
            "friendIds": lambda json_data: self.friendIdReadyChanged.emit(json_data.get("data", [])),
            "friend": lambda json_data: self.friendReadChanged.emit(json_data.get("data", "")),
            "msg": lambda json_data: self.messageReceived.emit(json_data.get("friendName", ""), json_data.get("data", "")),
            "file": self._handle_file_event,
            "fileMessage": self._handle_file_event,
            "registration": lambda json_data: self.registrationChanged.emit(json_data["data"], json_data["error"]),
            "loadfriend": lambda json_data: self.loadFriendListRequested.emit(json_data["data"]),
            "append friend": lambda json_data: self.appendFriendChanged.emit(json_data["status"], json_data["data"], json_data["friendName"]),
            "add friend": lambda json_data: self.loadAppendFriendChanged.emit(json_data["friendName"]),
            "lost connection": lambda json_data: self.friend_lost_connection.emit(json_data["friendName"], False),
            "online": lambda json_data: self.friend_lost_connection.emit(json_data["friendName"], True),
            "delete friend": self._handle_delete_friend_event,
            "deleteFriend": self._handle_delete_friend_event,
            "delete": self._handle_delete_friend_event
        }

    def _connect_socket(self):
        if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            return
        self.socket.abort()
        self.socket.connectToHost(self.host, self.port)

    def _set_reconnect_status(self, reconnecting: bool, message: str = ""):
        if reconnecting == self._last_reconnect_status:
            return
        self._last_reconnect_status = reconnecting
        self._last_reconnect_message = message
        self.reconnectStatusChanged.emit(reconnecting, message)

    def _health_check(self):
        if self.socket.state() in (QTcpSocket.SocketState.UnconnectedState, QTcpSocket.SocketState.ClosingState):
            if not self._is_reconnecting and not self._reconnect_phase:
                self._schedule_reconnect()

    def _on_socket_state_changed(self, state):
        if state == self._last_socket_state:
            return
        self._last_socket_state = state

        if state == QTcpSocket.SocketState.ConnectedState:
            self._reconnect_phase = False
            self._is_reconnecting = False
            self._set_reconnect_status(False, "")
            return

        if state in (QTcpSocket.SocketState.UnconnectedState, QTcpSocket.SocketState.ClosingState):
            if not self._reconnect_phase and not self._is_reconnecting:
                self._schedule_reconnect()

    def _on_socket_connected(self):
        self._last_socket_state = QTcpSocket.SocketState.ConnectedState
        self._reconnect_phase = False
        self._is_reconnecting = False
        self._reconnect_count = 0
        self._health_timer.start()
        self._set_reconnect_status(False, "")
        self._relogin_if_needed()

    def _on_socket_disconnected(self):
        if self._reconnect_phase:
            return
        self._last_socket_state = QTcpSocket.SocketState.UnconnectedState
        self._reconnect_phase = True
        self._set_reconnect_status(True, "服务器连接断开，正在重连...")
        self._schedule_reconnect()

    def _on_socket_error(self, socket_error):
        if self._reconnect_phase:
            return
        state = self.socket.state()
        if state not in (QTcpSocket.SocketState.ConnectingState, QTcpSocket.SocketState.ConnectedState):
            self._last_socket_state = QTcpSocket.SocketState.UnconnectedState
            self._reconnect_phase = True
            self._set_reconnect_status(True, "连接失败，正在重连...")
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._is_reconnecting:
            return
        self._is_reconnecting = True
        self._reconnect_phase = True
        if self._last_reconnect_status is not True:
            self._set_reconnect_status(True, "服务器连接断开，正在重连...")
        delay = min(max(self._reconnect_count, 1) * 1000, 8000)
        self._reconnect_timer.start(delay)

    def _attempt_reconnect(self):
        self._is_reconnecting = False
        if self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            self._reconnect_phase = False
            self._set_reconnect_status(False, "")
            return

        self._reconnect_count += 1
        self.socket.abort()
        self.socket.connectToHost(self.host, self.port)
        if self.socket.state() not in (
            QTcpSocket.SocketState.ConnectedState,
            QTcpSocket.SocketState.ConnectingState,
        ):
            self._schedule_reconnect()

    def _relogin_if_needed(self):
        user_name, password = self._last_login
        if user_name and password:
            self.loading_message(user_name, password)

    def set_login_credentials(self, user_name: str, password: str):
        self._last_login = (str(user_name or "").strip(), str(password or ""))

    def _handle_delete_friend_event(self, json_data):
        friend_name = json_data.get("friendName", json_data.get("data", ""))
        self.delete_friend_lostChanged.emit(str(friend_name).strip())

    def hash_password_(self, password: str) -> str:
        
        return ""    

    def _handle_file_event(self, json_data):
        friend_name = str(json_data.get("friendName", "")).strip()
        file_name = json_data.get("fileName", json_data.get("filename", json_data.get("name", "")))
        encoded_data = json_data.get("fileData", json_data.get("content", json_data.get("data", "")))
        if isinstance(encoded_data, dict):
            file_name = encoded_data.get("fileName", file_name)
            encoded_data = encoded_data.get("data", encoded_data.get("content", ""))
        if not friend_name or not file_name or not isinstance(encoded_data, str):
            return
        try:
            file_data = base64.b64decode(encoded_data, validate=True)
        except (ValueError, binascii.Error):
            return
        self.fileReceived.emit(friend_name, str(file_name), file_data)

    def __self_sender_msg__(self, msg: str):
        body = msg.encode("utf-8")
        length = len(body)
        head_mark = 0xA1A2
        tail_mark = 0xB1B2
        
        packet = struct.pack(">H", head_mark)
        packet += struct.pack(">I", length)
        packet += body 
        packet += struct.pack(">H", tail_mark)
        
        self.socket.write(packet) 

    def registration_mssge_send(self, userName: str, password: str):
        data = {
            "type": "registration",
            "userName": userName,
            "password": password
        }
        self.__self_sender_msg__(json.dumps(data))

    def load_end_mssage_end(self, userName):
        data = {
            "type": "loadend",
            "userName": userName
        }
        self.__self_sender_msg__(json.dumps(data))

    def getFriend_load(self, userName):
        data = {
            "type": "loading",
            "userName": userName
        }
        self.__self_sender_msg__(json.dumps(data))
         
    def loading_message(self, userName: str, password: str):
        self.set_login_credentials(userName, password)
        data = {
            "type": "load",
            "userName": userName,
            "password": password
        }
        self.__self_sender_msg__(json.dumps(data))

    def send_friend_get(self, friendId: int):
        data = {
            "type": "friend",
            "data": friendId
        }
        self.__self_sender_msg__(json.dumps(data))

    def send_message(self, userName: str, friendName: str, message: str):
        data = {
            "type": "msg",
            "data": message,
            "userName": userName,
            "friendName": friendName
        }
        self.__self_sender_msg__(json.dumps(data))

    def send_file(self, userName: str, friendName: str, file_path: str):
        try:
            with Path(file_path).open("rb") as file:
                file_data = base64.b64encode(file.read()).decode("ascii")
        except OSError:
            return False
        data = {
            "type": "file",
            "userName": userName,
            "friendName": friendName,
            "fileName": file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1],
            "fileData": file_data
        }
        body = json.dumps(data).encode("utf-8")
        packet = struct.pack(">H I", self.HEAD_MARK, len(body)) + body
        packet += struct.pack(">H", self.TAIL_MARK)
        total_size = len(packet)
        sent_size = 0
        chunk_size = 64 * 1024
        while sent_size < total_size:
            end = min(sent_size + chunk_size, total_size)
            self.socket.write(packet[sent_size:end])
            sent_size = end
            self.fileSendProgress.emit(int(sent_size * 100 / total_size))
        self.socket.flush()
        return True

    def send_load_friend_request(self, keyword: str):
        data = {
            "type": "loadfriend",
            "data": keyword
        }
        self.__self_sender_msg__(json.dumps(data))

    def send_append_friend_request(self, userName: str, friendName: str):
        data = {
            "type": "append friend",
            "userName": userName,
            "friendName": friendName
        }
        self.__self_sender_msg__(json.dumps(data))

    def send_delete_friend_request(self, userName: str, friendName: str):
        data = {
            "type": "delete friend",
            "userName": userName,
            "friendName": friendName
        }
        self.__self_sender_msg__(json.dumps(data))

    def receive_message(self):
        self._receive_buffer.extend(bytes(self.socket.readAll().data()))

        while len(self._receive_buffer) >= 4:
            buf_len = len(self._receive_buffer)
            if buf_len < 8:
                break

            head_mark, body_len = struct.unpack(">H I", self._receive_buffer[:6])
            full_packet_len = self.HEADER_FIX_LEN + body_len + self.TAIL_LEN

            if buf_len < full_packet_len:
                break

            tail_pos = self.HEADER_FIX_LEN + body_len
            tail_mark, = struct.unpack(">H", self._receive_buffer[tail_pos:tail_pos + 2])

            if head_mark != self.HEAD_MARK or tail_mark != self.TAIL_MARK:
                print("协议标记错误，丢弃损坏头部，滑动1字节继续查找包头")
                del self._receive_buffer[:1]
                continue

            payload_bytes = self._receive_buffer[6: 6 + body_len]
            del self._receive_buffer[:full_packet_len]

            try:
                json_data = json.loads(payload_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                print(f"JSON解析失败: {e}")
                continue

            if not isinstance(json_data, dict):
                continue

            message_type = json_data.get("type")
            self.type_handler[message_type](json_data)