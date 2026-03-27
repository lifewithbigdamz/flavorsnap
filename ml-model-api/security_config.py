"""
Security configuration and middleware for FlavorSnap API
"""
import os
import re
import hashlib
import hmac
from datetime import datetime, timedelta
from PIL import Image
import io

class SecurityConfig:
    """Security configuration class"""

    RATE_LIMITS = {
        # Default limits for unauthenticated requests
        'default': '20 per minute',
        'health': '1000 per hour',
        'api_info': '30 per minute',
        
        # Free tier limits (authenticated)
        'free_predict': '10 per minute',
        'free_upload': '5 per minute',
        'free_admin': '5 per minute',
        'free_dashboard': '20 per minute',
        
        # Premium tier limits (authenticated)
        'premium_predict': '100 per minute',
        'premium_upload': '50 per minute',
        'premium_admin': '20 per minute',
        'premium_dashboard': '100 per minute',
        
        # Enterprise tier limits (authenticated)
        'enterprise_predict': '500 per minute',
        'enterprise_upload': '200 per minute',
        'enterprise_admin': '100 per minute',
        'enterprise_dashboard': '500 per minute'
    }
    
    # API key tiers and their prefixes
    API_KEY_TIERS = {
        'free': {'prefix': 'free_', 'weight': 1},
        'premium': {'prefix': 'prem_', 'weight': 5},
        'enterprise': {'prefix': 'ent_', 'weight': 10}
    }
    
    # File upload security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp'
    }
    
    # Image dimension constraints
    MIN_IMAGE_WIDTH = 100
    MIN_IMAGE_HEIGHT = 100
    MAX_IMAGE_WIDTH = 10000  # Prevent memory exhaustion
    MAX_IMAGE_HEIGHT = 10000
    
    # Input validation patterns
    PATTERNS = {
        'filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'api_key': re.compile(r'^[a-zA-Z0-9]{32,}$'),
        'request_id': re.compile(r'^[a-zA-Z0-9\-_]{8,64}$')
    }

    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }


class InputValidator:
    """Input validation and sanitization utilities"""

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        if not text:
            return ""
        # Strip HTML tags with a simple regex (avoids bleach dependency)
        cleaned = re.sub(r'<[^>]+>', '', text)
        return cleaned[:max_length].strip()

    @staticmethod
    def validate_filename(filename: str) -> bool:
        if not filename:
            return False
        if not SecurityConfig.PATTERNS['filename'].match(filename):
            return False
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return ext in SecurityConfig.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        if not api_key:
            return False
        return bool(SecurityConfig.PATTERNS['api_key'].match(api_key))

    @staticmethod
    def validate_file_upload(file) -> tuple[bool, Optional[str]]:
        """Validate uploaded file with comprehensive security checks"""
        if not file:
            return False, "No file provided"
        if file.filename == '':
            return False, "Empty filename"
        
        # Validate filename format and extension
        if not InputValidator.validate_filename(file.filename):
            return False, "Invalid filename format or unsupported file extension"
        
        # Validate MIME type
        if file.content_type not in SecurityConfig.ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type. Allowed types: jpg, png, webp"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size == 0:
            return False, "File is empty"
        
        if file_size > SecurityConfig.MAX_CONTENT_LENGTH:
            max_size_mb = SecurityConfig.MAX_CONTENT_LENGTH / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_size_mb}MB"
        
        # Validate image dimensions and detect malicious files
        try:
            file_data = file.read()
            file.seek(0)  # Reset file pointer
            
            # Attempt to open as image (will fail for malicious files)
            img = Image.open(io.BytesIO(file_data))
            
            # Verify image format matches extension
            img_format = img.format.lower() if img.format else ''
            allowed_formats = {'jpeg', 'jpg', 'png', 'webp'}
            if img_format not in allowed_formats:
                return False, f"Invalid image format. Allowed formats: jpg, png, webp"
            
            # Check image dimensions
            width, height = img.size
            
            if width < SecurityConfig.MIN_IMAGE_WIDTH or height < SecurityConfig.MIN_IMAGE_HEIGHT:
                return False, f"Image too small. Minimum dimensions: {SecurityConfig.MIN_IMAGE_WIDTH}x{SecurityConfig.MIN_IMAGE_HEIGHT}px"
            
            if width > SecurityConfig.MAX_IMAGE_WIDTH or height > SecurityConfig.MAX_IMAGE_HEIGHT:
                return False, f"Image too large. Maximum dimensions: {SecurityConfig.MAX_IMAGE_WIDTH}x{SecurityConfig.MAX_IMAGE_HEIGHT}px"
            
            # Verify image can be loaded (detects corrupted/malicious files)
            img.verify()
            
            # Re-open for additional checks after verify()
            img = Image.open(io.BytesIO(file_data))
            
            # Check for suspicious metadata or embedded scripts
            if hasattr(img, 'info') and img.info:
                # Check for suspicious keys in metadata
                suspicious_keys = ['comment', 'software', 'exif']
                for key in suspicious_keys:
                    if key in img.info:
                        value = str(img.info[key]).lower()
                        if any(pattern in value for pattern in ['<script', 'javascript:', 'data:', 'vbscript:']):
                            return False, "Suspicious content detected in image metadata"
            
        except Exception as e:
            return False, f"Invalid or corrupted image file: {str(e)}"
        
        return True, None

    @staticmethod
    def secure_filename_custom(filename: str) -> str:
        """Custom secure filename generation with path traversal protection"""
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Use Werkzeug's secure_filename as base
        secure_name = secure_filename(filename)
        
        # Additional sanitization: remove any remaining suspicious characters
        secure_name = re.sub(r'[^\w\s.-]', '', secure_name)
        
        # Prevent path traversal attempts
        if '..' in secure_name or secure_name.startswith('.'):
            secure_name = secure_name.replace('..', '').lstrip('.')
        
        # Add timestamp to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(secure_name)
        
        # Ensure extension is lowercase and valid
        ext = ext.lower()
        if ext.lstrip('.') not in SecurityConfig.ALLOWED_EXTENSIONS:
            ext = '.jpg'  # Default to jpg if invalid
        
        return f"{name}_{timestamp}{ext}"


class APIKeyManager:
    """API key management utilities"""

    @staticmethod
    def generate_api_key() -> str:
        import secrets
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        return hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            hashed_key
        )


class RateLimitManager:
    """Rate limiting utilities"""

    @staticmethod
    def get_client_ip() -> str:
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'

    @staticmethod
    def get_rate_limit_key(endpoint: str = None) -> str:
        ip = RateLimitManager.get_client_ip()
        endpoint = endpoint or request.endpoint or 'unknown'
        return f"rate_limit:{endpoint}:{ip}"
    
    @staticmethod
    def get_api_key_tier(api_key: str) -> str:
        """Determine API key tier from key format"""
        if not api_key:
            return 'default'
        
        for tier, config in SecurityConfig.API_KEY_TIERS.items():
            if api_key.startswith(config['prefix']):
                return tier
        
        # Default to free tier for unrecognized keys
        return 'free'
    
    @staticmethod
    def get_rate_limit_for_endpoint(endpoint: str, api_key: str = None) -> str:
        """Get appropriate rate limit for endpoint based on API key tier"""
        tier = RateLimitManager.get_api_key_tier(api_key)
        
        # Map endpoints to rate limit keys
        endpoint_mapping = {
            'predict': f'{tier}_predict',
            'upload': f'{tier}_upload', 
            'generate_api_key': f'{tier}_admin',
            'performance_dashboard': f'{tier}_dashboard',
            'api_info': 'api_info',
            'health_check': 'health'
        }
        
        rate_limit_key = endpoint_mapping.get(endpoint, 'default')
        return SecurityConfig.RATE_LIMITS.get(rate_limit_key, SecurityConfig.RATE_LIMITS['default'])
    
    @staticmethod
    def get_tiered_key_func():
        """Key function that considers both IP and API tier"""
        def tiered_key():
            api_key = request.headers.get('X-API-Key')
            tier = RateLimitManager.get_api_key_tier(api_key)
            ip = RateLimitManager.get_client_ip()
            return f"{tier}:{ip}"
        return tiered_key


class SecurityMiddleware:
    """Security middleware for Flask application"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self._app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        content_length = request.content_length or 0
        if content_length > SecurityConfig.MAX_CONTENT_LENGTH:
            abort(413, description="Request too large")
        self._log_request()

    def after_request(self, response):
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    def _log_request(self):
        ip = RateLimitManager.get_client_ip()
        suspicious_patterns = ['../', '<script', 'javascript:', 'data:', 'vbscript:', 'onload=', 'onerror=']
        request_data = str(request.data) if request.data else ""
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                self._app.logger.warning(f"Suspicious request from {ip}: pattern '{pattern}' detected")
                break


class SecurityMonitor:
    """Security monitoring and alerting"""

    def __init__(self, app=None):
        self.app = app
        self.suspicious_ips: Dict[str, Any] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self._app = app
        app.before_request(self.monitor_request)

    def monitor_request(self):
        ip = RateLimitManager.get_client_ip()
        current_time = datetime.now()
        if ip not in self.suspicious_ips:
            self.suspicious_ips[ip] = {'count': 0, 'first_seen': current_time}
        self.suspicious_ips[ip]['count'] += 1
        if self._is_suspicious(ip):
            self._app.logger.warning(f"Suspicious activity detected from {ip}")

    def _is_suspicious(self, ip: str) -> bool:
        data = self.suspicious_ips[ip]
        if data['count'] > 1000:
            return True
        time_diff = datetime.now() - data['first_seen']
        if time_diff.total_seconds() < 60 and data['count'] > 100:
            return True
        return False


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    if url.startswith(('//', 'http://', 'https://')):
        return False
    return True


def validate_json_input(data: Dict[str, Any], required_fields: list = None) -> Tuple[bool, Optional[str]]:
    if not isinstance(data, dict):
        return False, "Invalid JSON format"
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
    return True, None
