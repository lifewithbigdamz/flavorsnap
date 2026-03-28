from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import os
import time
import logging
from functools import wraps
from datetime import datetime

from security_config import (
    SecurityConfig, InputValidator, APIKeyManager,
    RateLimitManager, SecurityMiddleware, SecurityMonitor,
    validate_json_input, is_safe_url
)

# Import image optimization module
from image_optimizer import get_image_optimizer, ImageFormat

# Import and configure structured logging
from logger_config import setup_logger
logger = setup_logger(__name__)

app = Flask(__name__)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    REDIS_URL = os.environ.get('REDIS_URL', '')
    API_KEYS = os.environ.get('API_KEYS', '').split(',') if os.environ.get('API_KEYS') else []
    UPLOAD_FOLDER = 'uploads'
    OPTIMIZED_FOLDER = 'uploads/optimized'
    MAX_CONTENT_LENGTH = SecurityConfig.MAX_CONTENT_LENGTH
    ENV = os.environ.get('FLASK_ENV', 'development')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit



app.config.from_object(Config)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OPTIMIZED_FOLDER'], exist_ok=True)

# Security middleware
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
    def decorated(*args, **kwargs):
        if app.config.get('ENV') == 'development':
            return f(*args, **kwargs)
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            logger.warning(f"Missing API key from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'API key required'}), 401
        if not InputValidator.validate_api_key(api_key):
            logger.warning(f"Invalid API key format from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'Invalid API key format'}), 401
        if api_key not in app.config['API_KEYS']:
            logger.warning(f"Unauthorized API key from {RateLimitManager.get_client_ip()}")
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/predict', methods=['POST'])
@tiered_rate_limit('predict')
@require_api_key
@track_inference
def predict():
    """Food classification endpoint with automatic image optimization"""
    start_time = time.time()
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400

        # Optimize image before processing
        try:
            optimizer = get_image_optimizer()
            optimization_result = optimizer.optimize_image(
                file.stream,
                quality='high',
                generate_webp=True,
                generate_thumbnails=True
            )
            
            # Save optimized images
            base_filename = InputValidator.secure_filename_custom(file.filename)
            base_filename = os.path.splitext(base_filename)[0]
            saved_paths = optimizer.save_optimized_images(
                optimization_result,
                app.config['OPTIMIZED_FOLDER'],
                base_filename
            )
            
            logger.info(f"Image optimized: original {optimization_result['metadata']['original_size']}B -> "
                       f"optimized {optimization_result['metadata']['optimized_size']}B "
                       f"({optimization_result['metadata']['compression_ratio']}% compression)")
            
            # Save original to uploads folder for reference
            filename = InputValidator.secure_filename_custom(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(save_path, 'wb') as f:
                optimization_result['original']['data'].seek(0)
                f.write(optimization_result['original']['data'].read())
                
        except Exception as opt_error:
            logger.warning(f"Image optimization failed, falling back: {str(opt_error)}")
            # Fallback: save original
            filename = InputValidator.secure_filename_custom(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.seek(0)
            file.save(save_path)

        # TODO: replace with actual model inference using optimized image
        processing_time = time.time() - start_time
        logger.info(f"Prediction completed for {filename} in {processing_time:.3f}s")

        return jsonify({
            'prediction': 'Sample food',
            'confidence': 0.95,
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat(),
            'request_id': request.headers.get('X-Request-ID', 'unknown'),
            'image_optimization': optimization_result['metadata'] if 'optimization_result' in locals() else None
        })

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/optimize', methods=['POST'])
@tiered_rate_limit('optimize')
@require_api_key
def optimize_image():
    """Endpoint for image optimization only (returns optimized images and metadata)"""
    start_time = time.time()
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400

        # Get optimization parameters from request
        quality = request.form.get('quality', 'high')
        generate_webp = request.form.get('generate_webp', 'true').lower() == 'true'
        generate_thumbnails = request.form.get('generate_thumbnails', 'true').lower() == 'true'
        max_width = int(request.form.get('max_width', 1920))
        max_height = int(request.form.get('max_height', 1080))

        # Optimize image
        optimizer = get_image_optimizer()
        optimization_result = optimizer.optimize_image(
            file.stream,
            quality=quality,
            generate_webp=generate_webp,
            generate_thumbnails=generate_thumbnails,
            max_width=max_width,
            max_height=max_height
        )

        # Save optimized images
        base_filename = InputValidator.secure_filename_custom(file.filename)
        base_filename = os.path.splitext(base_filename)[0]
        saved_paths = optimizer.save_optimized_images(
            optimization_result,
            app.config['OPTIMIZED_FOLDER'],
            base_filename
        )

        processing_time = time.time() - start_time
        logger.info(f"Image optimization endpoint: {optimization_result['metadata']['compression_ratio']}% "
                   f"compression in {processing_time:.3f}s")

        return jsonify({
            'status': 'success',
            'metadata': optimization_result['metadata'],
            'saved_paths': saved_paths,
            'sizes': {
                'original': optimization_result['original']['size'],
                'optimized': optimization_result['optimized']['size'],
                'jpeg_fallback': optimization_result['jpeg_fallback']['size'],
                'thumbnails': {
                    name: data['size']
                    for name, data in optimization_result.get('thumbnails', {}).items()
                }
            },
            'processing_time': processing_time
        }), 200

    except ValueError as ve:
        logger.warning(f"Image validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Image optimization error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/optimized/<path:filename>', methods=['GET'])
@limiter.limit("100 per minute")
def serve_optimized_image(filename: str):
    """Serve optimized images with proper caching headers"""
    try:
        from flask import send_file
        
        # Validate filename to prevent directory traversal
        if not InputValidator.validate_filename(filename):
            logger.warning(f"Invalid filename requested: {filename}")
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(app.config['OPTIMIZED_FOLDER'], filename)
        
        # Security check: ensure file is within optimized folder
        if not os.path.abspath(file_path).startswith(os.path.abspath(app.config['OPTIMIZED_FOLDER'])):
            logger.warning(f"Attempted directory traversal: {filename}")
            return jsonify({'error': 'Access denied'}), 403

        if not os.path.exists(file_path):
            return jsonify({'error': 'Image not found'}), 404

        # Determine MIME type
        if filename.endswith('.webp'):
            mime_type = 'image/webp'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif filename.endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = 'application/octet-stream'

        # Set aggressive caching headers for optimized images
        response = send_file(
            file_path,
            mimetype=mime_type,
            cache_timeout=31536000  # 1 year
        )
        
        # Add custom headers for better caching and security
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        response.headers['ETag'] = InputValidator.secure_filename_custom(filename)
        
        return response

    except Exception as e:
        logger.error(f"Error serving optimized image: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


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
    
    new_key = APIKeyManager.generate_api_key()
    logger.info("New API key generated")
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


@app.errorhandler(413)
def request_too_large_handler(e):
    return jsonify({
        'error': 'Request too large',
        'max_size': '16MB'
    }), 413


@app.errorhandler(500)
def internal_error_handler(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
