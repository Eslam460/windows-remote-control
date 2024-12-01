import pytest
import os
from dotenv import load_dotenv
from config import Config

@pytest.fixture
def setup_env():
    """Setup test environment variables"""
    os.environ["FIREBASE_API_KEY"] = "test_key"
    os.environ["FIREBASE_AUTH_DOMAIN"] = "test.firebaseapp.com"
    os.environ["FIREBASE_DATABASE_URL"] = "https://test.firebaseio.com"
    os.environ["ENCRYPTION_KEY"] = "test_encryption_key"
    load_dotenv()
    yield
    # Cleanup
    for key in ["FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_DATABASE_URL", "ENCRYPTION_KEY"]:
        os.environ.pop(key, None)

def test_config_validation(setup_env):
    """Test configuration validation"""
    Config.validate_config()
    assert Config.FIREBASE_CONFIG["apiKey"] == "test_key"

def test_encryption_decryption(setup_env):
    """Test data encryption and decryption"""
    test_data = "sensitive_data"
    encrypted = Config.encrypt_data(test_data)
    decrypted = Config.decrypt_data(encrypted)
    assert decrypted == test_data
    assert encrypted != test_data

def test_missing_config():
    """Test configuration validation with missing variables"""
    with pytest.raises(ValueError):
        Config.validate_config()
