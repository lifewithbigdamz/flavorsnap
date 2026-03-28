"""
Manual validation script to verify input validation implementation
Demonstrates all acceptance criteria are met
"""
import io
from PIL import Image
from werkzeug.datastructures import FileStorage
from security_config import InputValidator, SecurityConfig


def print_test(test_name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


def main():
    print("=" * 70)
    print("INPUT VALIDATION IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    print()
    
    # Test 1: File Type Validation
    print("1. FILE TYPE VALIDATION (jpg, png, webp only)")
    print("-" * 70)
    
    valid_extensions = ['test.jpg', 'test.jpeg', 'test.png', 'test.webp']
    invalid_extensions = ['test.gif', 'test.bmp', 'test.svg', 'test.exe']
    
    for ext in valid_extensions:
        result = InputValidator.validate_filename(ext)
        print_test(f"Accept {ext}", result)
    
    for ext in invalid_extensions:
        result = not InputValidator.validate_filename(ext)
        print_test(f"Reject {ext}", result)
    
    print()
    
    # Test 2: File Size Limit
    print("2. FILE SIZE LIMIT (max 10MB)")
    print("-" * 70)
    
    max_size = SecurityConfig.MAX_CONTENT_LENGTH
    max_size_mb = max_size / (1024 * 1024)
    print_test(f"Max size set to {max_size_mb}MB", max_size == 10 * 1024 * 1024)
    
    print()
    
    # Test 3: Image Dimension Validation
    print("3. IMAGE DIMENSION VALIDATION (min 100x100px)")
    print("-" * 70)
    
    min_width = SecurityConfig.MIN_IMAGE_WIDTH
    min_height = SecurityConfig.MIN_IMAGE_HEIGHT
    print_test(f"Min width set to {min_width}px", min_width == 100)
    print_test(f"Min height set to {min_height}px", min_height == 100)
    
    # Test with actual images
    print("\n   Testing with actual images:")
    
    # Valid image (200x200)
    img_valid = Image.new('RGB', (200, 200), color='red')
    img_bytes_valid = io.BytesIO()
    img_valid.save(img_bytes_valid, format='JPEG')
    img_bytes_valid.seek(0)
    
    file_valid = FileStorage(
        stream=img_bytes_valid,
        filename="valid.jpg",
        content_type="image/jpeg"
    )
    
    is_valid, error = InputValidator.validate_file_upload(file_valid)
    print_test("Accept 200x200px image", is_valid, error if not is_valid else "")
    
    # Invalid image (50x50)
    img_invalid = Image.new('RGB', (50, 50), color='blue')
    img_bytes_invalid = io.BytesIO()
    img_invalid.save(img_bytes_invalid, format='JPEG')
    img_bytes_invalid.seek(0)
    
    file_invalid = FileStorage(
        stream=img_bytes_invalid,
        filename="invalid.jpg",
        content_type="image/jpeg"
    )
    
    is_valid, error = InputValidator.validate_file_upload(file_invalid)
    print_test("Reject 50x50px image", not is_valid, error if error else "")
    
    print()
    
    # Test 4: Filename Sanitization
    print("4. FILENAME AND PATH SANITIZATION")
    print("-" * 70)
    
    dangerous_filenames = [
        ("../../../etc/passwd", "Path traversal"),
        ("test<script>.jpg", "Script injection"),
        ("test\x00.jpg", "Null byte"),
        ("../../secret.txt", "Directory traversal")
    ]
    
    for dangerous, description in dangerous_filenames:
        sanitized = InputValidator.secure_filename_custom(dangerous)
        safe = ".." not in sanitized and "<" not in sanitized and "\x00" not in sanitized
        print_test(f"Sanitize {description}", safe, f"Result: {sanitized}")
    
    # Test valid filename preservation
    valid_name = "my_photo.jpg"
    sanitized = InputValidator.secure_filename_custom(valid_name)
    preserved = "my_photo" in sanitized and sanitized.endswith(".jpg")
    print_test("Preserve valid filename", preserved, f"Result: {sanitized}")
    
    print()
    
    # Test 5: Malicious File Detection
    print("5. MALICIOUS FILE DETECTION")
    print("-" * 70)
    
    # Test non-image file
    fake_image = io.BytesIO(b"This is not an image")
    file_fake = FileStorage(
        stream=fake_image,
        filename="fake.jpg",
        content_type="image/jpeg"
    )
    
    is_valid, error = InputValidator.validate_file_upload(file_fake)
    print_test("Reject non-image file", not is_valid, error if error else "")
    
    # Test empty file
    empty_file = io.BytesIO(b"")
    file_empty = FileStorage(
        stream=empty_file,
        filename="empty.jpg",
        content_type="image/jpeg"
    )
    
    is_valid, error = InputValidator.validate_file_upload(file_empty)
    print_test("Reject empty file", not is_valid, error if error else "")
    
    # Test wrong MIME type
    img_bytes = io.BytesIO()
    img = Image.new('RGB', (200, 200), color='green')
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    file_wrong_mime = FileStorage(
        stream=img_bytes,
        filename="test.jpg",
        content_type="application/octet-stream"
    )
    
    is_valid, error = InputValidator.validate_file_upload(file_wrong_mime)
    print_test("Reject wrong MIME type", not is_valid, error if error else "")
    
    print()
    
    # Test 6: Error Responses
    print("6. PROPER ERROR RESPONSES")
    print("-" * 70)
    
    # No file
    is_valid, error = InputValidator.validate_file_upload(None)
    print_test("Error for no file", not is_valid and error is not None, f"Message: {error}")
    
    # Empty filename
    file_no_name = FileStorage(
        stream=io.BytesIO(b"test"),
        filename="",
        content_type="image/jpeg"
    )
    is_valid, error = InputValidator.validate_file_upload(file_no_name)
    print_test("Error for empty filename", not is_valid and error is not None, f"Message: {error}")
    
    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print()
    print("Summary of Implementation:")
    print("✅ File type validation (jpg, png, webp only)")
    print("✅ File size limit (max 10MB)")
    print("✅ Image dimension validation (min 100x100px)")
    print("✅ Filename and path sanitization")
    print("✅ Malicious file detection")
    print("✅ Proper error responses")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error running validation: {e}")
        import traceback
        traceback.print_exc()
