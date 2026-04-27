import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io
import os
import time

from flask import request, jsonify
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

# Import caching and model inference modules
from cache_manager import cache_manager
from model_inference import model_inference

# Import Swagger documentation setup
from swagger_setup import setup_swagger

# Import analytics module
from analytics import analytics

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

CORS(app,
     origins=['http://localhost:3000', 'https://yourdomain.com'],
     methods=['GET', 'POST', 'PUT', 'DELETE'],
     allow_headers=['Content-Type', 'Authorization', 'X-API-Key'],
     supports_credentials=True)

# Setup API documentation
setup_swagger(app)

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

# =========================
# MODEL CONFIGURATION
# =========================

MODEL_PATH = os.getenv("MODEL_PATH", "ml-model-api/model.pth")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ⚠️ Ensure this matches your trained model classes
CLASS_NAMES = [
    "Amala", "Eba", "Egusi Soup", "Jollof Rice",
    "Moi Moi", "Pounded Yam", "Suya"
]

def load_model():
    try:
        model = models.resnet18(pretrained=False)
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, len(CLASS_NAMES))

        model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        model.to(DEVICE)
        model.eval()

        print("✅ Model loaded successfully")
        return model

    except Exception as e:
        print(f"❌ Model loading failed: {str(e)}")
        return None

# Load model once at startup
model = load_model()

# =========================
# IMAGE PREPROCESSING
# =========================

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# =========================
# PREDICTION ENDPOINT
# =========================

@app.route('/predict', methods=['POST'])
@tiered_rate_limit('predict')
@require_api_key
def predict():
    """Food classification endpoint with intelligent caching"""
    start_time = time.time()

    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    request_id = request.headers.get('X-Request-ID', f'req_{int(time.time() * 1000)}')

    try:
        # Read image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

        # Preprocess image
        input_tensor = transform(image).unsqueeze(0).to(DEVICE)

        # Run inference
        with torch.no_grad():
            outputs = model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

        # Get prediction
        confidence, predicted_class = torch.max(probabilities, 0)

        predicted_label = CLASS_NAMES[predicted_class.item()]
        confidence_score = float(confidence.item())

        inference_time = time.time() - start_time

        return jsonify({
            'prediction': predicted_label,
            'confidence': round(confidence_score, 4),
            'inference_time': round(inference_time, 3)
        })

    except Exception as e:
        return jsonify({
            'error': 'Invalid image or processing failed',
            'details': str(e)
        }), 400


# =========================
# MANAGEMENT ENDPOINTS
# =========================

# Register all management endpoints
register_all_endpoints(app, model_registry, ab_test_manager, deployment_manager, model_validator)

# Register NLP endpoints
try:
    from nlp_handlers import register_nlp_endpoints
    register_nlp_endpoints(app)
    logger.info("NLP endpoints registered successfully")
except Exception as e:
    logger.warning(f"Failed to register NLP endpoints: {e}")


# =========================
# ANALYTICS ENDPOINTS
# =========================

@app.route('/analytics/usage', methods=['GET'])
def get_usage_stats():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = analytics.get_usage_stats(start_date, end_date)
    return jsonify(data)

@app.route('/analytics/performance', methods=['GET'])
def get_model_performance():
    data = analytics.get_model_performance()
    return jsonify(data)

@app.route('/analytics/engagement', methods=['GET'])
def get_user_engagement():
    data = analytics.get_user_engagement()
    return jsonify(data)

@app.route('/analytics/activity', methods=['GET'])
def get_real_time_activity():
    data = analytics.get_real_time_activity()
    return jsonify(data)

@app.route('/analytics/stats', methods=['GET'])
def get_stats_cards():
    data = analytics.get_stats_cards()
    return jsonify(data)

@app.route('/analytics/export', methods=['GET'])
def export_analytics():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = analytics.export_data(start_date, end_date)
    return jsonify(data)

@app.route('/analytics', methods=['GET'])
def get_all_analytics():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    data = {
        'usageStats': analytics.get_usage_stats(start_date, end_date),
        'modelPerformance': analytics.get_model_performance(),
        'userEngagement': analytics.get_user_engagement(),
        'statsCards': analytics.get_stats_cards(),
        'realTimeActivity': analytics.get_real_time_activity()
    }
    return jsonify(data)

# =========================
# TIME SERIES ANALYSIS ENDPOINTS
# =========================

@app.route('/analytics/timeseries', methods=['GET'])
def get_timeseries_data():
    """Get preprocessed time series data"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    aggregation = request.args.get('aggregation', 'daily')
    metric = request.args.get('metric', 'total_requests')
    
    data = analytics.get_time_series_data(start_date, end_date, aggregation, metric)
    return jsonify(data)

@app.route('/analytics/trend', methods=['GET'])
def analyze_trend():
    """Analyze trends in time series data"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metric = request.args.get('metric', 'total_requests')
    method = request.args.get('method', 'linear')
    
    data = analytics.analyze_trend(start_date, end_date, metric, method)
    return jsonify(data)

@app.route('/analytics/seasonality', methods=['GET'])
def detect_seasonality():
    """Detect and analyze seasonality"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metric = request.args.get('metric', 'total_requests')
    model = request.args.get('model', 'additive')
    period = request.args.get('period', type=int)
    
    data = analytics.detect_seasonality(start_date, end_date, metric, model, period)
    return jsonify(data)

@app.route('/analytics/forecast', methods=['GET'])
def forecast_metric():
    """Forecast future values"""
    metric = request.args.get('metric', 'total_requests')
    steps = request.args.get('steps', 30, type=int)
    model = request.args.get('model', 'arima')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    data = analytics.forecast_metric(metric, steps, model, start_date, end_date)
    return jsonify(data)

@app.route('/analytics/anomalies', methods=['GET'])
def detect_anomalies():
    """Detect anomalies in time series"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metric = request.args.get('metric', 'total_requests')
    method = request.args.get('method', 'zscore')
    threshold = request.args.get('threshold', 3.0, type=float)
    
    data = analytics.detect_anomalies(start_date, end_date, metric, method, threshold)
    return jsonify(data)

@app.route('/analytics/visualization', methods=['GET'])
def get_visualization_data():
    """Get data formatted for visualization"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metrics = request.args.getlist('metrics')
    
    if not metrics:
        metrics = None
    
    data = analytics.get_visualization_data(start_date, end_date, metrics)
    return jsonify(data)

@app.route('/analytics/performance-metrics', methods=['GET'])
def get_performance_metrics():
    """Get comprehensive performance metrics"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    data = analytics.get_performance_metrics(start_date, end_date)
    return jsonify(data)
        # Validate and sanitize JSON input if present
        if request.is_json:
            json_data = request.get_json()
            is_valid, error_msg = validate_json_input(json_data)
            if not is_valid:
                logger.warning(f"JSON validation failed: {error_msg}")
                return jsonify({'error': error_msg}), 400

        # Validate file upload
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']

        # Sanitize filename from form data
        if file.filename:
            file.filename = InputValidator.sanitize_filename(file.filename)

        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400

        # Read file data for hashing
        file.seek(0)
        image_data = file.read()
        file.seek(0)  # Reset file pointer

        # Compute image hash for caching
        image_hash = cache_manager.compute_image_hash(image_data)

        # Check cache first
        cached_result = cache_manager.get_cached_prediction(image_hash)
        if cached_result:
            cached_result['cached'] = True
            cached_result['request_id'] = request_id
            logger.info(f"Cache hit for request {request_id}, saved inference time")
            return jsonify(cached_result)

        # Cache miss - proceed with inference
        filename = InputValidator.secure_filename_custom(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(save_path, 'wb') as f:
            f.write(image_data)

        # Run model inference
        prediction_result = model_inference.predict(save_path)

        if 'error' in prediction_result:
            return jsonify({
                'error': prediction_result['error'],
                'request_id': request_id,
                'processing_time': prediction_result.get('processing_time', 0)
            }), 500

        # Prepare response
        response_data = {
            'predictions': prediction_result['predictions'],
            'top_prediction': prediction_result['top_prediction'],
            'confidence': prediction_result['top_prediction']['confidence'] if prediction_result['top_prediction'] else 0,
            'prediction': prediction_result['top_prediction']['class'] if prediction_result['top_prediction'] else 'unknown',
            'processing_time': prediction_result['processing_time'],
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'cached': False,
            'model_version': prediction_result.get('model_version', 'v1.0'),
            'image_hash': image_hash[:16]  # First 16 chars for debugging
        }

        # Cache the result
        cache_success = cache_manager.cache_prediction(
            image_hash=image_hash,
            prediction_data=response_data,
            model_version=prediction_result.get('model_version', 'v1.0')
        )

        if cache_success:
            logger.info(f"Cached prediction for image hash: {image_hash[:8]}...")
        else:
            logger.warning(f"Failed to cache prediction for image hash: {image_hash[:8]}...")

        # Clean up uploaded file
        try:
            os.remove(save_path)
        except Exception as e:
            logger.warning(f"Failed to clean up file {save_path}: {e}")

        logger.info(f"Prediction completed for request {request_id} in {prediction_result['processing_time']:.3f}s")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Prediction error for request {request_id}: {str(e)}", exc_info=True)
        processing_time = time.time() - start_time
        return jsonify({
            'error': 'Internal server error',
            'request_id': request_id,
            'processing_time': round(processing_time, 3)
        }), 500


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

        # Sanitize request ID from headers
        request_id = InputValidator.sanitize_string(
            request.headers.get('X-Request-ID', 'unknown'),
            max_length=64
        )

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



# =========================
# HEALTH CHECK
# =========================

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

        # Get cache stats
        cache_stats = cache_manager.get_cache_stats()

        # Get model info
        model_info = model_inference.get_model_info()

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
            'cache': cache_stats,
            'model': {
                'loaded': model_info['model_type'] != 'dummy',
                'type': model_info['model_type'],
                'classes': len(model_info['classes']),
                'device': model_info['device']
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


@app.route('/cache/stats', methods=['GET'])
@limiter.limit("10 per minute")
@require_api_key
def cache_stats():
    """Get cache performance statistics"""
    try:
        stats = cache_manager.get_cache_stats()
        return jsonify({
            'cache_stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return jsonify({'error': 'Failed to get cache stats'}), 500


@app.route('/cache/invalidate', methods=['POST'])
@limiter.limit("5 per minute")
@require_api_key
def invalidate_cache():
    """Invalidate cache entries"""
    try:
        data = request.get_json() or {}
        image_hash = data.get('image_hash')
        model_version = data.get('model_version', 'v1')

        invalidated_count = cache_manager.invalidate_cache(image_hash, model_version)

        return jsonify({
            'message': f'Invalidated {invalidated_count} cache entries',
            'image_hash': image_hash,
            'model_version': model_version,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return jsonify({'error': 'Failed to invalidate cache'}), 500


@app.route('/api/info', methods=['GET'])
@limiter.limit("30 per minute")
def api_info():
    return jsonify({
        'name': 'FlavorSnap API',
        'version': '2.0.0',
        'endpoints': {
            'predict': 'POST /predict - Food classification with caching',
            'health': 'GET /health - Health check with cache stats',
            'health_detailed': 'GET /health/detailed - Detailed health metrics',
            'health_database': 'GET /health/database - Database connectivity check',
            'health_redis': 'GET /health/redis - Redis connectivity check',
            'health_model': 'GET /health/model - ML model status check',
            'health_system': 'GET /health/system - System resources check',
            'health_dependencies': 'GET /health/dependencies - Dependencies check',
            'metrics': 'GET /metrics - Prometheus metrics',
            'dashboard': 'GET /dashboard - Performance dashboard',
            'info': 'GET /api/info - API information',
            'cache_stats': 'GET /cache/stats - Cache performance statistics',
            'cache_invalidate': 'POST /cache/invalidate - Invalidate cache entries',
            'admin_api_key': 'POST /admin/api-key/generate - Generate API key'
        },
        'caching': {
            'enabled': True,
            'type': 'Redis with in-memory fallback',
            'ttl_seconds': 3600,
            'hash_based_deduplication': True,
            'stats_tracking': True
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
        'status': 'healthy',
        'model_loaded': model is not None,
        'version': '1.0.0',
        'analytics_enabled': True
    })


# =========================
# ENTRY POINT
# =========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
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
