"""
Security configuration and middleware for FlavorSnap API
"""
import os
import bleach
import re
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available. Using fallback MIME detection.")
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from flask import request, abort
from werkzeug.utils import secure_filename
import hmac
from datetime import datetime, timedelta
import logging
from PIL import Image
import io

class SecurityConfig:
    """Security configuration class"""
    
    # Rate limiting configurations with tier-based access
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
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png', 
        'image/gif',
        'image/webp'
    }
    # Malicious file signatures
    MALICIOUS_SIGNATURES = {
        b'\x4D\x5A',  # PE executable
        b'\x7FELF',   # ELF executable
        b'\xCA\xFE\xBA\xBE',  # Java class
        b'\xD0\xCF\x11\xE0',  # Microsoft Office
        b'PK\x03\x04',  # ZIP (could contain malicious content)
    }
    # Image validation thresholds
    MAX_IMAGE_DIMENSION = 8192
    MIN_IMAGE_DIMENSION = 32
    
    # Input validation patterns
    PATTERNS = {
        'filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'api_key': re.compile(r'^[a-zA-Z0-9]{32,}$'),
        'request_id': re.compile(r'^[a-zA-Z0-9-_]{8,64}$')
    }
    
    # Security headers
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
        """Sanitize string input"""
        if not text:
            return ""
        
        # Clean HTML/Script tags
        cleaned = bleach.clean(text, tags=[], strip=True)
        
        # Limit length
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned.strip()
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename format"""
        if not filename:
            return False
        
        # Check pattern
        if not SecurityConfig.PATTERNS['filename'].match(filename):
            return False
        
        # Check extension
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return ext in SecurityConfig.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        if not api_key:
            return False
        
        return bool(SecurityConfig.PATTERNS['api_key'].match(api_key))
    
    @staticmethod
    def validate_file_upload(file) -> tuple[bool, Optional[str]]:
        """Comprehensive file validation with security checks"""
        if not file:
            return False, "No file provided"
        
        if file.filename == '':
            return False, "Empty filename"
        
        # Validate filename
        if not InputValidator.validate_filename(file.filename):
            return False, "Invalid filename"
        
        # Check file size first
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > SecurityConfig.MAX_CONTENT_LENGTH:
            return False, f"File too large. Max size: {SecurityConfig.MAX_CONTENT_LENGTH // (1024*1024)}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Read file content for validation
        file_content = file.read()
        file.seek(0)
        
        # Check for malicious file signatures
        is_malicious, malicious_msg = InputValidator._check_malicious_signatures(file_content)
        if is_malicious:
            return False, f"Malicious file detected: {malicious_msg}"
        
        # Validate MIME type using python-magic or fallback
        try:
            if MAGIC_AVAILABLE:
                detected_mime = magic.from_buffer(file_content, mime=True)
            else:
                # Fallback: use PIL to detect image format
                try:
                    image = Image.open(io.BytesIO(file_content))
                    format_to_mime = {
                        'JPEG': 'image/jpeg',
                        'PNG': 'image/png',
                        'GIF': 'image/gif',
                        'WEBP': 'image/webp'
                    }
                    detected_mime = format_to_mime.get(image.format, 'application/octet-stream')
                except:
                    detected_mime = file.content_type or 'application/octet-stream'
            
            if detected_mime not in SecurityConfig.ALLOWED_MIME_TYPES:
                return False, f"Unsupported file type detected: {detected_mime}"
        except Exception as e:
            logging.warning(f"MIME type detection failed: {e}")
            # Fallback to content-type header
            if file.content_type not in SecurityConfig.ALLOWED_MIME_TYPES:
                return False, f"Unsupported file type: {file.content_type}"
        
        # Validate image content
        is_valid_image, image_msg = InputValidator._validate_image_content(file_content)
        if not is_valid_image:
            return False, f"Invalid image: {image_msg}"
        
        return True, None
    
    @staticmethod
    def _check_malicious_signatures(file_content: bytes) -> Tuple[bool, str]:
        """Check for malicious file signatures"""
        # Check file header for known malicious signatures
        for signature, description in {
            b'\x4D\x5A': 'PE executable',
            b'\x7FELF': 'ELF executable', 
            b'\xCA\xFE\xBA\xBE': 'Java class',
            b'\xD0\xCF\x11\xE0': 'Microsoft Office',
            b'PK\x03\x04': 'ZIP archive'
        }.items():
            if file_content.startswith(signature):
                return True, description
        
        # Check for script content in image files
        text_content = file_content.decode('utf-8', errors='ignore').lower()
        script_patterns = [
            '<script', 'javascript:', 'vbscript:', 
            'onload=', 'onerror=', 'onclick=',
            'eval(', 'document.', 'window.',
            'php://', 'data://', 'file://'
        ]
        
        for pattern in script_patterns:
            if pattern in text_content:
                return True, f'Script content detected: {pattern}'
        
        return False, ''
    
    @staticmethod
    def _validate_image_content(file_content: bytes) -> Tuple[bool, str]:
        """Validate image content using PIL"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(file_content))
            
            # Verify image format
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                return False, f"Unsupported image format: {image.format}"
            
            # Check image dimensions
            width, height = image.size
            if width < SecurityConfig.MIN_IMAGE_DIMENSION or height < SecurityConfig.MIN_IMAGE_DIMENSION:
                return False, f"Image too small: {width}x{height}"
            
            if width > SecurityConfig.MAX_IMAGE_DIMENSION or height > SecurityConfig.MAX_IMAGE_DIMENSION:
                return False, f"Image too large: {width}x{height}"
            
            # Verify image can be loaded (detects corrupted files)
            image.verify()
            
            # Re-open after verify (verify() closes the image)
            image = Image.open(io.BytesIO(file_content))
            
            # Check for reasonable aspect ratio (to detect panorama attacks)
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 20:  # Very extreme aspect ratios
                return False, f"Extreme aspect ratio: {aspect_ratio:.2f}"
            
            return True, ''
            
        except Exception as e:
            return False, f"Image validation failed: {str(e)}"
    
    @staticmethod
    def secure_filename_custom(filename: str) -> str:
        """Custom secure filename generation"""
        # Use Werkzeug's secure_filename as base
        secure_name = secure_filename(filename)
        
        # Add timestamp to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(secure_name)
        
        return f"{name}_{timestamp}{ext}"

class APIKeyManager:
    """API key management utilities"""
    
    @staticmethod
    def generate_api_key(tier: str = 'free') -> str:
        """Generate a secure API key with tier prefix"""
        import secrets
        
        if tier not in SecurityConfig.API_KEY_TIERS:
            tier = 'free'
        
        prefix = SecurityConfig.API_KEY_TIERS[tier]['prefix']
        random_part = secrets.token_urlsafe(24)  # 32 chars total with prefix
        return f"{prefix}{random_part}"
    
    @staticmethod
    def generate_tiered_api_key(tier: str = 'free') -> dict:
        """Generate API key with tier information"""
        api_key = APIKeyManager.generate_api_key(tier)
        return {
            'api_key': api_key,
            'tier': tier,
            'limits': {
                'predict': SecurityConfig.RATE_LIMITS[f'{tier}_predict'],
                'upload': SecurityConfig.RATE_LIMITS[f'{tier}_upload'],
                'admin': SecurityConfig.RATE_LIMITS[f'{tier}_admin'],
                'dashboard': SecurityConfig.RATE_LIMITS[f'{tier}_dashboard']
            }
        }
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """Verify API key against hash"""
        return hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            hashed_key
        )

class RateLimitManager:
    """Rate limiting utilities with tier-based access"""
    
    @staticmethod
    def get_client_ip() -> str:
        """Get client IP address"""
        # Check for proxy headers
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'
    
    @staticmethod
    def get_rate_limit_key(endpoint: str = None) -> str:
        """Generate rate limit key"""
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
        """Initialize security middleware"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Before request security checks"""
        # Validate request size
        content_length = request.content_length or 0
        if content_length > SecurityConfig.MAX_CONTENT_LENGTH:
            abort(413, description="Request too large")
        
        # Log suspicious activity
        self._log_request()
    
    def after_request(self, response):
        """Add security headers to response"""
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response
    
    def _log_request(self):
        """Log request for security monitoring"""
        ip = RateLimitManager.get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        endpoint = request.endpoint or 'unknown'
        
        # Log suspicious patterns
        suspicious_patterns = [
            '../', '<script', 'javascript:', 'data:',
            'vbscript:', 'onload=', 'onerror='
        ]
        
        request_data = str(request.data) if request.data else ""
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                app.logger.warning(
                    f"Suspicious request from {ip}: {pattern} in {endpoint}"
                )
                break

# Security helper functions
def is_safe_url(url: str) -> bool:
    """Check if URL is safe for redirects"""
    if not url:
        return False
    
    # Prevent open redirects
    if url.startswith(('//', 'http://', 'https://')):
        return False
    
    return True

def validate_json_input(data: Dict[str, Any], required_fields: list = None) -> tuple[bool, Optional[str]]:
    """Validate JSON input"""
    if not isinstance(data, dict):
        return False, "Invalid JSON format"
    
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None

# Security monitoring
class SecurityMonitor:
    """Security monitoring and alerting"""
    
    def __init__(self, app=None):
        self.app = app
        self.suspicious_ips = {}
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security monitor"""
        app.before_request(self.monitor_request)
    
    def monitor_request(self):
        """Monitor requests for suspicious activity"""
        ip = RateLimitManager.get_client_ip()
        current_time = datetime.now()
        
        # Track requests per IP
        if ip not in self.suspicious_ips:
            self.suspicious_ips[ip] = {'count': 0, 'first_seen': current_time}
        
        self.suspicious_ips[ip]['count'] += 1
        
        # Check for unusual patterns
        if self._is_suspicious(ip):
            app.logger.warning(f"Suspicious activity detected from {ip}")
    
    def _is_suspicious(self, ip: str) -> bool:
        """Determine if IP is showing suspicious behavior"""
        data = self.suspicious_ips[ip]
        
        # High request rate
        if data['count'] > 1000:  # More than 1000 requests
            return True
        
        # Check time-based patterns
        time_diff = datetime.now() - data['first_seen']
        if time_diff.total_seconds() < 60 and data['count'] > 100:  # 100 requests in 1 minute
            return True
        
        return False
