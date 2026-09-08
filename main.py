import sys
from pathlib import Path
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
        self.msgwindow.sendFileRequested.connect(self.__send_file_event_handler__)
        self.client.fileSendProgress.connect(self.msgwindow.set_file_send_progress)
        self.client.messageReceived.connect(self.__message_received_handler__)
        self.client.fileReceived.connect(self.__file_received_handler__)
        self.client.loadStatusChanged.connect(self.__load_ok_handler__)
        self.client.friendIdReadyChanged.connect(self.__getFriendIds_handler__)
        self.client.friendReadChanged.connect(self.__getFriendList_handler__)
        self.MainWindow.loadFriendListRequested.connect(lambda keyword: self.client.send_load_friend_request(keyword))
        self.client.loadFriendListRequested.connect(self.MainWindow.load_friend_search_result)
        self.MainWindow.addFriendRequested.connect(lambda friendName: self.client.send_append_friend_request(self.userName, friendName))
        self.client.appendFriendChanged.connect(self.__handle_append_friend_result__)
        self.client.loadAppendFriendChanged.connect(self.__load_append_friend_result__)
        self.client.friend_lost_connection.connect(lambda friendName, online: self.MainWindow.set_friend_online(friendName, online))
        self.client.friend_lost_connection.connect(lambda friendName, online: self.msgwindow.set_friend_online(friendName, online))
        self.client.delete_friend_lostChanged.connect(self.__delete_friend_result__)
        self.MainWindow.deleteFriendRequested.connect(self.__delete_friend_requested__)

    def __delete_friend_requested__(self, friendName):
        self.__delete_friend_result__(friendName)
        self.client.send_delete_friend_request(self.userName, friendName)

    def __delete_friend_result__(self, friendName):
        friendName = str(friendName).strip()
        if not friendName:
            return
        if friendName in self.friendList:
            self.friendList.remove(friendName)
        self.MainWindow.remove_friend(friendName)
        
    def __refresh_friend_list__(self):
        if not self.userName:
            return
        self.friendList = []
        self.friendId = []
        self.cnt = 0
        self.client.getFriend_load(self.userName)

    def __load_append_friend_result__(self, friendName: str):
        self.friendList.append(friendName)
        self.MainWindow.set_friend_list(self.friendList)
        self.__load_history_previews__([friendName])

    def __handle_append_friend_result__(self, success: bool, message: str, friendName: str):
        self.MainWindow.handle_add_friend_result(success, message)
        if success:
            self.friendList.append(friendName)
            self.MainWindow.set_friend_list(self.friendList)
            self.__load_history_previews__([friendName])

    def __load_history_previews__(self, friends):
        for friendName in friends:
            message = self.history.latest_message(friendName)
            if message:
                self.MainWindow.update_chat_preview(friendName, message, unread=False)

    def __send_msg_event_handler__(self, friendName: str, msg: str):
        self.MainWindow.update_chat_preview(friendName, msg, unread=False)
        self.client.send_message(self.userName, friendName, msg)

    def __send_file_event_handler__(self, file_path: str):
        friendName = self.msgwindow.friend_account
        file_path = str(file_path).strip()
        if not self.userName or not friendName or not file_path:
            return
        if not Path(file_path).is_file():
            return
        self.history.append_file(friendName, "self", file_path)
        self.MainWindow.update_chat_preview(
            friendName,
            "[文件] " + Path(file_path).name,
            unread=False,
        )
        self.client.send_file(self.userName, friendName, file_path)

    def __message_received_handler__(self, friendName: str, msg: str):
        friendName = str(friendName).strip()
        msg = str(msg)
        if not friendName or not msg or not self.userName:
            return
        self.history.append_message(friendName, friendName, msg)
        self.msgwindow.receive_message(friendName, msg)
        is_active_chat = (
            self.msgwindow.isVisible()
            and self.msgwindow.friend_account == friendName
        )
        self.MainWindow.update_chat_preview(friendName, msg, unread=not is_active_chat)

    def __file_received_handler__(self, friendName: str, fileName: str, fileData: bytes):
        friendName = str(friendName).strip()
        fileName = str(fileName).strip()
        if not friendName or not fileName or fileData is None:
            return
        file_path = self.history.save_received_file(friendName, fileName, fileData)
        if not file_path:
            return
        self.history.append_file(friendName, friendName, file_path)
        self.msgwindow.receive_file(friendName, file_path)
        self.MainWindow.update_chat_preview(
            friendName,
            "[文件] " + Path(file_path).name,
            unread=not (
                self.msgwindow.isVisible()
                and self.msgwindow.friend_account == friendName
            ),
        )
        
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
            self.__load_history_previews__(self.friendList)
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
            self.__load_history_previews__(self.friendList)
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