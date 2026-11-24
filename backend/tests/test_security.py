"""Security and threat-model compliance tests (SECURITY.md §3)."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app

SAMPLE_IMAGE = Path(settings.REPO_ROOT_DIR) / "data" / "processed" / "waste12" / "test" / "cardboard" / "cardboard_garbage12_01706.jpg"


def test_t1_reject_non_image_polyglot(client: TestClient):
    """T1: Uploading a .txt file disguised as .jpg is rejected with 415."""
    fake_bytes = b"Hello, I am a bash script or text payload pretending to be an image!"
    resp = client.post(
        "/api/v1/predict",
        files={"file": ("malicious.jpg", fake_bytes, "image/jpeg")},
    )
    assert resp.status_code == 415


def test_t2_reject_oversized_file(client: TestClient):
    """T2: Upload exceeding MAX_UPLOAD_MB (8 MB) is rejected with 413."""
    oversized = b"0" * (8 * 1024 * 1024 + 1024)  # > 8 MB
    resp = client.post(
        "/api/v1/predict",
        files={"file": ("huge.jpg", oversized, "image/jpeg")},
    )
    assert resp.status_code == 413


def test_t2_decompression_bomb(client: TestClient):
    """T2: Decompression bomb image (> 40M pixels) is rejected with 413/422."""
    # Create an image header declaring massive spatial resolution
    buf = io.BytesIO()
    # 7000 x 7000 = 49M pixels > MAX_IMAGE_PIXELS (40M)
    bomb_img = Image.new("RGB", (7000, 7000), color=(128, 128, 128))
    bomb_img.save(buf, format="JPEG")
    bomb_bytes = buf.getvalue()

    resp = client.post(
        "/api/v1/predict",
        files={"file": ("bomb.jpg", bomb_bytes, "image/jpeg")},
    )
    assert resp.status_code in {413, 422}


def test_t3_exif_metadata_stripped(client: TestClient):
    """T3: Stored images have all EXIF metadata stripped (privacy protection)."""
    # Create a JPEG with mock EXIF data
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    exif = img.getexif()
    exif[0x010E] = "User location GPS leak"  # ImageDescription tag
    img.save(buf, format="JPEG", exif=exif)
    tagged_bytes = buf.getvalue()

    resp = client.post(
        "/api/v1/predict",
        files={"file": ("tagged.jpg", tagged_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    pred_id = resp.json()["id"]

    # Retrieve stored image from backend
    img_resp = client.get(f"/api/v1/predictions/{pred_id}/image")
    assert img_resp.status_code == 200

    stored_img = Image.open(io.BytesIO(img_resp.content))
    stored_exif = stored_img.getexif()
    assert len(stored_exif) == 0 or 0x010E not in stored_exif, "EXIF tag was not stripped!"


def test_t4_path_traversal_blocked(client: TestClient):
    """T4: Arbitrary path traversal in file endpoints is blocked."""
    resp1 = client.get("/api/v1/predictions/../../etc/passwd/image")
    assert resp1.status_code in {404, 422}

    resp2 = client.get("/api/v1/predictions/..%2F..%2Fetc%2Fpasswd/image")
    assert resp2.status_code in {404, 422}


def test_t6_rate_limiter(client: TestClient):
    """T6: Rate limit enforced at 20 requests per minute on /predict."""
    if not SAMPLE_IMAGE.exists():
        pytest.skip(f"Sample test image {SAMPLE_IMAGE} not found.")

    with open(SAMPLE_IMAGE, "rb") as f:
        file_bytes = f.read()

    # First 20 requests succeed
    for _ in range(20):
        resp = client.post(
            "/api/v1/predict",
            files={"file": ("test.jpg", file_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200

    # 21st request must trigger 429 Too Many Requests
    resp21 = client.post(
        "/api/v1/predict",
        files={"file": ("test.jpg", file_bytes, "image/jpeg")},
    )
    assert resp21.status_code == 429
    assert "Rate limit exceeded" in resp21.json()["error"]


def test_t7_admin_localhost_only(session):
    """T7: Admin endpoints reject non-localhost callers with 403."""
    # Simulate a remote client IP (e.g. 10.0.0.5)
    with TestClient(app, client=("10.0.0.5", 54321)) as remote_client:
        resp = remote_client.get("/api/v1/admin/feedback.csv")
        assert resp.status_code == 403
        assert "localhost" in resp.json()["error"]["message"]

        resp_del = remote_client.delete("/api/v1/admin/predictions/any_id")
        assert resp_del.status_code == 403

    # Localhost client (127.0.0.1) is allowed
    with TestClient(app, client=("127.0.0.1", 54321)) as local_client:
        resp_local = local_client.get("/api/v1/admin/feedback.csv")
        assert resp_local.status_code == 200


def test_t7_admin_rejects_proxied_requests(session):
    """T7: Admin endpoints reject any request carrying reverse proxy headers even from 127.0.0.1."""
    with TestClient(app, client=("127.0.0.1", 54321)) as local_client:
        # Direct local request without proxy headers -> 200
        resp_direct = local_client.get("/api/v1/admin/feedback.csv")
        assert resp_direct.status_code == 200

        # Proxied via X-Forwarded-For -> 403
        resp_xff = local_client.get(
            "/api/v1/admin/feedback.csv",
            headers={"X-Forwarded-For": "192.168.1.50"},
        )
        assert resp_xff.status_code == 403
        assert "reverse proxies" in resp_xff.json()["error"]["message"]

        # Proxied via X-Forwarded-Host -> 403
        resp_xfh = local_client.get(
            "/api/v1/admin/feedback.csv",
            headers={"X-Forwarded-Host": "ecosort.internal"},
        )
        assert resp_xfh.status_code == 403

        # Proxied via X-Real-IP -> 403
        resp_xri = local_client.get(
            "/api/v1/admin/feedback.csv",
            headers={"X-Real-IP": "10.0.0.1"},
        )
        assert resp_xri.status_code == 403

        # Proxied via Forwarded -> 403
        resp_fwd = local_client.get(
            "/api/v1/admin/feedback.csv",
            headers={"Forwarded": "for=192.0.2.60;proto=http;by=203.0.113.43"},
        )
        assert resp_fwd.status_code == 403

        # Delete endpoint also rejects proxy headers -> 403
        resp_del = local_client.delete(
            "/api/v1/admin/predictions/test_pred_id",
            headers={"X-Forwarded-For": "192.168.1.50"},
        )
        assert resp_del.status_code == 403


def test_t13_unknown_model_rejected(client: TestClient):
    """T13: Unknown model names are rejected with 422 (strict allowlist)."""
    if not SAMPLE_IMAGE.exists():
        pytest.skip(f"Sample test image {SAMPLE_IMAGE} not found.")

    with open(SAMPLE_IMAGE, "rb") as f:
        file_bytes = f.read()

    resp = client.post(
        "/api/v1/predict",
        params={"model": "injected_evil_model_pickle"},
        files={"file": ("test.jpg", file_bytes, "image/jpeg")},
    )
    assert resp.status_code == 422
    assert "Unknown model" in resp.json()["error"]["message"]


def test_security_headers_present(client: TestClient):
    """Verify HTTP security headers are present on all responses (SECURITY.md §2)."""
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=(self)" in headers.get("Permissions-Policy", "")
    assert headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none'"
    assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert "X-Request-ID" in headers


def test_docs_relaxed_csp(client: TestClient):
    """Swagger UI (/docs) and OpenAPI schema have relaxed CSP allowing CDN assets."""
    resp = client.get("/docs")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "https://cdn.jsdelivr.net" in csp
    assert "https://fastapi.tiangolo.com" in csp
    assert "'unsafe-inline'" in csp

    resp_openapi = client.get("/openapi.json")
    assert resp_openapi.status_code == 200
    assert "https://cdn.jsdelivr.net" in resp_openapi.headers.get("Content-Security-Policy", "")


def test_docs_disabled_in_production(monkeypatch):
    """When ENV=production, /docs and /redoc are disabled (return 404)."""
    monkeypatch.setattr(settings, "ENV", "production")
    from app.main import create_app

    prod_app = create_app()
    with TestClient(prod_app, client=("127.0.0.1", 50000)) as prod_client:
        resp_docs = prod_client.get("/docs")
        assert resp_docs.status_code == 404

        resp_redoc = prod_client.get("/redoc")
        assert resp_redoc.status_code == 404

        resp_openapi = prod_client.get("/openapi.json")
        assert resp_openapi.status_code == 404
