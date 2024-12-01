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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QGridLayout, 
                              QWidget, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyrebase
from config import Config
from datetime import datetime
FIREBASE_CONFIG = Config.FIREBASE_CONFIG

class CameraThread(QThread):
    frame_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.streaming = False
        self.cap = None
        self.frame_interval = 0.016  # ~60 FPS
        self.last_frame_time = 0
        self.quality = 80  # جودة أعلى للصورة

    def run(self):
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # استخدام DirectShow للأداء الأفضل
            if not self.cap.isOpened():
                print("خطأ: لا يمكن فتح الكاميرا")
                return

            # تحسين إعدادات الكاميرا للبث المباشر
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 60)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
            while self.running:
                if self.streaming:
                    current_time = time.time()
                    if current_time - self.last_frame_time >= self.frame_interval:
                        ret, frame = self.cap.read()
                        if ret:
                            # تحسين جودة الصورة للبث المباشر
                            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                            _, buffer = cv2.imencode('.jpg', frame, encode_params)
                            jpg_as_text = base64.b64encode(buffer).decode()
                            self.frame_ready.emit(jpg_as_text)
                            self.last_frame_time = current_time
                    else:
                        # انتظار قصير جداً
                        time.sleep(0.001)
                else:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"خطأ في thread الكاميرا: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()

    def stop(self):
        self.running = False
        self.streaming = False
        self.wait()
        if self.cap:
            self.cap.release()

    def toggle_streaming(self, state):
        self.streaming = state
        if not state and self.cap:
            # إعادة تعيين الإعدادات عند إيقاف البث
            self.quality = 80
            self.last_frame_time = 0

class WindowsController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("التحكم في Windows")
        self.setGeometry(100, 100, 600, 400)
        
        # إعداد الواجهة أولاً
        self.setup_ui()
        
        # تهيئة المتغيرات
        self.firebase = None
        self.db = None
        self.camera_thread = None
        self.volume = None
        
        # محاولة الاتصال بالخدمات
        self.initialize_services()
        
    def initialize_services(self):
        try:
            # إعداد Firebase
            self.firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
            self.db = self.firebase.database()
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Firebase initialization error: {str(e)}")
            self.db = None
        
        try:
            # إعداد الكاميرا
            self.camera_thread = CameraThread()
            self.camera_thread.frame_ready.connect(self.update_camera_frame)
            self.camera_thread.start()
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Camera initialization error: {str(e)}")
            self.camera_thread = None

        try:
            # إعداد التحكم في الصوت
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume = interface.QueryInterface(IAudioEndpointVolume)
            print("Audio initialized successfully")
        except Exception as e:
            print(f"Audio initialization error: {str(e)}")
            self.volume = None

        # بدء الاستماع للأوامر
        if self.db:
            self.start_command_listener()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # تحسين التخطيط باستخدام Grid
        layout = QGridLayout()
        
        # إضافة العنوان
        title = QLabel("لوحة التحكم")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin: 15px;
                padding: 10px;
                background: #ecf0f1;
                border-radius: 10px;
            }
        """)
        layout.addWidget(title, 0, 0, 1, 2)
        
        # إنشاء الأزرار مع تصميم جديد
        buttons_data = [
            ("إيقاف تشغيل", self.shutdown_pc, "#e74c3c"),
            ("إعادة تشغيل", self.restart_pc, "#e67e22"),
            ("قفل الجهاز", self.lock_pc, "#f1c40f"),
            ("إيقاف الشاشة", self.monitor_off, "#2ecc71"),
            ("تشغيل الشاشة", self.monitor_on, "#27ae60"),
            ("تشغيل الكاميرا", self.start_camera, "#3498db"),
            ("إيقاف الكاميرا", self.stop_camera, "#2980b9"),
            ("معلومات النظام", self.get_system_info, "#9b59b6")
        ]
        
        row = 1
        col = 0
        for text, func, color in buttons_data:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 15px;
                    margin: 8px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {color}dd;
                    transform: scale(1.05);
                }}
                QPushButton:pressed {{
                    background-color: {color}aa;
                }}
            """)
            layout.addWidget(btn, row, col)
            col = (col + 1) % 2
            if col == 0:
                row += 1
        
        # إضافة مؤشر الحالة
        self.status_label = QLabel("جاري التحميل...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 14px;
                margin: 10px;
            }
        """)
        layout.addWidget(self.status_label, row + 1, 0, 1, 2)
        
        central_widget.setLayout(layout)
        
        # تطبيق النمط العام
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QWidget {
                font-family: Arial;
            }
        """)
        
        # تحسين حجم النافذة
        self.setMinimumSize(500, 600)
        
    def shutdown_pc(self):
        os.system("shutdown /s /t 0")
    
    def restart_pc(self):
        os.system("shutdown /r /t 0")
    
    def lock_pc(self):
        win32gui.LockWorkStation()
    
    def monitor_off(self):
        try:
            # محاولة إطفاء الشاشة باستخدام أكثر من طريقة
            try:
                # الطريقة الأولى: استخدام WM_SYSCOMMAND
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 2)
            except Exception:
                # الطريقة الثانية: استخدام PowerShell
                os.system('powershell (Add-Type "[DllImport(\\\"user32.dll\\\")] public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);" -Name "Win32SendMessage" -Namespace Win32Functions -PassThru)::Win32SendMessage(-1, 0x0112, 0xF170, 2)')
            
            # تحديث حالة الشاشة في Firebase
            if self.db:
                self.db.child("monitor_status").set({"state": "off", "timestamp": datetime.now().isoformat()})
                
        except Exception as e:
            print(f"Error turning monitor off: {str(e)}")
            self.show_popup_message({"message": "حدث خطأ أثناء محاولة إطفاء الشاشة", "duration": 5})

    def monitor_on(self):
        try:
            # محاولة تشغيل الشاشة باستخدام أكثر من طريقة
            try:
                # الطريقة الأولى: تحريك الماوس
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -1, 0, 0)
            except Exception:
                pass
            
            try:
                # الطريقة الثانية: إرسال رسالة تشغيل الشاشة
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, -1)
            except Exception:
                # الطريقة الثالثة: استخدام PowerShell
                os.system('powershell (Add-Type "[DllImport(\\\"user32.dll\\\")] public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);" -Name "Win32SendMessage" -Namespace Win32Functions -PassThru)::Win32SendMessage(-1, 0x0112, 0xF170, -1)')
            
            # تحديث حالة الشاشة في Firebase
            if self.db:
                self.db.child("monitor_status").set({"state": "on", "timestamp": datetime.now().isoformat()})
                
        except Exception as e:
            print(f"Error turning monitor on: {str(e)}")
            self.show_popup_message({"message": "حدث خطأ أثناء محاولة تشغيل الشاشة", "duration": 5})
    
    def start_camera(self):
        self.execute_command("start_camera")
    
    def stop_camera(self):
        self.execute_command("stop_camera")
    
    def get_system_info(self):
        self.execute_command("get_system_info")
    
    def show_popup_message(self, popup_data):
        """عرض رسالة منبثقة مع إمكانية الاختفاء التلقائي"""
        try:
            message = popup_data.get("message", "")
            duration = popup_data.get("duration", 10)  # المدة الافتراضية 10 ثواني
            
            # إنشاء نافذة منبثقة
            popup = QMessageBox(self)
            popup.setWindowTitle("رسالة")
            popup.setText(message)
            popup.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
            
            # تعيين النمط
            popup.setStyleSheet("""
                QMessageBox {
                    background-color: #2c3e50;
                    color: white;
                    border-radius: 10px;
                    padding: 20px;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                }
            """)
            
            # عرض الرسالة
            popup.show()
            
            # إعداد مؤقت لإغلاق الرسالة
            QTimer.singleShot(duration * 1000, popup.close)
            
        except Exception as e:
            print(f"Error showing popup: {str(e)}")

    def update_camera_frame(self, frame_data):
        if self.db:
            self.db.child("camera_feed").set({"frame": frame_data})

    def update_system_info(self):
        try:
            # CPU معلومات
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            
            # الذاكرة معلومات
            memory = psutil.virtual_memory()
            
            # القرص الصلب معلومات
            disk = psutil.disk_usage('/')
            
            # معلومات البطارية
            battery = psutil.sensors_battery()
            battery_info = {
                "percent": battery.percent if battery else "N/A",
                "power_plugged": battery.power_plugged if battery else "N/A",
                "time_left": str(battery.secsleft) if battery and battery.secsleft != -1 else "N/A"
            }
            
            # معلومات الشبكة
            network = psutil.net_io_counters()
            
            system_info = {
                "cpu": {
                    "percent": cpu_percent,
                    "frequency_current": round(cpu_freq.current, 2),
                    "frequency_max": round(cpu_freq.max, 2),
                    "cores": cpu_count
                },
                "memory": {
                    "total": round(memory.total / (1024 ** 3), 2),  # GB
                    "available": round(memory.available / (1024 ** 3), 2),  # GB
                    "percent": memory.percent,
                    "used": round(memory.used / (1024 ** 3), 2)  # GB
                },
                "disk": {
                    "total": round(disk.total / (1024 ** 3), 2),  # GB
                    "used": round(disk.used / (1024 ** 3), 2),  # GB
                    "free": round(disk.free / (1024 ** 3), 2),  # GB
                    "percent": disk.percent
                },
                "battery": battery_info,
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "timestamp": datetime.now().isoformat()
            }
            
            if self.db:
                self.db.child("system_info").set(system_info)
                
        except Exception as e:
            print(f"Error updating system info: {str(e)}")
    
    def start_command_listener(self):
        try:
            def stream_handler(message):
                if message is None or message.get("data") is None:
                    return

                command = message["data"].get("command", "")
                try:
                    if command == "shutdown":
                        os.system("shutdown /s /t 1")
                    elif command == "restart":
                        os.system("shutdown /r /t 1")
                    elif command == "lock":
                        win32gui.LockWorkStation()
                    elif command == "monitor_off":
                        self.monitor_off()
                    elif command == "monitor_on":
                        self.monitor_on()
                    elif command.startswith("set_volume_"):
                        if self.volume:
                            volume_level = float(command.split("_")[2])
                            self.volume.SetMasterVolumeLevelScalar(volume_level / 100, None)
                    elif command.startswith("set_brightness_"):
                        brightness_level = int(command.split("_")[2])
                        sbc.set_brightness(brightness_level)
                    elif command == "start_camera":
                        if self.camera_thread:
                            self.camera_thread.toggle_streaming(True)
                    elif command == "stop_camera":
                        if self.camera_thread:
                            self.camera_thread.toggle_streaming(False)
                    elif command == "get_system_info":
                        self.update_system_info()
                    elif command.startswith("show_popup_"):
                        # معالجة أمر الرسالة المنبثقة
                        popup_data = message["data"].get("popup_data", {})
                        self.show_popup_message(popup_data)
                except Exception as e:
                    print(f"Error executing command {command}: {str(e)}")

            if self.db:
                self.db.child("commands").stream(stream_handler)
        except Exception as e:
            print(f"Error in command listener: {str(e)}")

    def closeEvent(self, event):
        if self.camera_thread:
            self.camera_thread.stop()
        event.accept()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # دعم اللغة العربية
        print("Creating window...")
        window = WindowsController()
        print("Window created successfully")
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
