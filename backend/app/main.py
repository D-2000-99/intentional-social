import logging
import sys
import time
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import auth, posts, feed, connections, tags, connection_tags, insights, comments, digest
from app.config import settings
from app.core.exceptions import AppException
from app.core.deps import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Intentional Social",
    description="A social platform focused on intentional connections",
    version="1.0.0"
)

logger.info("Application starting...")

# Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app)
logger.info("Prometheus metrics enabled at /metrics")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Share limiter with auth router (after import to avoid circular dependency)
auth.limiter = limiter

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Request size limit middleware (security)
@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    """Limit request size to prevent memory exhaustion attacks."""
    max_size = 10 * 1024 * 1024  # 10MB
    
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "type": "RequestTooLarge",
                        "message": "Request size exceeds maximum allowed (10MB)",
                        "status_code": 413
                    }
                }
            )
    
    return await call_next(request)

# Request logging middleware (optimized for production)
# Only log slow requests (>1s), errors, or critical endpoints to reduce CPU overhead
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Skip logging for health checks and metrics (high frequency, low value)
    if request.url.path in ["/health", "/metrics"]:
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Only log slow requests (>1s), errors (4xx/5xx), or auth endpoints
    should_log = (
        duration > 1.0 or  # Slow requests
        response.status_code >= 400 or  # Errors
        request.url.path.startswith("/auth/")  # Auth endpoints (important for security)
    )
    
    if should_log:
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {duration:.2f}s - "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
    
    return response


# CORS configuration from environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(feed.router)
app.include_router(digest.router)
app.include_router(connections.router)
app.include_router(connection_tags.router)
app.include_router(tags.router)
app.include_router(insights.router)
app.include_router(comments.router)


# Global exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions with consistent format."""
    logger.error(
        f"Application error: {exc.detail} - "
        f"Path: {request.url.path} - "
        f"User: {getattr(request.state, 'user_id', 'anonymous')}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(
        f"Unexpected error: {str(exc)} - "
        f"Path: {request.url.path}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred",
                "status_code": 500
            }
        }
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Check database connectivity."""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
        )