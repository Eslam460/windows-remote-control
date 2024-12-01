import sys
import os
import ctypes
import win32security
import win32api
import win32con
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                           QVBoxLayout, QWidget, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import pyrebase
import psutil
from config import FIREBASE_CONFIG
import threading
import time

class WindowsController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("التحكم في Windows")
        self.setGeometry(100, 100, 600, 400)
        
        # إعداد Firebase
        self.firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        self.db = self.firebase.database()
        
        # بدء مراقبة الأوامر
        self.start_command_listener()
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # إضافة العنوان
        title = QLabel("لوحة التحكم في Windows")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #2c3e50;
                margin: 20px;
            }
        """)
        layout.addWidget(title)
        
        # إضافة حالة الاتصال
        self.connection_label = QLabel("حالة الاتصال: متصل")
        self.connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_label)
        
        # إنشاء الأزرار
        shutdown_btn = self.create_button("إيقاف تشغيل الجهاز", self.shutdown_pc)
        restart_btn = self.create_button("إعادة تشغيل الجهاز", self.restart_pc)
        lock_btn = self.create_button("قفل الجهاز", self.lock_pc)
        
        # إضافة الأزرار إلى Layout
        layout.addWidget(shutdown_btn)
        layout.addWidget(restart_btn)
        layout.addWidget(lock_btn)
        
        central_widget.setLayout(layout)
        
        # تطبيق النمط
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px;
                margin: 10px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
    
    def create_button(self, text, function):
        button = QPushButton(text)
        button.clicked.connect(function)
        return button
    
    def shutdown_pc(self):
        if self.show_confirmation("هل أنت متأكد من إيقاف تشغيل الجهاز؟"):
            self.execute_command("shutdown")
    
    def restart_pc(self):
        if self.show_confirmation("هل أنت متأكد من إعادة تشغيل الجهاز؟"):
            self.execute_command("restart")
    
    def lock_pc(self):
        self.execute_command("lock")
    
    def show_confirmation(self, message):
        reply = QMessageBox.question(self, 'تأكيد', message,
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes
    
    def execute_command(self, command):
        if command == "shutdown":
            os.system("shutdown /s /t 0")
        elif command == "restart":
            os.system("shutdown /r /t 0")
        elif command == "lock":
            ctypes.windll.user32.LockWorkStation()
            
    def start_command_listener(self):
        def listen_for_commands():
            while True:
                try:
                    # مراقبة الأوامر في Firebase
                    commands = self.db.child("commands").get()
                    if commands.val():
                        for command in commands.each():
                            cmd_data = command.val()
                            if not cmd_data.get("executed", False):
                                # تنفيذ الأمر
                                self.execute_command(cmd_data["command"])
                                # تحديث حالة الأمر
                                self.db.child("commands").child(command.key()).update({"executed": True})
                    time.sleep(1)
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(5)
        
        # بدء المراقبة في thread منفصل
        thread = threading.Thread(target=listen_for_commands, daemon=True)
        thread.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # دعم اللغة العربية
    window = WindowsController()
    window.show()
    sys.exit(app.exec_())
