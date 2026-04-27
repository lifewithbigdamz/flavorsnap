"""
Advanced Logger Configuration for FlavorSnap
Implements structured logging with multiple outputs, levels, and analysis capabilities
"""

import logging
import logging.config
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process,
            'extra': getattr(record, 'extra', {})
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': type(record.exc_info).__name__,
                'message': str(record.exc_info),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)
    
    def formatException(self, exc_info):
        """Format exception information"""
        import traceback
        return traceback.format_exception(exc_info)

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class LoggerManager:
    """Advanced logger manager for FlavorSnap"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.loggers = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path(self.config.get('log_dir', '/app/logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'structured': {
                    '()': StructuredFormatter,
                    'format': 'json'
                },
                'colored': {
                    '()': ColoredFormatter,
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
                'detailed': {
                    '()': logging.Formatter,
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': self.config.get('console_level', 'INFO'),
                    'formatter': 'colored',
                    'stream': sys.stdout
                },
                'console_error': {
                    'class': 'logging.StreamHandler',
                    'level': 'ERROR',
                    'formatter': 'colored',
                    'stream': sys.stderr
                },
                'file_structured': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': self.config.get('file_level', 'DEBUG'),
                    'formatter': 'structured',
                    'filename': str(log_dir / 'structured.log'),
                    'maxBytes': 100 * 1024 * 1024,  # 100MB
                    'backupCount': 5,
                    'encoding': 'utf-8'
                },
                'file_detailed': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': self.config.get('file_level', 'DEBUG'),
                    'formatter': 'detailed',
                    'filename': str(log_dir / 'detailed.log'),
                    'maxBytes': 50 * 1024 * 1024,  # 50MB
                    'backupCount': 3,
                    'encoding': 'utf-8'
                },
                'file_error': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'ERROR',
                    'formatter': 'structured',
                    'filename': str(log_dir / 'error.log'),
                    'maxBytes': 20 * 1024 * 1024,  # 20MB
                    'backupCount': 5,
                    'encoding': 'utf-8'
                },
                'file_audit': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'structured',
                    'filename': str(log_dir / 'audit.log'),
                    'maxBytes': 30 * 1024 * 1024,  # 30MB
                    'backupCount': 10,
                    'encoding': 'utf-8'
                },
                'file_performance': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'structured',
                    'filename': str(log_dir / 'performance.log'),
                    'maxBytes': 40 * 1024 * 1024,  # 40MB
                    'backupCount': 5,
                    'encoding': 'utf-8'
                },
                'file_security': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'structured',
                    'filename': str(log_dir / 'security.log'),
                    'maxBytes': 25 * 1024 * 1024,  # 25MB
                    'backupCount': 10,
                    'encoding': 'utf-8'
                }
            },
            'loggers': {
                '': {
                    'level': self.config.get('root_level', 'INFO'),
                    'handlers': ['console', 'file_structured', 'file_error']
                },
                'flavorsnap.app': {
                    'level': self.config.get('app_level', 'INFO'),
                    'handlers': ['file_structured'],
                    'propagate': False
                },
                'flavorsnap.api': {
                    'level': self.config.get('api_level', 'INFO'),
                    'handlers': ['file_structured', 'file_performance'],
                    'propagate': False
                },
                'flavorsnap.ml': {
                    'level': self.config.get('ml_level', 'INFO'),
                    'handlers': ['file_structured', 'file_performance'],
                    'propagate': False
                },
                'flavorsnap.security': {
                    'level': self.config.get('security_level', 'INFO'),
                    'handlers': ['file_security', 'file_audit'],
                    'propagate': False
                },
                'flavorsnap.performance': {
                    'level': self.config.get('performance_level', 'INFO'),
                    'handlers': ['file_performance'],
                    'propagate': False
                },
                'flavorsnap.audit': {
                    'level': self.config.get('audit_level', 'INFO'),
                    'handlers': ['file_audit'],
                    'propagate': False
                },
                'uvicorn': {
                    'level': self.config.get('uvicorn_level', 'INFO'),
                    'handlers': ['file_structured'],
                    'propagate': False
                },
                'sqlalchemy': {
                    'level': self.config.get('sqlalchemy_level', 'WARNING'),
                    'handlers': ['file_structured'],
                    'propagate': False
                }
            }
        }
        
        # Apply configuration
        logging.config.dictConfig(logging_config)
        
        # Store loggers for easy access
        for logger_name in logging_config['loggers'].keys():
            self.loggers[logger_name] = logging.getLogger(logger_name)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a specific logger"""
        return self.loggers.get(name, logging.getLogger(name))
    
    def set_level(self, logger_name: str, level: str):
        """Set logging level for a specific logger"""
        logger = self.get_logger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
    
    def add_context(self, logger_name: str, **context):
        """Add context to all future log messages"""
        logger = self.get_logger(logger_name)
        logger = logging.LoggerAdapter(logger, context)
        return logger

# Global logger manager instance
_logger_manager = None

def setup_logging(config: Optional[Dict[str, Any]] = None):
    """Setup global logging configuration"""
    global _logger_manager
    
    if config is None:
        config = {
            'log_dir': os.getenv('LOG_DIR', '/app/logs'),
            'console_level': os.getenv('LOG_LEVEL', 'INFO'),
            'file_level': os.getenv('FILE_LOG_LEVEL', 'DEBUG'),
            'root_level': os.getenv('ROOT_LOG_LEVEL', 'INFO'),
            'app_level': os.getenv('APP_LOG_LEVEL', 'INFO'),
            'api_level': os.getenv('API_LOG_LEVEL', 'INFO'),
            'ml_level': os.getenv('ML_LOG_LEVEL', 'INFO'),
            'security_level': os.getenv('SECURITY_LOG_LEVEL', 'INFO'),
            'performance_level': os.getenv('PERFORMANCE_LOG_LEVEL', 'INFO'),
            'audit_level': os.getenv('AUDIT_LOG_LEVEL', 'INFO'),
            'uvicorn_level': os.getenv('UVICORN_LOG_LEVEL', 'INFO'),
            'sqlalchemy_level': os.getenv('SQLALCHEMY_LOG_LEVEL', 'WARNING')
        }
    
    _logger_manager = LoggerManager(config)
    return _logger_manager

def get_logger(name: str = '') -> logging.Logger:
    """Get a logger instance"""
    if _logger_manager is None:
        setup_logging()
    
    if name:
        return _logger_manager.get_logger(name)
    else:
        return logging.getLogger()

# Convenience functions
def debug(message: str, **kwargs):
    """Log debug message"""
    get_logger().debug(message, **kwargs)

def info(message: str, **kwargs):
    """Log info message"""
    get_logger().info(message, **kwargs)

def warning(message: str, **kwargs):
    """Log warning message"""
    get_logger().warning(message, **kwargs)

def error(message: str, **kwargs):
    """Log error message"""
    get_logger().error(message, **kwargs)

def critical(message: str, **kwargs):
    """Log critical message"""
    get_logger().critical(message, **kwargs)

# Module-specific loggers
def get_app_logger() -> logging.Logger:
    """Get application logger"""
    return get_logger('flavorsnap.app')

def get_api_logger() -> logging.Logger:
    """Get API logger"""
    return get_logger('flavorsnap.api')

def get_ml_logger() -> logging.Logger:
    """Get ML logger"""
    return get_logger('flavorsnap.ml')

def get_security_logger() -> logging.Logger:
    """Get security logger"""
    return get_logger('flavorsnap.security')

def get_performance_logger() -> logging.Logger:
    """Get performance logger"""
    return get_logger('flavorsnap.performance')

def get_audit_logger() -> logging.Logger:
    """Get audit logger"""
    return get_logger('flavorsnap.audit')

def get_uvicorn_logger() -> logging.Logger:
    """Get uvicorn logger"""
    return get_logger('uvicorn')

# Context-aware logging
def log_with_context(logger_name: str, message: str, context: Dict[str, Any]):
    """Log message with context"""
    logger = get_logger(logger_name)
    logger = logging.LoggerAdapter(logger, context)
    logger.info(message)

# Performance logging decorator
def log_performance(func_name: str = None):
    """Decorator to log function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                perf_logger = get_performance_logger()
                perf_logger.info(
                    f"Function {func_name or func.__name__} completed",
                    extra={
                        'function': func_name or func.__name__,
                        'duration': duration,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs),
                        'success': True
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                perf_logger = get_performance_logger()
                perf_logger.error(
                    f"Function {func_name or func.__name__} failed",
                    extra={
                        'function': func_name or func.__name__,
                        'duration': duration,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs),
                        'success': False,
                        'error': str(e)
                    }
                )
                
                raise e
        
        return wrapper
    return decorator

# Security logging
def log_security_event(event_type: str, user_id: str = None, ip_address: str = None, 
                    details: Dict[str, Any] = None, severity: str = 'INFO'):
    """Log security event"""
    security_logger = get_security_logger()
    
    security_event = {
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat(),
        'severity': severity,
        'details': details or {}
    }
    
    security_logger.info(
        f"Security event: {event_type}",
        extra={'security_event': security_event}
    )

# Audit logging
def log_audit_event(action: str, resource: str, user_id: str = None, 
                result: str = 'SUCCESS', details: Dict[str, Any] = None):
    """Log audit event"""
    audit_logger = get_audit_logger()
    
    audit_event = {
        'action': action,
        'resource': resource,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
        'result': result,
        'details': details or {}
    }
    
    audit_logger.info(
        f"Audit event: {action} on {resource}",
        extra={'audit_event': audit_event}
    )

# Error tracking
def track_error(error: Exception, context: Dict[str, Any] = None):
    """Track error with context"""
    error_logger = get_logger('flavorsnap.app')
    
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or {},
        'timestamp': datetime.utcnow().isoformat(),
        'traceback': str(error.__traceback__) if hasattr(error, '__traceback__') else None
    }
    
    error_logger.error(
        f"Error tracked: {type(error).__name__}",
        extra={'error_data': error_data},
        exc_info=True
    )

# Request logging
def log_request(method: str, path: str, user_id: str = None, 
              ip_address: str = None, user_agent: str = None,
              status_code: int = None, response_time: float = None,
              request_id: str = None):
    """Log HTTP request"""
    api_logger = get_api_logger()
    
    request_data = {
        'method': method,
        'path': path,
        'user_id': user_id,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'status_code': status_code,
        'response_time': response_time,
        'request_id': request_id,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    api_logger.info(
        f"Request: {method} {path}",
        extra={'request_data': request_data}
    )

# Business logic logging
def log_business_event(event_name: str, data: Dict[str, Any] = None, 
                     user_id: str = None, importance: str = 'INFO'):
    """Log business event"""
    app_logger = get_app_logger()
    
    business_event = {
        'event_name': event_name,
        'data': data or {},
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
        'importance': importance
    }
    
    app_logger.info(
        f"Business event: {event_name}",
        extra={'business_event': business_event}
    )

# ML model logging
def log_ml_event(event_type: str, model_name: str, data: Dict[str, Any] = None,
               metrics: Dict[str, float] = None):
    """Log ML model event"""
    ml_logger = get_ml_logger()
    
    ml_event = {
        'event_type': event_type,
        'model_name': model_name,
        'data': data or {},
        'metrics': metrics or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    ml_logger.info(
        f"ML event: {event_type} for model {model_name}",
        extra={'ml_event': ml_event}
    )

# Compliance logging
def log_compliance_event(regulation: str, event_type: str, data: Dict[str, Any] = None):
    """Log compliance event"""
    audit_logger = get_audit_logger()
    
    compliance_event = {
        'regulation': regulation,
        'event_type': event_type,
        'data': data or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    audit_logger.info(
        f"Compliance event: {event_type} under {regulation}",
        extra={'compliance_event': compliance_event}
    )

# Initialize logging on import
if __name__ == "__main__":
    # Test logging configuration
    setup_logging()
    
    # Test different loggers
    get_app_logger().info("Application logger initialized")
    get_api_logger().info("API logger initialized")
    get_security_logger().info("Security logger initialized")
    get_performance_logger().info("Performance logger initialized")
    get_audit_logger().info("Audit logger initialized")
    
    # Test structured logging
    get_api_logger().info(
        "Test structured log",
        extra={
            'request_id': 'test-123',
            'user_id': 'test-user',
            'method': 'GET',
            'path': '/test'
        }
    )
    
    # Test security logging
    log_security_event(
        event_type='test_access',
        user_id='test-user',
        ip_address='192.168.1.1',
        details={'test': True}
    )
    
    # Test performance logging
    @log_performance('test_function')
    def test_function():
        import time
        time.sleep(0.1)
        return "test result"
    
    test_function()
