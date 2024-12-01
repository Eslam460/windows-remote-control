from datetime import datetime, timedelta
import jwt
from config import Config
from loguru import logger

class SecurityManager:
    def __init__(self):
        self.login_attempts = {}
        self.blocked_ips = set()
        
    def generate_token(self, user_id: str) -> str:
        """Generate a secure JWT token for user authentication"""
        try:
            expiry = datetime.utcnow() + timedelta(seconds=Config.ACCESS_TOKEN_EXPIRY)
            token = jwt.encode(
                {
                    'user_id': user_id,
                    'exp': expiry
                },
                Config.ENCRYPTION_KEY,
                algorithm='HS256'
            )
            logger.info(f"Generated token for user: {user_id}")
            return token
        except Exception as e:
            logger.error(f"Error generating token: {str(e)}")
            raise

    def validate_token(self, token: str) -> bool:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, Config.ENCRYPTION_KEY, algorithms=['HS256'])
            return True
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return False
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return False

    def check_login_attempts(self, ip_address: str) -> bool:
        """Check if IP is allowed to attempt login"""
        if ip_address in self.blocked_ips:
            return False
            
        current_time = datetime.utcnow()
        if ip_address in self.login_attempts:
            attempts = self.login_attempts[ip_address]
            if len(attempts) >= Config.MAX_LOGIN_ATTEMPTS:
                if (current_time - attempts[0]).total_seconds() < 3600:
                    self.blocked_ips.add(ip_address)
                    logger.warning(f"IP blocked due to multiple failed attempts: {ip_address}")
                    return False
                else:
                    self.login_attempts[ip_address] = []
        
        return True

    def record_login_attempt(self, ip_address: str, success: bool):
        """Record login attempt"""
        if success:
            self.login_attempts.pop(ip_address, None)
            return
            
        current_time = datetime.utcnow()
        if ip_address not in self.login_attempts:
            self.login_attempts[ip_address] = []
        self.login_attempts[ip_address].append(current_time)
        
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_str:
            return ""
        # Remove potentially dangerous characters
        sanitized = ''.join(char for char in input_str if char.isalnum() or char in ' -_.')
        return sanitized[:255]  # Limit length

    def validate_command(self, command: str) -> bool:
        """Validate system commands before execution"""
        allowed_commands = {'shutdown', 'restart', 'lock', 'sleep', 'hibernate'}
        return command.lower() in allowed_commands
