"""
Main FastAPI application.

This is the entry point for the API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from database.db import init_db
from api.routes import health, agents, telegram, bookings, properties, logs, n8n, metrics

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Airbnb Property Operations Manager API",
    description="Multi-agent system for managing Airbnb property operations",
    version="1.0.0"
)

# CORS configuration
# Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when server starts."""
    init_db()
    print("Database initialized")

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(telegram.router, prefix="/api", tags=["telegram"])
app.include_router(bookings.router, prefix="/api", tags=["bookings"])
app.include_router(properties.router, prefix="/api", tags=["properties"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(n8n.router, prefix="/api", tags=["n8n"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Airbnb Property Operations Manager API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "localhost")
    port = int(os.getenv("API_PORT", 8000))
    
    uvicorn.run(app, host=host, port=port)

