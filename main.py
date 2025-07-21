import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from config.settings import settings
from config.database import init_db, close_db
from models.ml_models import ModelFactory
from api.auth import router as auth_router
# Import other routers as they are implemented
# from api.survey import router as survey_router
# from api.questions import router as questions_router
# from api.audio import router as audio_router
# from api.results import router as results_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up OPIC Automatic Grader...")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Load ML models
        await asyncio.to_thread(ModelFactory.load_all_models)
        logger.info("ML models loaded")
        
        # Create upload directory if it doesn't exist
        import os
        os.makedirs(settings.upload_folder, exist_ok=True)
        logger.info(f"Upload folder created: {settings.upload_folder}")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down...")
        
        # Clean up ML models
        ModelFactory.cleanup()
        logger.info("ML models cleaned up")
        
        # Close database connections
        close_db()
        logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="OPIC Automatic Grader",
    description="AI-powered English speaking assessment system",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth_router, prefix=settings.api_prefix)
# app.include_router(survey_router, prefix=settings.api_prefix)
# app.include_router(questions_router, prefix=settings.api_prefix)
# app.include_router(audio_router, prefix=settings.api_prefix)
# app.include_router(results_router, prefix=settings.api_prefix)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "OPIC Automatic Grader",
        "version": "2.0.0"
    }


# Root endpoint - serve login page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main login page"""
    try:
        with open("templates/login.html", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>OPIC Automatic Grader</h1><p>Login page not found. Please check templates directory.</p>",
            status_code=200
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """Handle 404 errors"""
    return {"error": "Not found", "detail": "The requested resource was not found"}


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(exc)}")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )