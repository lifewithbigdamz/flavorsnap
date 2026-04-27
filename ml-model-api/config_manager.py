#!/usr/bin/env python3
"""
Advanced Configuration Manager for FlavorSnap
Implements comprehensive configuration management with validation, secrets management, hot reloading, and monitoring
"""

import os
import json
import yaml
import logging
import asyncio
import hashlib
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import watchdog.observers
import watchdog.events
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets
import prometheus_client as prom
from pydantic import BaseModel, ValidationError, validator
from functools import wraps
import copy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigStatus(Enum):
    ACTIVE = "active"
    LOADING = "loading"
    ERROR = "error"
    VALIDATING = "validating"

class ConfigChangeType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RELOAD = "reload"

@dataclass
class ConfigChange:
    """Configuration change record"""
    timestamp: datetime
    change_type: ConfigChangeType
    key: str
    old_value: Any
    new_value: Any
    source: str
    user: Optional[str] = None
    version: int = 0

@dataclass
class ConfigVersion:
    """Configuration version record"""
    version: int
    timestamp: datetime
    config_hash: str
    changes: List[ConfigChange]
    author: str
    description: str

class PrometheusMetrics:
    """Prometheus metrics for configuration management"""
    
    def __init__(self):
        self.config_loads_total = prom.Counter(
            'config_loads_total',
            'Total number of configuration loads',
            ['environment', 'status']
        )
        
        self.config_changes_total = prom.Counter(
            'config_changes_total',
            'Total number of configuration changes',
            ['change_type', 'environment']
        )
        
        self.config_validation_errors_total = prom.Counter(
            'config_validation_errors_total',
            'Total number of configuration validation errors',
            ['environment', 'validation_type']
        )
        
        self.config_reload_duration = prom.Histogram(
            'config_reload_duration_seconds',
            'Time taken to reload configuration',
            ['environment']
        )
        
        self.config_size_bytes = prom.Gauge(
            'config_size_bytes',
            'Size of configuration in bytes',
            ['environment', 'config_type']
        )
        
        self.config_last_reload_time = prom.Gauge(
            'config_last_reload_timestamp',
            'Timestamp of last configuration reload',
            ['environment']
        )

class ConfigValidator(BaseModel):
    """Pydantic model for configuration validation"""
    
    class App(BaseModel):
        name: str
        version: str
        environment: str
        debug: bool
        hot_reload: bool
        log_level: str
        
        @validator('log_level')
        def validate_log_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'log_level must be one of {valid_levels}')
            return v.upper()
    
    class Server(BaseModel):
        host: str
        port: int
        workers: int
        reload: bool
        access_log: bool
        
        @validator('port')
        def validate_port(cls, v):
            if not 1 <= v <= 65535:
                raise ValueError('port must be between 1 and 65535')
            return v
        
        @validator('workers')
        def validate_workers(cls, v):
            if v < 1:
                raise ValueError('workers must be at least 1')
            return v
    
    class Database(BaseModel):
        host: str
        port: int
        name: str
        username: str
        password: str
        pool_size: int
        max_overflow: int
        echo: bool
        
        @validator('port')
        def validate_port(cls, v):
            if not 1 <= v <= 65535:
                raise ValueError('port must be between 1 and 65535')
            return v
        
        @validator('pool_size')
        def validate_pool_size(cls, v):
            if v < 1:
                raise ValueError('pool_size must be at least 1')
            return v
    
    class Redis(BaseModel):
        host: str
        port: int
        db: int
        password: Optional[str]
        ssl: bool
        max_connections: int
        
        @validator('port')
        def validate_port(cls, v):
            if not 1 <= v <= 65535:
                raise ValueError('port must be between 1 and 65535')
            return v
        
        @validator('db')
        def validate_db(cls, v):
            if not 0 <= v <= 15:
                raise ValueError('redis db must be between 0 and 15')
            return v
    
    class Security(BaseModel):
        jwt_secret: str
        jwt_expiration: int
        bcrypt_rounds: int
        
        @validator('jwt_expiration')
        def validate_jwt_expiration(cls, v):
            if v < 60:  # At least 1 minute
                raise ValueError('jwt_expiration must be at least 60 seconds')
            return v
        
        @validator('bcrypt_rounds')
        def validate_bcrypt_rounds(cls, v):
            if not 4 <= v <= 31:
                raise ValueError('bcrypt_rounds must be between 4 and 31')
            return v

class AdvancedConfigManager:
    """Advanced configuration manager with validation, hot reloading, and monitoring"""
    
    def __init__(self, env: Optional[str] = None, config_dir: Optional[Path] = None):
        self.env = env or os.getenv('FLAVORSNAP_ENV', os.getenv('NODE_ENV', 'development'))
        self.config_dir = config_dir or Path(__file__).parent.parent / 'config' / 'environments'
        self.config: Dict[str, Any] = {}
        self.original_config: Dict[str, Any] = {}
        self.status = ConfigStatus.LOADING
        
        # Version control
        self.versions: List[ConfigVersion] = []
        self.current_version = 0
        self.max_versions = 50
        
        # Hot reloading
        self.hot_reload_enabled = False
        self.file_observer = None
        self.reload_callbacks: List[Callable] = []
        
        # Validation
        self.validator = ConfigValidator
        self.validation_enabled = True
        self.strict_validation = False
        
        # Security
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Monitoring
        self.metrics = PrometheusMetrics()
        self.change_history: List[ConfigChange] = []
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Load initial configuration
        self._load_configuration()
        self._setup_logging()
        
        logger.info(f"Advanced configuration manager initialized for environment: {self.env}")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for secrets"""
        key = os.getenv('CONFIG_ENCRYPTION_KEY')
        if key:
            return base64.urlsafe_b64decode(key.encode())
        
        if self.env == 'production':
            raise ValueError("CONFIG_ENCRYPTION_KEY must be set in production")
        
        # Generate key for development/staging
        logger.warning("No CONFIG_ENCRYPTION_KEY provided. Using generated key for non-production.")
        return Fernet.generate_key()
    
    def _load_configuration(self):
        """Load configuration from files"""
        start_time = time.time()
        try:
            with self._lock:
                self.status = ConfigStatus.LOADING
                
                # Load base configuration
                config_file = self.config_dir / f'{self.env}.yaml'
                if not config_file.exists():
                    config_file = self.config_dir / f'{self.env}.yml'
                
                if not config_file.exists():
                    config_file = self.config_dir / f'{self.env}.json'
                
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        if config_file.suffix in ['.yaml', '.yml']:
                            self.config = yaml.safe_load(f)
                        else:
                            self.config = json.load(f)
                    
                    # Replace environment variables
                    self.config = self._replace_env_vars(self.config)
                    
                    # Validate configuration
                    if self.validation_enabled:
                        self._validate_configuration()
                    
                    # Store original for comparison
                    self.original_config = copy.deepcopy(self.config)
                    
                    # Update metrics
                    self.metrics.config_last_reload_time.labels(environment=self.env).set(time.time())
                    config_size = len(json.dumps(self.config).encode())
                    self.metrics.config_size_bytes.labels(environment=self.env, config_type='main').set(config_size)
                    
                    self.status = ConfigStatus.ACTIVE
                    logger.info(f"Configuration loaded successfully from {config_file}")
                    
                    # Record load in metrics
                    self.metrics.config_loads_total.labels(environment=self.env, status='success').inc()
                    
                else:
                    raise FileNotFoundError(f"Configuration file not found for environment: {self.env}")
        
        except Exception as e:
            self.status = ConfigStatus.ERROR
            logger.error(f"Failed to load configuration: {e}")
            self.metrics.config_loads_total.labels(environment=self.env, status='error').inc()
            raise
        
        finally:
            duration = time.time() - start_time
            self.metrics.config_reload_duration.labels(environment=self.env).observe(duration)
    
    def _replace_env_vars(self, obj: Any) -> Any:
        """Replace environment variables in configuration"""
        if isinstance(obj, str):
            # Handle ${VAR} and ${VAR:default} syntax
            import re
            
            def replace_var(match):
                var_expr = match.group(1)
                if ':' in var_expr:
                    var, default = var_expr.split(':', 1)
                    return os.getenv(var, default)
                else:
                    return os.getenv(var_expr, '')
            
            return re.sub(r'\$\{([^}]+)\}', replace_var, obj)
        elif isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        return obj
    
    def _validate_configuration(self):
        """Validate configuration using Pydantic models"""
        try:
            # Validate app section
            if 'app' in self.config:
                ConfigValidator.App(**self.config['app'])
            
            # Validate server section
            if 'server' in self.config:
                ConfigValidator.Server(**self.config['server'])
            
            # Validate database section
            if 'database' in self.config:
                ConfigValidator.Database(**self.config['database'])
            
            # Validate redis section
            if 'redis' in self.config:
                ConfigValidator.Redis(**self.config['redis'])
            
            # Validate security section
            if 'security' in self.config:
                ConfigValidator.Security(**self.config['security'])
            
            logger.info("Configuration validation passed")
            
        except ValidationError as e:
            error_msg = f"Configuration validation failed: {e}"
            logger.error(error_msg)
            
            if self.strict_validation:
                raise ValueError(error_msg)
            else:
                self.metrics.config_validation_errors_total.labels(
                    environment=self.env, 
                    validation_type='pydantic'
                ).inc()
    
    def _setup_logging(self):
        """Setup logging based on configuration"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        
        # Configure root logger
        logging.getLogger().setLevel(getattr(logging, log_level))
        
        # Setup file handler if configured
        if 'file_path' in log_config:
            file_handler = logging.FileHandler(log_config['file_path'])
            file_handler.setLevel(getattr(logging, log_level))
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            logging.getLogger().addHandler(file_handler)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        with self._lock:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key: str, value: Any, track_change: bool = True) -> bool:
        """Set configuration value using dot notation"""
        with self._lock:
            keys = key.split('.')
            old_value = self.get(key)
            
            # Navigate to the parent
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            
            # Track change if requested
            if track_change and old_value != value:
                change = ConfigChange(
                    timestamp=datetime.utcnow(),
                    change_type=ConfigChangeType.UPDATE,
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    source='api',
                    version=self.current_version + 1
                )
                self.change_history.append(change)
                
                # Update metrics
                self.metrics.config_changes_total.labels(
                    change_type='update',
                    environment=self.env
                ).inc()
                
                logger.info(f"Configuration updated: {key} = {value}")
            
            return True
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f'features.{feature}', False)
    
    def enable_hot_reload(self, callback: Optional[Callable] = None):
        """Enable hot reloading of configuration files"""
        if self.hot_reload_enabled:
            return
        
        self.hot_reload_enabled = True
        
        if callback:
            self.reload_callbacks.append(callback)
        
        # Setup file watcher
        class ConfigFileHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, config_manager):
                self.config_manager = config_manager
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(('.yaml', '.yml', '.json')):
                    logger.info(f"Configuration file changed: {event.src_path}")
                    self.config_manager.reload_configuration()
        
        self.file_observer = watchdog.observers.Observer()
        self.file_observer.schedule(
            ConfigFileHandler(self),
            str(self.config_dir),
            recursive=False
        )
        self.file_observer.start()
        
        logger.info("Hot reloading enabled")
    
    def disable_hot_reload(self):
        """Disable hot reloading of configuration files"""
        if not self.hot_reload_enabled:
            return
        
        self.hot_reload_enabled = False
        
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
        
        logger.info("Hot reloading disabled")
    
    def reload_configuration(self):
        """Reload configuration from files"""
        try:
            old_config = copy.deepcopy(self.config)
            self._load_configuration()
            
            # Call reload callbacks
            for callback in self.reload_callbacks:
                try:
                    callback(old_config, self.config)
                except Exception as e:
                    logger.error(f"Error in reload callback: {e}")
            
            # Record reload change
            change = ConfigChange(
                timestamp=datetime.utcnow(),
                change_type=ConfigChangeType.RELOAD,
                key='*',
                old_value=old_config,
                new_value=self.config,
                source='hot_reload',
                version=self.current_version + 1
            )
            self.change_history.append(change)
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            raise
    
    def create_version(self, description: str = "", author: str = "system") -> int:
        """Create a new version of the configuration"""
        with self._lock:
            self.current_version += 1
            
            # Calculate config hash
            config_str = json.dumps(self.config, sort_keys=True)
            config_hash = hashlib.sha256(config_str.encode()).hexdigest()
            
            # Create version record
            version = ConfigVersion(
                version=self.current_version,
                timestamp=datetime.utcnow(),
                config_hash=config_hash,
                changes=copy.deepcopy(self.change_history[-10:]) if self.change_history else [],
                author=author,
                description=description
            )
            
            self.versions.append(version)
            
            # Limit number of versions
            if len(self.versions) > self.max_versions:
                self.versions.pop(0)
            
            logger.info(f"Configuration version {self.current_version} created")
            return self.current_version
    
    def rollback_to_version(self, version: int) -> bool:
        """Rollback configuration to a specific version"""
        with self._lock:
            version_record = next((v for v in self.versions if v.version == version), None)
            
            if not version_record:
                logger.error(f"Version {version} not found")
                return False
            
            # Load version from backup if available
            backup_file = self.config_dir / f'.backup_{version}.yaml'
            if backup_file.exists():
                try:
                    with open(backup_file, 'r') as f:
                        self.config = yaml.safe_load(f)
                    
                    # Validate after rollback
                    if self.validation_enabled:
                        self._validate_configuration()
                    
                    logger.info(f"Configuration rolled back to version {version}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to rollback to version {version}: {e}")
                    return False
            else:
                logger.error(f"Backup file for version {version} not found")
                return False
    
    def get_change_history(self, limit: int = 50) -> List[ConfigChange]:
        """Get configuration change history"""
        return self.change_history[-limit:]
    
    def get_versions(self) -> List[ConfigVersion]:
        """Get configuration versions"""
        return self.versions
    
    def export_config(self, format: str = 'yaml', include_secrets: bool = False) -> str:
        """Export configuration in specified format"""
        config_to_export = copy.deepcopy(self.config)
        
        # Remove secrets if requested
        if not include_secrets:
            config_to_export = self._mask_secrets(config_to_export)
        
        if format.lower() == 'yaml':
            return yaml.dump(config_to_export, default_flow_style=False, sort_keys=False)
        elif format.lower() == 'json':
            return json.dumps(config_to_export, indent=2, sort_keys=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_config(self, config_data: Union[str, Dict[str, Any]], format: str = 'yaml', merge: bool = True):
        """Import configuration data"""
        try:
            if isinstance(config_data, str):
                if format.lower() == 'yaml':
                    new_config = yaml.safe_load(config_data)
                elif format.lower() == 'json':
                    new_config = json.loads(config_data)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            else:
                new_config = config_data
            
            # Replace environment variables
            new_config = self._replace_env_vars(new_config)
            
            # Validate new configuration
            if self.validation_enabled:
                temp_config = self.config
                self.config = new_config
                self._validate_configuration()
                self.config = temp_config
            
            with self._lock:
                old_config = copy.deepcopy(self.config)
                
                if merge:
                    # Deep merge configurations
                    self._deep_merge(self.config, new_config)
                else:
                    # Replace entire configuration
                    self.config = new_config
                
                # Track import change
                change = ConfigChange(
                    timestamp=datetime.utcnow(),
                    change_type=ConfigChangeType.UPDATE,
                    key='*',
                    old_value=old_config,
                    new_value=self.config,
                    source='import',
                    version=self.current_version + 1
                )
                self.change_history.append(change)
                
                logger.info(f"Configuration imported successfully (merge={merge})")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive configuration values"""
        sensitive_keys = ['password', 'secret', 'key', 'token', 'dsn', 'api_key']
        masked_config = copy.deepcopy(config)
        
        def mask_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        obj[key] = '***MASKED***'
                    else:
                        mask_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    mask_recursive(item)
        
        mask_recursive(masked_config)
        return masked_config
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration manager status"""
        return {
            'environment': self.env,
            'status': self.status.value,
            'current_version': self.current_version,
            'total_versions': len(self.versions),
            'hot_reload_enabled': self.hot_reload_enabled,
            'validation_enabled': self.validation_enabled,
            'strict_validation': self.strict_validation,
            'config_size': len(json.dumps(self.config)),
            'last_reload': self.change_history[-1].timestamp.isoformat() if self.change_history else None
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on configuration"""
        checks = {
            'config_loaded': self.status == ConfigStatus.ACTIVE,
            'validation_passed': True,
            'hot_reload_working': True,
            'secrets_available': True,
            'environment_vars_resolved': True
        }
        
        # Check validation
        try:
            if self.validation_enabled:
                self._validate_configuration()
        except Exception:
            checks['validation_passed'] = False
        
        # Check hot reload
        if self.hot_reload_enabled:
            checks['hot_reload_working'] = self.file_observer is not None and self.file_observer.is_alive()
        
        # Check required secrets
        required_secrets = ['security.jwt_secret']
        missing_secrets = []
        for secret in required_secrets:
            if not self.get(secret):
                missing_secrets.append(secret)
        checks['secrets_available'] = len(missing_secrets) == 0
        
        # Overall health
        checks['healthy'] = all(checks.values())
        checks['issues'] = [k for k, v in checks.items() if not v and k != 'healthy']
        
        return checks

# Global instance
config_manager = AdvancedConfigManager()

# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return config_manager.get(key, default)

def set_config(key: str, value: Any, track_change: bool = True) -> bool:
    """Set configuration value"""
    return config_manager.set(key, value, track_change)

def is_feature_enabled(feature: str) -> bool:
    """Check if feature is enabled"""
    return config_manager.is_feature_enabled(feature)

def reload_config():
    """Reload configuration"""
    return config_manager.reload_configuration()

def get_config_status() -> Dict[str, Any]:
    """Get configuration status"""
    return config_manager.get_status()

def health_check() -> Dict[str, Any]:
    """Perform configuration health check"""
    return config_manager.health_check()

# Decorator for configuration-dependent functions
def config_required(*required_keys):
    """Decorator to ensure required configuration keys are present"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            missing_keys = []
            for key in required_keys:
                if not config_manager.get(key):
                    missing_keys.append(key)
            
            if missing_keys:
                raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    # Test configuration manager
    print("Testing Advanced Configuration Manager")
    
    # Get some configuration values
    print(f"App name: {get_config('app.name')}")
    print(f"Environment: {get_config('app.environment')}")
    print(f"Server port: {get_config('server.port')}")
    
    # Check features
    print(f"ML Classification enabled: {is_feature_enabled('ml_classification')}")
    
    # Get status
    status = get_config_status()
    print(f"Config status: {status}")
    
    # Health check
    health = health_check()
    print(f"Health check: {health}")
    
    # Export configuration
    yaml_config = config_manager.export_config(format='yaml', include_secrets=False)
    print(f"YAML config (first 200 chars): {yaml_config[:200]}...")
