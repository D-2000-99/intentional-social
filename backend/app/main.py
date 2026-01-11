import logging
import sys
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import auth, posts, feed, connections, tags, connection_tags, insights, comments
from app.config import settings

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

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}"
    )
    
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        f"Request completed: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {duration:.2f}s"
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
app.include_router(connections.router)
app.include_router(connection_tags.router)
app.include_router(tags.router)
app.include_router(insights.router)
app.include_router(comments.router)


@app.get("/health")
def health():
    return {"status": "ok"}