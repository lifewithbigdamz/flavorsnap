import os
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(app_name="flavorsnap"):
    # Ensure log directory exists
    log_dir = os.environ.get("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(app_name)
    
    # Set log level based on environment
    env = os.environ.get('FLASK_ENV', 'development')
    log_level = logging.DEBUG if env == 'development' else logging.INFO
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if setup_logger is called multiple times
    if not logger.handlers:
        # Rotating File Handler (JSON structured for log aggregators/monitoring)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{app_name}.log"),
            maxBytes=10485760, # 10MB limit
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger