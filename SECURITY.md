# SECURITY.md — Threat model and controls

Scope: a public demo web app with no user accounts that accepts image uploads and runs a local PyTorch model. Assets: server availability, stored images and feedback, and the model files. **The project uses no API keys, tokens or passwords of any kind.** The CNN is trained and run locally.

## 1. Threats → controls
| # | Threat | Control (must be implemented and tested) |
|---|---|---|
| T1 | Malicious upload (non-image, polyglot, script, SVG) | Allowlist `image/jpeg, image/png, image/webp`. Check the type by **decoding with Pillow** (`Image.open` + `verify()`, then reopen), not by trusting the extension or `Content-Type`. Reject SVG/GIF/HEIC (unless HEIC is converted on the client). |
| T2 | Decompression bomb / huge image | Reject at `MAX_UPLOAD_MB` (8) while streaming. `Image.MAX_IMAGE_PIXELS = 40_000_000` and treat `DecompressionBombWarning` as an error. Downscale to ≤ 1024 px before storing. |
| T3 | Privacy leak via EXIF (GPS) | **Re-encode** every stored image as JPEG q90 from pixel data, which strips all metadata. Never store the original bytes. |
| T4 | Path traversal / arbitrary file read | Stored filenames are `uuid4().hex + ".jpg"`. Files are served **only by prediction id** through a DB lookup. No user-supplied paths anywhere. |
| T5 | IDOR on predictions | No accounts, so history is a public demo by design (stated on the About page). Ids are random UUIDv4 (not guessable). Delete is admin-only. |
| T6 | Abuse / DoS of the costly `/predict` | slowapi rate limit `20/minute` per client IP (in memory, not persisted), global request body limit, Uvicorn `--limit-concurrency 32`, inference in a bounded threadpool, 15 s timeout. |
| T7 | Admin endpoints (export feedback, delete scan) | **Localhost-only, no token.** A dependency checks `request.client.host in {"127.0.0.1", "::1"}` and returns 403 otherwise. The Next.js proxy forwards admin routes **only** in development, and blocks `/api/v1/admin/*` in production builds. |
| T8 | XSS | React escapes by default. **No `dangerouslySetInnerHTML`.** Feedback comments are plain text, ≤ 280 chars, and stripped of control characters on the server. Strict CSP (below). |
| T9 | CSRF | No cookies or sessions, so there is no ambient auth. Admin routes are localhost-only. |
| T10 | CORS misuse | The frontend proxies `/api` via Next rewrites (same origin). The backend allows only `ALLOWED_ORIGINS` and never `*` with credentials. |
| T11 | Secrets in repo | No secrets are needed to run locally. The optional `.env` is gitignored, and `.env.example` holds only defaults (no real values). Run `gitleaks detect` (or `git grep -nE "(api[_-]?key|secret|token)\s*="`) before every milestone sign-off. |
| T12 | Dependency vulnerabilities | Pinned versions. Run `pip-audit` (ml, backend) and `pnpm audit --prod` (frontend) at each milestone; fix highs or log why not. |
| T13 | Unsafe model loading (pickle) | `torch.load(path, map_location=..., weights_only=True)` **always**. Load only from `MODEL_DIR`. Model names are validated against the registry allowlist. |
| T14 | Error leaks | Generic error JSON with `request_id`. Stack traces only in server logs. `debug=False` outside dev. |
| T15 | Log injection / PII | Structured JSON logs (`request_id, method, path, status, ms, model`). Never log image bytes, tokens or IPs beyond the rate limiter's memory. |

## 2. HTTP security headers (both backend responses and Next.js pages)
```
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:;
  script-src 'self' 'nonce-{per-request}' ; style-src 'self' 'unsafe-inline'; font-src 'self';
  connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'
Strict-Transport-Security: max-age=31536000; includeSubDomains   (production/HTTPS only)
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(self), microphone=(), geolocation=(), interest-cohort=()
X-Frame-Options: DENY
Cross-Origin-Opener-Policy: same-origin
```
- Next.js: set via `middleware.ts` (nonce-based CSP for scripts) plus `headers()` in `next.config.ts`. Dev mode may need `'unsafe-eval'` **only when `NODE_ENV=development`**.
- Backend: middleware adds the same headers to every response (API responses can use `default-src 'none'; frame-ancestors 'none'`).
- `camera=(self)` is required for the scanner and must not be blocked.
- **Verification:** `curl -sI http://localhost:3000/ | grep -iE "content-security|x-content|referrer|permissions|x-frame"`, the same for `http://localhost:8000/api/v1/health/live`, plus a Playwright test that checks the headers.

## 3. Security tests (pytest, backend/tests/test_security.py)
- Upload a `.txt` renamed to `.jpg` → 415. A 9 MB file → 413. A 20000×20000 PNG bomb → 413/422. A JPEG with GPS EXIF → the stored file has no EXIF.
- `GET /api/v1/predictions/../../etc/passwd/image` → 404/422.
- Admin endpoints from a non-localhost client (simulate with the TestClient `client=("10.0.0.5", 1234)`) → 403. From 127.0.0.1 → 200.
- 21 predict calls in a minute → the 21st returns 429.
- Unknown `model=` → 422 (allowlist).
- All responses include the security headers.
