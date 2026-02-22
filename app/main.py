"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.auth import routes as auth_routes
from app.voting import routes as voting_routes
from app.admin import routes as admin_routes

# Create FastAPI app
app = FastAPI(
    title="Blockchain Voting System",
    description="A secure, tamper-resistant blockchain-based voting system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


# Include routers
app.include_router(auth_routes.router)
app.include_router(voting_routes.router)
app.include_router(admin_routes.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Blockchain Voting System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


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
