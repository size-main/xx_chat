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
        self.client = Client("bc0sd7tr.beesnat.com", 12436)
        self.history = HistoryWorker()
        self.clientThread = QThread()
        self.load = load()
        self.MainWindow = MainWindow()
        self.msgwindow = MsgWindow()
        self.setParent(self.MainWindow)
        self.load.show()
        self.client.moveToThread(self.clientThread)
        self.load.loadSignal.connect(self.__loading_init__)
        self.load.registerSignal.connect(lambda userName, password: self.client.registration_mssge_send(userName, password))
        self.client.registrationChanged.connect(lambda success, message: self.load.register_result(success, message))
        self.MainWindow.chatRequested.connect(self.msgwindow.openMsg)
        self.msgwindow.sendMessage.connect(self.__send_msg_event_handler__)
        self.client.messageReceived.connect(self.__message_received_handler__)
        self.client.loadStatusChanged.connect(self.__load_ok_handler__)
        self.client.friendIdReadyChanged.connect(self.__getFriendIds_handler__)
        self.client.friendReadChanged.connect(self.__getFriendList_handler__)
        self.MainWindow.loadFriendListRequested.connect(lambda keyword: self.client.send_load_friend_request(keyword))
        self.client.loadFriendListRequested.connect(self.MainWindow.load_friend_search_result)
        self.MainWindow.addFriendRequested.connect(lambda friendName: self.client.send_append_friend_request(self.userName, friendName))
        self.client.appendFriendChanged.connect(self.__handle_append_friend_result__)

    def __refresh_friend_list__(self):
        if not self.userName:
            return
        self.friendList = []
        self.friendId = []
        self.cnt = 0
        self.client.getFriend_load(self.userName)

    def __handle_append_friend_result__(self, success: bool, message: str):
        self.MainWindow.handle_add_friend_result(success, message)
        if success:
            self.__refresh_friend_list__()

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
        self.friendId = [friend for friend in friendIds if friend]
        self.cnt = len(self.friendId)
        if self.cnt <= 0:
            self.MainWindow.set_friend_list(self.friendList)
            return
        self.client.send_friend_get(self.friendId[self.cnt - 1])
        self.cnt -= 1

    def __getFriendList_handler__(self, friendName: str):
        friendName = str(friendName).strip()
        if not friendName or friendName in self.friendList:
            return
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