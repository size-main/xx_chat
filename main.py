import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread
from PyQt6.QtGui import QIcon
from client import Client
from load import load
from MainWindow import MainWindow
from msgWindow import MsgWindow
from history import HistoryWorker

class MainCode(QObject):
    def __init__(self):
        super().__init__()
        self.userName: str = None
        self.nowFriend: str = None
        self.cnt = 0
        self.friendId = []
        self.friendList = list()
        self.client = Client("127.0.0.1", 8088)
        self.history = HistoryWorker()
        self.clientThread = QThread()
        self.load = load()
        self.MainWindow = MainWindow()
        self.msgwindow = MsgWindow()
        self.setParent(self.MainWindow)
        self.load.show()
        self.client.moveToThread(self.clientThread)
        self.load.loadSignal.connect(self.__loading_init__)
        self.load.registerSignal.connect(self.client.registration_mssge_send)
        self.client.registrationChanged.connect(self.load.register_result)
        self.MainWindow.chatRequested.connect(self.msgwindow.openMsg)
        self.msgwindow.sendMessage.connect(self.__send_msg_event_handler__)
        self.client.messageReceived.connect(self.__message_received_handler__)
        self.client.loadStatusChanged.connect(self.__load_ok_handler__)
        self.client.friendIdReadyChanged.connect(self.__getFriendIds_handler__)
        self.client.friendReadChanged.connect(self.__getFriendList_handler__)

    def __send_msg_event_handler__(self, friendName: str, msg: str):
        self.client.send_message(self.userName, friendName, msg)

    def __message_received_handler__(self, friendName: str, msg: str):
        friendName = str(friendName).strip()
        msg = str(msg)
        if not friendName or not msg or not self.userName:
            return
        self.history.append_message(friendName, friendName, msg)
        self.msgwindow.receive_message(friendName, msg)
        
    def __loading_init__(self, userName: str, password: str):
        self.userName = userName
        self.history.set_user_name(userName)
        self.msgwindow.set_user_name(userName)
        self.client.loading_message(userName, password)

    def __load_ok_handler__(self):
        self.load.close()
        self.MainWindow.show()
        self.client.getFriend_load(self.userName)

    def __getFriendIds_handler__(self, friendIds: list):
        self.friendId = friendIds
        self.cnt = len(self.friendId)
        self.client.send_friend_get(self.friendId[self.cnt - 1])
        self.cnt -= 1

    def __getFriendList_handler__(self, friendName: str):
        self.friendList.append(friendName)
        if self.cnt <= 0:
            self.MainWindow.set_friend_list(self.friendList)
            self.client.load_end_mssage_end(self.userName)
            return
        else:
            self.client.send_friend_get(self.friendId[self.cnt - 1])
            self.cnt -= 1 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    appIcon = QIcon(":/logo.ico")
    app.setWindowIcon(appIcon)
    window = MainCode()

    sys.exit(app.exec())