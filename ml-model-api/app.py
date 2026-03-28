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

# Import model validator
from model_validator import ModelValidator, FileValidationResult
from model_registry import ModelRegistry

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

# Initialize model registry and validator
try:
    model_registry = ModelRegistry()
    model_validator = ModelValidator(model_registry)
    logger.info("Model validator initialized successfully")
except Exception as e:
    logger.warning(f"Model validator initialization failed: {e}")
    model_validator = None

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
        
        # Enhanced file validation using security module
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({
                'error': error_msg,
                'error_type': 'validation_failed',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Additional validation using model validator if available
        if model_validator:
            try:
                validation_result = model_validator.validate_uploaded_file(file)
                if not validation_result.is_valid:
                    logger.warning(f"Model validator failed: {validation_result.validation_errors}")
                    return jsonify({
                        'error': 'File validation failed',
                        'details': validation_result.validation_errors,
                        'error_type': 'security_validation_failed',
                        'timestamp': datetime.now().isoformat()
                    }), 400
                
                # Log validation details for monitoring
                logger.info(f"File validated successfully: {validation_result.filename}, "
                           f"size: {validation_result.file_size}, "
                           f"mime: {validation_result.detected_mime_type}, "
                           f"dimensions: {validation_result.image_dimensions}")
                           
            except Exception as e:
                logger.error(f"Model validator error: {str(e)}")
                # Continue with basic validation if model validator fails
        
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
            'request_id': request.headers.get('X-Request-ID', 'unknown'),
            'file_info': {
                'filename': filename,
                'size': file.tell() if hasattr(file, 'tell') else 'unknown'
            }
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# File validation endpoint for testing and monitoring
@app.route('/validate-file', methods=['POST'])
@tiered_rate_limit('upload')
@require_api_key
def validate_file():
    """Dedicated file validation endpoint"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not model_validator:
            # Fallback to basic security validation
            is_valid, error_msg = InputValidator.validate_file_upload(file)
            return jsonify({
                'is_valid': is_valid,
                'error': error_msg if not is_valid else None,
                'validation_type': 'basic_security'
            })
        
        # Comprehensive validation
        validation_result = model_validator.validate_uploaded_file(file)
        
        response = {
            'is_valid': validation_result.is_valid,
            'filename': validation_result.filename,
            'file_size': validation_result.file_size,
            'detected_mime_type': validation_result.detected_mime_type,
            'image_dimensions': validation_result.image_dimensions,
            'file_hash': validation_result.file_hash,
            'validation_errors': validation_result.validation_errors,
            'security_flags': validation_result.security_flags,
            'validation_type': 'comprehensive',
            'timestamp': datetime.now().isoformat()
        }
        
        # Log validation results
        if validation_result.is_valid:
            logger.info(f"File validation successful: {validation_result.filename}")
        else:
            logger.warning(f"File validation failed: {validation_result.filename}, "
                          f"errors: {validation_result.validation_errors}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Batch file validation endpoint
@app.route('/validate-files', methods=['POST'])
@tiered_rate_limit('upload')
@require_api_key
def validate_files():
    """Batch file validation endpoint"""
    try:
        if not model_validator:
            return jsonify({'error': 'Batch validation not available'}), 503
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        
        # Prepare file list for batch validation
        file_list = [(file, file.filename) for file in files]
        
        # Perform batch validation
        validation_results = model_validator.batch_validate_files(file_list)
        
        # Get summary statistics
        summary = model_validator.get_validation_summary(validation_results)
        
        # Convert results to dict for JSON serialization
        results_dict = []
        for result in validation_results:
            results_dict.append({
                'filename': result.filename,
                'is_valid': result.is_valid,
                'file_size': result.file_size,
                'detected_mime_type': result.detected_mime_type,
                'image_dimensions': result.image_dimensions,
                'file_hash': result.file_hash,
                'validation_errors': result.validation_errors,
                'security_flags': result.security_flags
            })
        
        response = {
            'results': results_dict,
            'summary': summary,
            'validation_type': 'batch_comprehensive',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Batch validation completed: {summary['total_files']} files, "
                   f"{summary['valid_files']} valid, {summary['security_issues']} security issues")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Batch file validation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint (exempt from rate limiting)
@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Comprehensive health check endpoint"""
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
        
        # Perform quick dependency checks
        overall_status = 'healthy'
        checks = {}
        
        # Check model file
        model_exists = os.path.exists('model.pth')
        checks['model'] = 'available' if model_exists else 'missing'
        if not model_exists:
            overall_status = 'degraded'
        
        # Check database connectivity
        try:
            import sqlite3
            conn = sqlite3.connect('predictions.db', timeout=2)
            conn.close()
            checks['database'] = 'connected'
        except Exception:
            checks['database'] = 'disconnected'
            overall_status = 'degraded'
        
        # Check Redis if configured
        if os.environ.get('REDIS_URL'):
            try:
                import redis
                r = redis.from_url(os.environ.get('REDIS_URL'), socket_timeout=2)
                r.ping()
                checks['redis'] = 'connected'
            except Exception:
                checks['redis'] = 'disconnected'
                overall_status = 'degraded'
        
        # Update health check status metric
        if hasattr(monitoring_middleware, 'HEALTH_CHECK_STATUS'):
            monitoring_middleware.HEALTH_CHECK_STATUS.set(1 if overall_status == 'healthy' else 0)
        
        return jsonify({
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'checks': checks,
            'endpoints': {
                'basic': '/health',
                'detailed': '/health/detailed',
                'database': '/health/database',
                'redis': '/health/redis',
                'model': '/health/model',
                'system': '/health/system',
                'dependencies': '/health/dependencies'
            },
            'security': {
                'rate_limiting': True,
                'api_key_auth': True,
                'security_headers': True,
                'input_validation': True
            },
            'monitoring': {
                'enabled': True,
                'metrics_endpoint': '/metrics',
                'dashboard_endpoint': '/dashboard'
            },
            'detailed_metrics': detailed_health
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        if hasattr(monitoring_middleware, 'HEALTH_CHECK_STATUS'):
            monitoring_middleware.HEALTH_CHECK_STATUS.set(0)
        return jsonify({
            'status': 'unhealthy',
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
            'validate_file': 'POST /validate-file - Single file validation',
            'validate_files': 'POST /validate-files - Batch file validation',
            'health': 'GET /health - Basic health check',
            'health_detailed': 'GET /health/detailed - Detailed health metrics',
            'health_database': 'GET /health/database - Database connectivity check',
            'health_redis': 'GET /health/redis - Redis connectivity check',
            'health_model': 'GET /health/model - ML model status check',
            'health_system': 'GET /health/system - System resources check',
            'health_dependencies': 'GET /health/dependencies - Dependencies check',
            'metrics': 'GET /metrics - Prometheus metrics',
            'dashboard': 'GET /dashboard - Performance dashboard',
            'info': 'GET /api/info - API information',
            'admin_api_key': 'POST /admin/api-key/generate - Generate API key'
        },
        'health_checks': {
            'basic': {
                'endpoint': '/health',
                'description': 'Overall system health status',
                'response_time': '< 100ms',
                'includes': ['model_status', 'database_connectivity', 'redis_status']
            },
            'detailed': {
                'endpoint': '/health/detailed',
                'description': 'Comprehensive system metrics',
                'response_time': '< 500ms',
                'includes': ['system_resources', 'gpu_status', 'model_metrics']
            },
            'specialized': {
                'database': '/health/database - Database performance and connectivity',
                'redis': '/health/redis - Redis connection and metrics',
                'model': '/health/model - ML model loading and inference metrics',
                'system': '/health/system - CPU, memory, disk, network metrics',
                'dependencies': '/health/dependencies - Package versions and environment'
            }
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
            'application_metrics': ['requests', 'response_time', 'inference_metrics', 'error_rate'],
            'health_check_metrics': ['dependency_status', 'resource_usage', 'model_performance']
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
