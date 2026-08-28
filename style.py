from enum import Enum

msg_window_style = """
    QDialog {
        background: #f6f4fb;
    }

    QLabel { 
        color: #293047;
        font-family: "Microsoft YaHei UI";
    }

    QLabel#friendAccount {
        color: #38205f;
        font-size: 18px;
        font-weight: 700;
    }

    QTextEdit {
        background: #ffffff;
        border: 1px solid #e3dced;
        border-radius: 8px;
        padding: 8px;
        font-size: 14px;
    }

    QTextEdit:focus {
        border: 1px solid #9b73c7;
    }

    QPushButton#sendButton { 
        background: #7250a4; 
        color: #ffffff;
        border: 0; 
        border-radius: 7px; 
        padding: 0 20px; 
        font-weight: 600; 
    }

    QPushButton#sendButton:hover { 
        background: #60418e; 
    }
                
    QPushButton#sendButton:disabled { 
        background: #c7b9d8; 
    }
"""

msg_my_bubble = """
    background: #dff3dc;
    color: #24482b; 
    border-radius: 10px;
    padding: 9px 12px;
"""

msg_friend_bubble = """
     background: #cbb3e8;
    color: #24482b; 
    border-radius: 10px;
    padding: 9px 12px;
"""

MainWindow_style = """
    QMainWindow { 
        background: #f5f7fb; 
    }

    QWidget { 
        color: #263247; 
        font-family: "Microsoft YaHei UI"; 
    }

    QFrame#sidebar { 
        background: #202b3c; 
    }

    QLabel#brand { 
        color: #ffffff; 
        font-size: 22px; 
        font-weight: 700; 
    }

    QLabel#account { 
        color: #aab7ca; 
        font-size: 12px; 
    }

    QLabel#sectionTitle { 
        color: #7f8ba0; 
        font-size: 12px; 
        font-weight: 700; 
    }

    QLabel#pageTitle { 
        color: #1d2939; 
        font-size: 24px; 
        font-weight: 700; 
    }

    QLabel#hint { 
        color: #8b96a8; 
        font-size: 13px; 
    }

    QPushButton#navButton { 
        border: 0; 
        border-radius: 8px; 
        padding: 12px; 
        text-align: left; 
        color: #b8c3d5; 
        font-size: 14px; 
        background: transparent; 
    }

    QPushButton#navButton:hover { 
        background: #2d3a4f; 
        color: #ffffff; 
    }

    QPushButton#navButton:checked { 
        background: #3b82d0; 
        color: #ffffff; 
    }

    QLineEdit#searchBox { 
        background: #ffffff; 
        border: 1px solid #e3e8f0; 
        border-radius: 9px; 
        padding: 10px 13px; 
        font-size: 14px; 
    }

    QLineEdit#searchBox:focus { 
        border: 1px solid #4d9de0; 
    }

    QListWidget { 
        border: 0; 
        background: transparent; 
        outline: 0; 
    }

    QListWidget::item { 
        padding: 13px 14px; 
        border-radius: 9px; 
    }

    QListWidget::item:hover { 
        background: #eaf2fb; 
    }

    QListWidget::item:selected { 
        background: #dcecfb; 
        color: #1769aa;
    }

    QFrame#resultFrame { 
        background: #ffffff; 
        border: 1px solid #e3e8f0; 
        border-radius: 10px; 
    }

    QPushButton#primaryButton { 
        background: #3184cf; 
        color: #ffffff; 
        border: 0; 
        border-radius: 7px; 
        padding: 9px 18px; 
        font-weight: 600; 
    }

    QPushButton#primaryButton:hover { 
        background: #256eaf; 
    }

    QPushButton#primaryButton:disabled { 
        background: #a9c8e5; 
    }

    QPushButton#secondaryButton { 
        background: #edf4fb; 
        color: #2775b5; 
        border: 0; 
        border-radius: 7px; 
        padding: 8px 15px; 
        font-weight: 600; 
    }
"""

class loadWindow(Enum):
    toolButton = """
        QToolButton {
            border: none;
            border-radius: 16px;
            padding: 6px;
        }
        QToolButton:hover {
            background-color: #E8F2FC;
        }
    """
    closeButton = """
        QToolButton {
            border: none;
            border-radius: 16px;
            padding: 6px;
        }
        QToolButton:hover {
            background-color: #FDE8E8;
        }
    """
    center_widget = """
        QPushButton {
            background-color: rgba(0, 0, 0, 0);
            color: rgb(0, 179, 255);
            border: none;
        }
        QPushButton: hover {
            background-color: rgba(0, 0, 0, 0);
        }
        QPushButton: pressed {
            background-color:  rgba(0, 0, 0, 0);
        }
    """
    portrait = """
        QLabel {
            background-color: #EAF4FC;
            border: 4px solid #FFFFFF;
            border-radius: 44px;
        }
    """
    lineEdit = """
        QLineEdit {
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
            background-color: #FFFFFF;
            color: #333333; 
            font-size: 14px; 
            font-family: \"Microsoft YaHei\", sans-serif; 
            box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.05);
            min-height: 32px;
        } 
    """
    loading = """
        QPushButton#loading {
            background-color: rgb(12, 162, 255); 
            color: rgb(255, 255, 255);
            border: none;
            border-radius: 10px;
            padding: 6px 12px;
        }
        QPushButton#loading:hover:enabled {
            background-color: rgb(12, 165, 220); 
        }
        QPushButton#loading:pressed:enabled {
            background-color: rgb(12, 170, 200); 
        }
        QPushButton#loading:disabled {
            background-color: rgba(12, 162, 255, 0.5); 
            color: rgba(255, 255, 255, 0.7); 
            border: none;
        }
    """

regiseter = """
    QMainWindow { 
        background: #f5f9fd; 
    }
    
    QLabel { 
        color: #263247; 
        font-family: "Microsoft YaHei"; 
    }

    QLineEdit {
        border: none;
        border-radius: 6px;
        padding: 6px 10px;
        background: #ffffff;
        color: #333333;
        font-size: 14px;
        min-height: 32px;
    }
    
    QPushButton#registerButton {
        background-color: rgb(12, 162, 255);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 6px 12px;
    }
    
    QPushButton#registerButton:disabled {
        background-color: rgba(12, 162, 255, 0.5);
    }
    
    QPushButton#backButton, QToolButton#closeButton {
        border: none;
        color: rgb(0, 179, 255);
        background: transparent;
    }
"""