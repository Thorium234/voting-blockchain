"""FastAPI application entry point with enterprise security."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import time

from app.database import init_db
from app.auth import routes as auth_routes
from app.voting import routes as voting_routes
from app.admin import routes as admin_routes
from app.admin import superadmin_routes
from app.admin import command_center
from app.aspirant import routes as aspirant_routes
from app.config import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Blockchain Voting System",
    description="A secure, tamper-resistant blockchain-based voting system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HSTS (Strict Transport Security)
        if settings.ENABLE_HSTS:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE_SECONDS}; includeSubDomains"
            )
        
        # X-Frame-Options (prevent clickjacking)
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options (prevent MIME sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        if settings.ENABLE_CSP:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        
        # Remove server identification
        response.headers["Server"] = "VotingSystem"
        
        return response


# Request ID Middleware for tracing
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to each request for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


# Rate Limit Headers Middleware
class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Add rate limit info to response headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers if available
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)
        
        return response


# Add middleware (order matters - last added is executed first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitHeadersMiddleware)


# Configure CORS with explicit origins
def get_allowed_origins():
    """Get allowed CORS origins from settings."""
    origins = settings.ALLOWED_ORIGINS
    if not origins or "localhost" in str(origins):
        # Default development origins
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ]
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Client-Version"],
    max_age=600,  # Cache preflight for 10 minutes
)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


# Include routers
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(voting_routes.router, prefix="/api/v1")
app.include_router(admin_routes.router, prefix="/api/v1")
app.include_router(superadmin_routes.router, prefix="/api/v1")
app.include_router(command_center.router, prefix="/api/v1")
app.include_router(aspirant_routes.router, prefix="/api/v1")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Blockchain Voting System API",
        "version": "1.0.0",
        "docs": "/docs",
        "security": "Zero-trust authentication enabled"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    from app.blockchain.chain import Blockchain
    from app.database import get_db
    from app.models import Block as BlockModel
    
    db = next(get_db())
    blocks_count = db.query(BlockModel).count()
    
    # Quick chain validation
    blockchain = Blockchain()
    is_valid, _ = blockchain.is_chain_valid()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "blockchain_height": blocks_count,
        "chain_valid": is_valid,
        "timestamp": time.time()
    }


@app.get("/health/detailed")
def detailed_health_check():
    """Detailed health check with component status."""
    from app.database import get_db
    from app.models import Block as BlockModel, User, Vote
    import sqlite3
    
    db = next(get_db())
    
    # Database check
    db_status = "ok"
    try:
        db.query(User).count()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Blockchain check
    chain_status = "ok"
    blocks_count = 0
    try:
        blocks_count = db.query(BlockModel).count()
    except Exception as e:
        chain_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "ok" and chain_status == "ok" else "degraded",
        "components": {
            "database": db_status,
            "blockchain": chain_status
        },
        "metrics": {
            "total_blocks": blocks_count,
            "timestamp": time.time()
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Don't expose internal errors
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
