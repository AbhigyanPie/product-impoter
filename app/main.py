"""
Product Importer API
--------------------
FastAPI application for importing products from CSV files.

Features:
- CSV upload with real-time progress tracking
- Product CRUD with filtering and pagination
- Webhook configuration and management
- Bulk operations with confirmation

Supports both:
- Local development (SQLite + in-memory progress)
- Production (PostgreSQL + Redis/Celery)
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.config import get_settings
from app.routers import products, uploads, webhooks

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - creates tables on startup."""
    # Create database tables
    print(f"\n{'='*50}")
    print(f"  {settings.app_name}")
    print(f"{'='*50}")
    print(f"  Database: {'SQLite (local)' if settings.is_sqlite else 'PostgreSQL'}")
    
    Base.metadata.create_all(bind=engine)
    print(f"  Tables: Created/Verified ✓")
    print(f"{'='*50}\n")
    
    yield
    # Cleanup on shutdown (if needed)


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Import products from CSV files into a SQL database",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(products.router)
app.include_router(uploads.router)
app.include_router(webhooks.router)


@app.get("/")
async def home(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }


# For running with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)