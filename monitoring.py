import psutil
from datetime import datetime
from loguru import logger
import json

class SystemMonitor:
    def __init__(self):
        self.performance_logs = []
        
    def get_system_status(self) -> dict:
        """Get current system status"""
        try:
            status = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': datetime.now().isoformat()
            }
            self.performance_logs.append(status)
            return status
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {}

    def log_action(self, action: str, user: str, status: str, details: str = None):
        """Log system actions"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'user': user,
                'status': status,
                'details': details
            }
            logger.info(json.dumps(log_entry))
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")

    def check_system_health(self) -> bool:
        """Check if system resources are within acceptable limits"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Define thresholds
            is_healthy = (
                cpu_percent < 90 and
                memory_percent < 90 and
                disk_percent < 90
            )
            
            if not is_healthy:
                logger.warning(
                    f"System resources critical: CPU={cpu_percent}%, "
                    f"Memory={memory_percent}%, Disk={disk_percent}%"
                )
            
            return is_healthy
        except Exception as e:
            logger.error(f"Error checking system health: {str(e)}")
            return False

    def cleanup_old_logs(self, days: int = 30):
        """Clean up old performance logs"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            self.performance_logs = [
                log for log in self.performance_logs
                if datetime.fromisoformat(log['timestamp']) > cutoff_date
            ]
        except Exception as e:
            logger.error(f"Error cleaning up logs: {str(e)}")

    def get_performance_report(self) -> dict:
        """Generate performance report"""
        try:
            if not self.performance_logs:
                return {}
                
            cpu_values = [log['cpu_percent'] for log in self.performance_logs]
            memory_values = [log['memory_percent'] for log in self.performance_logs]
            
            return {
                'avg_cpu': sum(cpu_values) / len(cpu_values),
                'avg_memory': sum(memory_values) / len(memory_values),
                'max_cpu': max(cpu_values),
                'max_memory': max(memory_values),
                'log_count': len(self.performance_logs)
            }
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {}
