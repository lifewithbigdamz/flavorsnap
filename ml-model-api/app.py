from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import os
import time
import logging
from functools import wraps
from datetime import datetime

# Import security modules
from security_config import (
    SecurityConfig, InputValidator, APIKeyManager, 
    RateLimitManager, SecurityMiddleware, SecurityMonitor,
    validate_json_input, is_safe_url
)

# Import performance monitoring
from monitoring import MonitoringMiddleware, track_inference, update_model_accuracy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    API_KEYS = os.environ.get('API_KEYS', '').split(',') if os.environ.get('API_KEYS') else []
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    UPLOAD_FOLDER = 'uploads'
    ENV = os.environ.get('FLASK_ENV', 'development')

app.config.from_object(Config)

# Initialize security middleware
security_middleware = SecurityMiddleware(app)
security_monitor = SecurityMonitor(app)

# Initialize performance monitoring middleware
monitoring_middleware = MonitoringMiddleware(app)

# Initialize rate limiter with tiered key function
limiter = Limiter(
    key_func=RateLimitManager.get_tiered_key_func(),
    app=app,
    default_limits=["20 per minute"]
)

# CORS Configuration
CORS(app, 
     origins=['http://localhost:3000', 'https://yourdomain.com'],
     methods=['GET', 'POST', 'PUT', 'DELETE'],
     allow_headers=['Content-Type', 'Authorization', 'X-API-Key'],
     supports_credentials=True)

# Dynamic rate limiting decorator
def tiered_rate_limit(endpoint_name: str):
    """Dynamic rate limiting based on API key tier"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            rate_limit = RateLimitManager.get_rate_limit_for_endpoint(endpoint_name, api_key)
            
            # Apply rate limit using flask-limiter
            with limiter.limit(rate_limit):
                return f(*args, **kwargs)
        return decorated_function
    return decorator
# API Key Authentication
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip API key check in development
        if app.config.get('ENV') == 'development':
            return f(*args, **kwargs)
            
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            logger.warning(f"Missing API key from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'API key required'}), 401
        
        # Validate API key format
        if not InputValidator.validate_api_key(api_key):
            logger.warning(f"Invalid API key format from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'Invalid API key format'}), 401
        
        if api_key not in app.config['API_KEYS']:
            logger.warning(f"Unauthorized API key from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'Invalid API key'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Rate Limiting for Specific Endpoints
@app.route('/predict', methods=['POST'])
@tiered_rate_limit('predict')
@require_api_key
@track_inference
def predict():
    """Food classification endpoint with comprehensive security measures"""
    start_time = time.time()
    
    try:
        # Validate input using security module
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        # Validate file upload
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Generate secure filename
        filename = InputValidator.secure_filename_custom(file.filename)
        
        # Mock prediction logic (replace with actual model)
        processing_time = time.time() - start_time
        
        logger.info(f"Prediction completed for {filename} in {processing_time:.3f}s")
        
        return jsonify({
            'prediction': 'Sample food',
            'confidence': 0.95,
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat(),
            'request_id': request.headers.get('X-Request-ID', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint (exempt from rate limiting)
@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    try:
        # Get detailed health from monitoring middleware
        if hasattr(monitoring_middleware, '_get_detailed_health'):
            detailed_health = monitoring_middleware._get_detailed_health()
        else:
            detailed_health = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'monitoring': 'basic'
            }
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'security': {
                'rate_limiting': True,
                'api_key_auth': True,
                'security_headers': True,
                'input_validation': True
            },
            'monitoring': {
                'enabled': True,
                'metrics_endpoint': '/metrics',
                'dashboard_endpoint': '/dashboard',
                'detailed_health_endpoint': '/health/detailed'
            },
            'detailed_metrics': detailed_health
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'degraded',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

# API info endpoint
@app.route('/api/info', methods=['GET'])
@limiter.limit("30 per minute")
def api_info():
    return jsonify({
        'name': 'FlavorSnap API',
        'version': '2.0.0',
        'endpoints': {
            'predict': 'POST /predict - Food classification',
            'health': 'GET /health - Health check',
            'health_detailed': 'GET /health/detailed - Detailed health metrics',
            'metrics': 'GET /metrics - Prometheus metrics',
            'dashboard': 'GET /dashboard - Performance dashboard',
            'info': 'GET /api/info - API information',
            'admin_api_key': 'POST /admin/api-key/generate - Generate API key'
        },
        'security': {
            'rate_limiting': 'enabled',
            'api_key_auth': 'Required for production',
            'cors_enabled': True,
            'security_headers': True,
            'input_validation': True,
            'file_upload_limits': {
                'max_size': '16MB',
                'allowed_types': ['image/jpeg', 'image/png', 'image/gif']
            }
        },
        'monitoring': {
            'prometheus_metrics': True,
            'performance_dashboard': True,
            'system_metrics': ['cpu', 'memory', 'gpu', 'disk'],
            'application_metrics': ['requests', 'response_time', 'inference_metrics', 'error_rate']
        }
    })

# API key generation endpoint (admin only)
@app.route('/admin/api-key/generate', methods=['POST'])
@tiered_rate_limit('generate_api_key')
def generate_api_key():
    """Generate new API key with tier support (admin endpoint)"""
    if app.config.get('ENV') == 'production':
        # Add admin authentication here
        pass
    
    # Get tier from request, default to free
    request_data = request.get_json(silent=True) or {}
    tier = request_data.get('tier', 'free')
    
    if tier not in ['free', 'premium', 'enterprise']:
        return jsonify({'error': 'Invalid tier. Must be free, premium, or enterprise'}), 400
    
    # Generate tiered API key
    key_info = APIKeyManager.generate_tiered_api_key(tier)
    logger.info(f"New {tier} API key generated")
    
    return jsonify({
        'api_key': key_info['api_key'],
        'tier': key_info['tier'],
        'limits': key_info['limits'],
        'message': 'Store this key securely - it will not be shown again'
    })

# Performance dashboard endpoint
@app.route('/dashboard', methods=['GET'])
@tiered_rate_limit('performance_dashboard')
def performance_dashboard():
    """Serve performance dashboard"""
    try:
        from performance_dashboard import create_dashboard
        dashboard = create_dashboard()
        return dashboard
    except ImportError as e:
        logger.error(f"Performance dashboard not available: {e}")
        return jsonify({'error': 'Performance dashboard not available'}), 503
    except Exception as e:
        logger.error(f"Error serving performance dashboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    api_key = request.headers.get('X-API-Key')
    tier = RateLimitManager.get_api_key_tier(api_key)
    endpoint = request.endpoint or 'unknown'
    
    # Get the specific rate limit for this endpoint and tier
    rate_limit = RateLimitManager.get_rate_limit_for_endpoint(endpoint, api_key)
    
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': str(e.description),
        'retry_after': getattr(e, 'retry_after', 60),
        'limit': rate_limit,
        'tier': tier,
        'endpoint': endpoint
    }), 429

@app.errorhandler(404)
def not_found_handler(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error_handler(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_too_large_handler(e):
    return jsonify({
        'error': 'Request too large',
        'max_size': '16MB'
    }), 413

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
