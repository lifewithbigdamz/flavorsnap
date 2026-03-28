# Input Validation Implementation

## Overview

This document describes the comprehensive input validation implementation for the FlavorSnap API backend, addressing security vulnerabilities related to file uploads.

## Issue Reference

**Branch:** `no-input-validation`  
**Component:** Backend API  
**Priority:** Security Enhancement

## Problem Statement

The API previously accepted any file type and size without proper validation, creating potential security vulnerabilities including:

- Malicious file uploads
- Server resource exhaustion
- Path traversal attacks
- Code injection attempts

## Implementation

### 1. File Type Validation ✅

**Location:** `security_config.py` - `SecurityConfig.ALLOWED_EXTENSIONS`

**Accepted formats:**

- JPG/JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- WebP (`.webp`)

**Rejected formats:**

- GIF, BMP, SVG, TIFF, and all other formats
- Executable files (.exe, .sh, .bat)
- Script files (.js, .py, .php)

**Implementation:**

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp'
}
```

**Validation checks:**

- File extension validation
- MIME type verification
- Actual image format verification using PIL

### 2. File Size Limit ✅

**Location:** `security_config.py` - `SecurityConfig.MAX_CONTENT_LENGTH`

**Limit:** 10MB (10,485,760 bytes)

**Implementation:**

```python
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
```

**Validation:**

- File size checked before processing
- Clear error message when limit exceeded
- Prevents memory exhaustion attacks

### 3. Image Dimension Validation ✅

**Location:** `security_config.py` - `SecurityConfig.MIN_IMAGE_WIDTH/HEIGHT`

**Requirements:**

- Minimum width: 100px
- Minimum height: 100px
- Maximum width: 10,000px (prevents memory exhaustion)
- Maximum height: 10,000px (prevents memory exhaustion)

**Implementation:**

```python
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100
MAX_IMAGE_WIDTH = 10000
MAX_IMAGE_HEIGHT = 10000
```

**Validation:**

- Uses PIL to read actual image dimensions
- Rejects images below minimum size
- Rejects excessively large images

### 4. Filename and Path Sanitization ✅

**Location:** `security_config.py` - `InputValidator.secure_filename_custom()`

**Protection against:**

- Path traversal attacks (`../`, `..\\`)
- Special characters and script injection
- Null byte injection
- Directory manipulation

**Implementation features:**

- Removes path components using `os.path.basename()`
- Uses Werkzeug's `secure_filename()` as base
- Additional regex sanitization
- Timestamp addition to prevent collisions
- Lowercase extension normalization

**Example:**

```python
Input:  "../../../etc/passwd"
Output: "passwd_20240327_143022.jpg"

Input:  "test<script>.jpg"
Output: "testscript_20240327_143022.jpg"
```

### 5. Malicious File Detection ✅

**Location:** `security_config.py` - `InputValidator.validate_file_upload()`

**Detection methods:**

1. **File format verification:** Uses PIL to verify file is actually an image
2. **Image integrity check:** Calls `img.verify()` to detect corruption
3. **Metadata scanning:** Checks for suspicious content in EXIF/metadata
4. **Empty file detection:** Rejects zero-byte files
5. **MIME type validation:** Ensures Content-Type matches allowed types

**Suspicious patterns detected:**

- `<script>` tags in metadata
- `javascript:` URIs
- `data:` URIs
- `vbscript:` code

### 6. Error Responses ✅

**Location:** `security_config.py` - `InputValidator.validate_file_upload()`

**Clear error messages for:**

- No file provided
- Empty filename
- Invalid file extension
- Unsupported MIME type
- File too large (with size limit)
- Image too small (with minimum dimensions)
- Image too large (with maximum dimensions)
- Corrupted or invalid image
- Suspicious content detected

**Example responses:**

```json
{
  "error": "File too large. Maximum size: 10.0MB"
}

{
  "error": "Image too small. Minimum dimensions: 100x100px"
}

{
  "error": "Unsupported file type. Allowed types: jpg, png, webp"
}
```

## API Integration

### Endpoint: POST /predict

The validation is integrated into the main prediction endpoint:

```python
@app.route('/predict', methods=['POST'])
@limiter.limit(SecurityConfig.RATE_LIMITS['predict'])
@require_api_key
def predict():
    # Validate file upload
    is_valid, error_msg = InputValidator.validate_file_upload(file)
    if not is_valid:
        logger.warning(f"File validation failed: {error_msg}")
        return jsonify({'error': error_msg}), 400

    # Generate secure filename
    filename = InputValidator.secure_filename_custom(file.filename)
    # ... process file
```

## Testing

### Test Suite

**Location:** `test_input_validation.py`

**Test coverage:**

- File type validation (8 tests)
- File size validation (3 tests)
- Image dimension validation (5 tests)
- Filename sanitization (5 tests)
- Malicious file detection (4 tests)
- Error responses (3 tests)

**Run tests:**

```bash
cd ml-model-api
python -m pytest test_input_validation.py -v
```

### Manual Validation

**Location:** `validate_implementation.py`

**Run validation:**

```bash
cd ml-model-api
python validate_implementation.py
```

## Dependencies

### New Dependencies Added

**File:** `ml-model-api/requirements.txt`

```
Flask==3.0.0
flask-cors==4.0.0
flask-limiter==3.5.0
werkzeug==3.0.1
bleach==6.1.0
redis==5.0.1
Pillow==10.2.0  # Added for image validation
```

**Install dependencies:**

```bash
pip install -r ml-model-api/requirements.txt
```

## Security Benefits

1. **Prevents malicious uploads:** Only valid image files accepted
2. **Protects server resources:** File size and dimension limits prevent DoS
3. **Blocks path traversal:** Filename sanitization prevents directory attacks
4. **Detects disguised files:** Format verification catches fake images
5. **Provides clear feedback:** Detailed error messages for debugging

## Configuration

### Environment Variables

```bash
# Flask configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# File upload limits (optional, defaults shown)
MAX_CONTENT_LENGTH=10485760  # 10MB in bytes
```

### Customization

To modify validation rules, edit `security_config.py`:

```python
class SecurityConfig:
    # Change allowed formats
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # Change size limit
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    # Change dimension limits
    MIN_IMAGE_WIDTH = 100
    MIN_IMAGE_HEIGHT = 100
    MAX_IMAGE_WIDTH = 10000
    MAX_IMAGE_HEIGHT = 10000
```

## API Documentation Update

### Updated /api/info Response

```json
{
  "security": {
    "file_upload_limits": {
      "max_size": "10485760 bytes",
      "allowed_types": ["image/jpeg", "image/png", "image/webp"],
      "min_dimensions": "100x100px",
      "max_dimensions": "10000x10000px"
    }
  }
}
```

## Acceptance Criteria Status

| Criteria                                     | Status   | Implementation                               |
| -------------------------------------------- | -------- | -------------------------------------------- |
| ✅ Validate file types (jpg, png, webp only) | Complete | `SecurityConfig.ALLOWED_EXTENSIONS`          |
| ✅ Limit file size (max 10MB)                | Complete | `SecurityConfig.MAX_CONTENT_LENGTH`          |
| ✅ Validate image dimensions (min 100x100px) | Complete | `SecurityConfig.MIN_IMAGE_*`                 |
| ✅ Sanitize file names and paths             | Complete | `InputValidator.secure_filename_custom()`    |
| ✅ Malicious file detection                  | Complete | `InputValidator.validate_file_upload()`      |
| ✅ Proper error responses                    | Complete | All validation functions return clear errors |

## Migration Notes

### Breaking Changes

- Files larger than 10MB will now be rejected (previously 16MB)
- GIF format no longer accepted
- Images smaller than 100x100px will be rejected

### Backward Compatibility

- Existing valid uploads (jpg, png, webp) continue to work
- API response format unchanged
- Error response format consistent with existing patterns

## Monitoring

### Logging

All validation failures are logged with details:

```python
logger.warning(f"File validation failed: {error_msg}")
```

### Metrics to Monitor

- Validation failure rate
- Most common rejection reasons
- File size distribution
- Image dimension distribution

## Future Enhancements

Potential improvements for future iterations:

1. Add support for HEIC/HEIF formats
2. Implement virus scanning integration
3. Add image content analysis (NSFW detection)
4. Implement rate limiting per user
5. Add file hash checking for duplicates
6. Implement automatic image optimization

## References

- [OWASP File Upload Security](https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload)
- [Werkzeug Security Documentation](https://werkzeug.palletsprojects.com/en/latest/utils/#werkzeug.utils.secure_filename)
- [Pillow Security Considerations](https://pillow.readthedocs.io/en/stable/releasenotes/index.html)

## Support

For issues or questions about this implementation:

1. Check the test suite for examples
2. Review error messages in logs
3. Consult this documentation
4. Contact the development team

---

**Last Updated:** 2024-03-27  
**Version:** 1.0.0  
**Author:** Development Team
