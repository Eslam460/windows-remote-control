import sys
import os
import psutil
import win32gui
import win32con
import win32api
import cv2
import base64
import time
import screen_brightness_control as sbc
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyrebase
from config import FIREBASE_CONFIG

class CameraThread(QThread):
    frame_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.streaming = False

    def run(self):
        cap = cv2.VideoCapture(0)
        while self.running:
            if self.streaming:
                ret, frame = cap.read()
                if ret:
                    # تحويل الإطار إلى JPG ثم إلى Base64
                    _, buffer = cv2.imencode('.jpg', frame)
                    jpg_as_text = base64.b64encode(buffer).decode()
                    self.frame_ready.emit(jpg_as_text)
            time.sleep(0.1)
        cap.release()

    def stop(self):
        self.running = False
        self.wait()

    def toggle_streaming(self, state):
        self.streaming = state

class WindowsController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("التحكم في Windows")
        self.setGeometry(100, 100, 600, 400)
        
        # إعداد Firebase
        self.firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        self.db = self.firebase.database()
        
        # إعداد الكاميرا
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.start()

        # إعداد التحكم في الصوت
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = interface.QueryInterface(IAudioEndpointVolume)

        # بدء الاستماع للأوامر
        self.start_command_listener()

        # إعداد الواجهة
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
        monitor_off_btn = self.create_button("إيقاف الشاشة", self.monitor_off)
        monitor_on_btn = self.create_button("تشغيل الشاشة", self.monitor_on)
        camera_btn = self.create_button("تشغيل الكاميرا", self.start_camera)
        stop_camera_btn = self.create_button("إيقاف الكاميرا", self.stop_camera)
        system_info_btn = self.create_button("معلومات النظام", self.get_system_info)
        
        # إضافة الأزرار إلى Layout
        layout.addWidget(shutdown_btn)
        layout.addWidget(restart_btn)
        layout.addWidget(lock_btn)
        layout.addWidget(monitor_off_btn)
        layout.addWidget(monitor_on_btn)
        layout.addWidget(camera_btn)
        layout.addWidget(stop_camera_btn)
        layout.addWidget(system_info_btn)
        
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
    
    def monitor_off(self):
        self.execute_command("monitor_off")
    
    def monitor_on(self):
        self.execute_command("monitor_on")
    
    def start_camera(self):
        self.execute_command("start_camera")
    
    def stop_camera(self):
        self.execute_command("stop_camera")
    
    def get_system_info(self):
        self.execute_command("get_system_info")
    
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
            win32gui.LockWorkStation()
        elif command == "monitor_off":
            win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 2)
        elif command == "monitor_on":
            win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, -1)
        elif command == "start_camera":
            self.camera_thread.toggle_streaming(True)
        elif command == "stop_camera":
            self.camera_thread.toggle_streaming(False)
        elif command == "get_system_info":
            self.update_system_info()
    
    def start_command_listener(self):
        def stream_handler(message):
            if message["data"] is None:
                return

            command = message["data"].get("command")
            if command == "shutdown":
                os.system("shutdown /s /t 1")
            elif command == "restart":
                os.system("shutdown /r /t 1")
            elif command == "lock":
                win32gui.LockWorkStation()
            elif command == "monitor_off":
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 2)
            elif command == "monitor_on":
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, -1)
            elif command.startswith("set_volume_"):
                volume_level = float(command.split("_")[2])
                self.volume.SetMasterVolumeLevelScalar(volume_level / 100, None)
            elif command.startswith("set_brightness_"):
                brightness_level = int(command.split("_")[2])
                sbc.set_brightness(brightness_level)
            elif command == "start_camera":
                self.camera_thread.toggle_streaming(True)
            elif command == "stop_camera":
                self.camera_thread.toggle_streaming(False)
            elif command == "get_system_info":
                self.update_system_info()

        self.db.child("commands").stream(stream_handler)

    def update_camera_frame(self, frame_data):
        self.db.child("camera_feed").set({"frame": frame_data})

    def update_system_info(self):
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "battery_percent": psutil.sensors_battery().percent if psutil.sensors_battery() else "N/A"
        }
        
        self.db.child("system_info").set(system_info)

    def closeEvent(self, event):
        self.camera_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # دعم اللغة العربية
    window = WindowsController()
    window.show()
    sys.exit(app.exec_())
