"""
Health check endpoints.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Airbnb Property Operations Manager API"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information."""
    import os
    from database.db import engine
    
    # Check database connection
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Airbnb Property Operations Manager API",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

