import sys
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QTcpSocket
from PyQt6.QtWidgets import QMessageBox
import json
import struct

class Client(QObject):
    messageReceived = pyqtSignal(str, str)
    loadStatusChanged = pyqtSignal(bool)
    friendIdReadyChanged = pyqtSignal(list)
    friendReadChanged = pyqtSignal(str)
    loadFriendListRequested = pyqtSignal(list)
    registrationChanged = pyqtSignal(bool, str)
    appendFriendChanged = pyqtSignal(bool, str, str)
    loadAppendFriendChanged = pyqtSignal(str)
    friend_lost_connection = pyqtSignal(str, bool)

    HEAD_MARK = 0xA1A2
    TAIL_MARK = 0xB1B2
    HEADER_FIX_LEN = 6
    TAIL_LEN = 2

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        super().__init__()
        self.socket = QTcpSocket()
        self._receive_buffer = bytearray()
        self.socket.connectToHost(host, port)
        self.socket.readyRead.connect(self.receive_message)
        self.socket.disconnected.connect(lambda: QMessageBox.warning(None, "警告", "服务器断开"))
        self.socket.errorOccurred.connect(lambda: QMessageBox.warning(None, "警告", "服务器连接失败"))
        self. type_handler = {
            "load": lambda json_data: self.loadStatusChanged.emit(json_data.get("status") == "enable"),
            "friendIds": lambda json_data: self.friendIdReadyChanged.emit(json_data.get("data", [])),
            "friend": lambda json_data: self.friendReadChanged.emit(json_data.get("data", "")),
            "msg": lambda json_data: self.messageReceived.emit(json_data.get("friendName", ""), json_data.get("data", "")),
            "registration": lambda json_data: self.registrationChanged.emit(json_data["data"], json_data["error"]),
            "loadfriend": lambda json_data: self.loadFriendListRequested.emit(json_data["data"]),
            "append friend": lambda json_data: self.appendFriendChanged.emit(json_data["status"], json_data["data"], json_data["friendName"]),
            "add friend": lambda json_data: self.loadAppendFriendChanged.emit(json_data["friendName"]),
            "lost connection": lambda json_data: self.friend_lost_connection.emit(json_data["friendName"], False),
            "online": lambda json_data: self.friend_lost_connection.emit(json_data["friendName"], True)
        }

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