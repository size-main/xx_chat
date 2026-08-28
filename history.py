import json
import sys
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class HistoryWorker(QObject):
    historyLoaded = pyqtSignal(str, list)
    historyError = pyqtSignal(str)

    def __init__(self, path: str = None, userName: str = None) -> None:
        super().__init__()
        base_path = Path(path) if path else Path(sys.argv[0]).resolve().parent
        if base_path.suffix:
            base_path = base_path.parent
        self.base_path = base_path / "history"
        self.user_name = ""
        self.set_user_name(userName)

    def _user_path(self):
        return self.base_path / self.user_name

    def _history_file(self, friend_account):
        friend_name = str(friend_account).strip()
        if not friend_name:
            return None
        return self._user_path() / f"{friend_name}.json"

    @pyqtSlot(str)
    def set_user_name(self, user_name):
        self.user_name = str(user_name or "").strip()
        if self.user_name:
            self._user_path().mkdir(parents=True, exist_ok=True)

    @pyqtSlot(str)
    def load_history(self, friend_account):
        friend_name = str(friend_account).strip()
        history_file = self._history_file(friend_name)
        if history_file is None or not self.user_name:
            self.historyLoaded.emit(friend_name, [])
            return
        try:
            if not history_file.exists():
                self.historyLoaded.emit(friend_name, [])
                return
            with history_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
            messages = data if isinstance(data, list) else []
            self.historyLoaded.emit(friend_name, messages)
        except (OSError, json.JSONDecodeError) as error:
            self.historyError.emit(f"读取聊天记录失败: {error}")
            self.historyLoaded.emit(friend_name, [])

    @pyqtSlot(str, list)
    def save_history(self, friend_account, messages):
        history_file = self._history_file(friend_account)
        if history_file is None or not self.user_name:
            return
        try:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with history_file.open("w", encoding="utf-8") as file:
                json.dump(messages if isinstance(messages, list) else [], file,
                        ensure_ascii=False, indent=2)
        except OSError as error:
            self.historyError.emit(f"保存聊天记录失败: {error}")

    @pyqtSlot(str, str, str)
    def append_message(self, friend_account, sender, message):
        history_file = self._history_file(friend_account)
        if history_file is None or not self.user_name:
            return
        messages = []
        if history_file.exists():
            try:
                with history_file.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                messages = data if isinstance(data, list) else []
            except (OSError, json.JSONDecodeError):
                messages = []
        messages.append({"sender": str(sender), "message": str(message)})
        self.save_history(friend_account, messages)