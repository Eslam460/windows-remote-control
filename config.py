import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from loguru import logger

# تكوين السجلات
logger.add("app.log", rotation="500 MB", retention="10 days", level="INFO")

class Config:
    # تكوين Firebase
    FIREBASE_CONFIG = {
        "apiKey": "AIzaSyDjjOAoVDLih9mAy6BSSmtghHTOV3TkGLg",
        "authDomain": "pcandfon.firebaseapp.com",
        "databaseURL": "https://pcandfon-default-rtdb.firebaseio.com",
        "projectId": "pcandfon",
        "storageBucket": "pcandfon.firebasestorage.app",
        "messagingSenderId": "1063272939698",
        "appId": "1:1063272939698:web:2aec7f3b1c3ec5efb809ab",
        "measurementId": "G-LVBGZ3Z2FS"
    }

    # تكوين الأمان
    ENCRYPTION_KEY = b'E0f0OqvFOw9AjXCNqVU7fB-6zBBa34TfT76QBG_gLGI='
    cipher_suite = Fernet(ENCRYPTION_KEY)
    ACCESS_TOKEN_EXPIRY = 3600
    MAX_LOGIN_ATTEMPTS = 3

    # تكوين التطبيق
    DEBUG_MODE = False
    APP_NAME = "Windows Controller"
    VERSION = "2.0.0"

    @staticmethod
    def encrypt_data(data: str) -> str:
        """تشفير البيانات الحساسة"""
        if Config.cipher_suite:
            return Config.cipher_suite.encrypt(data.encode()).decode()
        return data

    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """فك تشفير البيانات"""
        if Config.cipher_suite:
            return Config.cipher_suite.decrypt(encrypted_data.encode()).decode()
        return encrypted_data

    @staticmethod
    def validate_config():
        """التحقق من صحة الإعدادات"""
        try:
            # التحقق من تكوين Firebase
            required_firebase_keys = ["apiKey", "authDomain", "databaseURL"]
            for key in required_firebase_keys:
                if key not in Config.FIREBASE_CONFIG or not Config.FIREBASE_CONFIG[key]:
                    raise ValueError(f"Missing required Firebase configuration: {key}")

            # التحقق من مفتاح التشفير
            if not Config.ENCRYPTION_KEY:
                raise ValueError("Missing encryption key")

            # اختبار التشفير
            test_data = "test"
            encrypted = Config.encrypt_data(test_data)
            decrypted = Config.decrypt_data(encrypted)
            if decrypted != test_data:
                raise ValueError("Encryption test failed")

            logger.info("Configuration validation successful")
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            raise

# التحقق من الإعدادات عند استيراد الوحدة
Config.validate_config()
