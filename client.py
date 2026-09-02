import sys
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QTcpSocket
from PyQt6.QtWidgets import QMessageBox
import json

class Client(QObject):
    messageReceived = pyqtSignal(str, str)
    loadStatusChanged = pyqtSignal(bool)
    friendIdReadyChanged = pyqtSignal(list)
    friendReadChanged = pyqtSignal(str)
    loadFriendListRequested = pyqtSignal(list)
    registrationChanged = pyqtSignal(bool, str)
    appendFriendChanged = pyqtSignal(bool, str)

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        super().__init__()
        self.socket = QTcpSocket()
        self._receive_buffer = bytearray()
        self.socket.connectToHost(host, port)
        self.socket.readyRead.connect(self.receive_message)
        self.socket.disconnected.connect(lambda: QMessageBox.warning(None, "警告", "服务器断开"))
        self.socket.errorOccurred.connect(lambda: QMessageBox.warning(None, "警告", "服务器连接失败"))

    def registration_mssge_send(self, userName: str, password: str):
        data = {
            "type": "registration",
            "userName": userName,
            "password": password
        }
        self.socket.write(json.dumps(data).encode())

    def load_end_mssage_end(self, userName):
        data = {
            "type": "loadend",
            "userName": userName
        }
        self.socket.write(json.dumps(data).encode())

    def getFriend_load(self, userName):
        data = {
            "type": "loading",
            "userName": userName
        }
        self.socket.write(json.dumps(data).encode())
        
    def loading_message(self, userName: str, password: str):
        data = {
            "type": "load",
            "userName": userName,
            "password": password
        }
        self.socket.write(json.dumps(data).encode())

    def send_friend_get(self, friendId: int):
        data = {
            "type": "friend",
            "data": friendId
        }
        print(data)
        self.socket.write(json.dumps(data).encode())

    def send_message(self, userName: str, friendName: str, message: str):
        data = {
            "type": "msg",
            "data": message,
            "userName": userName,
            "friendName": friendName
        }
        self.socket.write(json.dumps(data).encode())

    def send_load_friend_request(self, keyword: str):
        data = {
            "type": "loadfriend",
            "data": keyword
        }
        self.socket.write(json.dumps(data).encode())

    def send_append_friend_request(self, userName: str, friendName: str):
        data = {
            "type": "append friend",
            "userName": userName,
            "friendName": friendName
        }
        self.socket.write(json.dumps(data).encode())

    def receive_message(self):
        self._receive_buffer.extend(bytes(self.socket.readAll().data()))

        while len(self._receive_buffer) >= 4:
            size = int.from_bytes(self._receive_buffer[:4], byteorder="big")
            if len(self._receive_buffer) < size + 4:
                return

            payload = bytes(self._receive_buffer[4:size + 4])
            del self._receive_buffer[:size + 4]

            try:
                json_data = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                print("收到无效的 JSON 消息")
                continue

            if not isinstance(json_data, dict):
                continue

            message_type = json_data.get("type")
            if message_type == "load":
                self.loadStatusChanged.emit(json_data.get("status") == "enable")
            elif message_type == "friendIds":
                self.friendIdReadyChanged.emit(json_data.get("data", []))
            elif message_type == "friend":
                self.friendReadChanged.emit(json_data.get("data", ""))
            elif message_type == "msg":
                self.messageReceived.emit(
                    json_data.get("friendName", ""),
                    json_data.get("data", ""),
                )
            elif message_type == "registration":
                self.registrationChanged.emit(json_data["data"], json_data["error"])
            elif message_type == "loadfriend":
                self.loadFriendListRequested.emit(json_data["data"])
            elif message_type == "append friend":
                self.appendFriendChanged.emit(json_data["status"], json_data["data"])