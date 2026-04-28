import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io
import os
import sys

# Add the parent directory to the path to import config modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_config, get_config_value
from logger_config import get_logger
from db_config import db_config, init_database

# Initialize configuration
config = get_config()
logger = get_logger(__name__)

# Create Flask app with configuration
app = Flask(__name__)

# Configure Flask app from config
app.config['SECRET_KEY'] = get_config_value('app.secret_key')
app.config['DEBUG'] = get_config_value('app.debug', False)
app.config['MAX_CONTENT_LENGTH'] = get_config_value('file_storage.max_file_size', 16777216)

# Initialize database
try:
    init_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# Configuration change callback
def on_config_change(new_config, old_config):
    """Handle configuration changes"""
    logger.info("Configuration changed, updating Flask app settings")
    app.config['SECRET_KEY'] = new_config.get('app', {}).get('secret_key')
    app.config['DEBUG'] = new_config.get('app', {}).get('debug', False)
    app.config['MAX_CONTENT_LENGTH'] = new_config.get('file_storage', {}).get('max_file_size', 16777216)

# Register configuration change callback
config.add_change_callback(on_config_change)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = db_config.test_connection()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': config.get('monitoring.health_check_interval'),
            'database': 'connected' if db_status else 'disconnected',
            'version': get_config_value('app.version', '1.0.0'),
            'environment': config.environment
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/config', methods=['GET'])
def get_config_info():
    """Get configuration information (non-sensitive)"""
    try:
        monitoring_info = config.get_monitoring_info()
        
        # Remove sensitive information
        safe_info = {
            'environment': monitoring_info['environment'],
            'last_reload': monitoring_info['last_reload'],
            'version_count': monitoring_info['version_count'],
            'watcher_active': monitoring_info['watcher_active'],
            'backup_count': monitoring_info['backup_count'],
            'validation_status': monitoring_info['validation_status']
        }
        
        return jsonify(safe_info), 200
    except Exception as e:
        logger.error(f"Failed to get config info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration"""
    try:
        config.reload_config()
        logger.info("Configuration reloaded via API")
        return jsonify({'message': 'Configuration reloaded successfully'}), 200
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@tiered_rate_limit('predict')
@require_api_key
def predict():
    """Food classification prediction endpoint"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    
    # Validate file extension
    allowed_extensions = get_config_value('file_storage.allowed_extensions', ['jpg', 'jpeg', 'png', 'gif', 'bmp'])
    if file.filename and '.' in file.filename:
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File extension not allowed. Allowed: {allowed_extensions}'}), 400

    try:
        # Log prediction request
        logger.info(f"Processing image: {file.filename}")
        
        # Placeholder for preprocessing & prediction
        image = Image.open(file.stream)
        
        # TODO: Implement actual model prediction
        # model_path = get_config_value('ml_model.model_path')
        # classes_file = get_config_value('ml_model.classes_file')
        # input_size = get_config_value('ml_model.input_size', [224, 224])
        
        predicted_label = "Moi Moi"  # Dummy output for now
        confidence = 0.95  # Dummy confidence
        
        logger.info(f"Prediction completed: {predicted_label} (confidence: {confidence})")
        
        return jsonify({
            'label': predicted_label,
            'confidence': confidence,
            'model_version': get_config_value('app.version', '1.0.0')
        })
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle not found error"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        # Get server configuration
        host = get_config_value('app.host', '0.0.0.0')
        port = get_config_value('app.port', 5000)
        debug = get_config_value('app.debug', False)
        
        logger.info(f"Starting FlavorSnap ML API on {host}:{port}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Debug mode: {debug}")
        
        # Start Flask application
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    finally:
        # Cleanup resources
        config.cleanup()
