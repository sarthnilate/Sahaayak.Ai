from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # CSP tailored for React SPA with Leaflet maps and Google Fonts
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob: https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org",
            "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

        return response


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """
    Enforces double-submit CSRF cookie/header verification on all state-changing
    requests (POST, PUT, PATCH, DELETE) for authenticated or session-bound clients.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        import secrets

        from fastapi.responses import JSONResponse

        # Safe HTTP methods do not mutate state
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        # Allow initial credential handshake and test seed endpoints
        if (
            path.endswith("/auth/login")
            or path.endswith("/auth/register")
            or path.endswith("/auth/logout")
            or path.endswith("/seed")
            or path in ("/docs", "/openapi.json")
        ):
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        auth_cookie = request.cookies.get("access_token")

        # If user has an auth session cookie or csrf token cookie, require double-submit match
        if csrf_cookie or auth_cookie:
            if (
                not csrf_cookie
                or not csrf_header
                or not secrets.compare_digest(csrf_cookie, csrf_header)
            ):
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_VALIDATION_FAILED",
                            "message": "CSRF validation failed: Missing or mismatched X-CSRF-Token header",
                            "details": {},
                            "request_id": request_id,
                        }
                    },
                )

        return await call_next(request)
