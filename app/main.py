"""
Main FastAPI application for LinkedIn Management System.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.api.ui_routes import ui_router
from contextlib import asynccontextmanager
from loguru import logger

from app.config.settings import settings
from app.models.database import init_db
from app.api.routes import router
from app.api.automation_routes import automation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting LinkedIn Management System")
    init_db()
    logger.info("📊 Database initialized")
    
    # Initialize workflow checkpoints database
    try:
        import sqlite3
        conn = sqlite3.connect("workflow_checkpoints.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT PRIMARY KEY,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint BLOB,
                metadata BLOB,
                UNIQUE(thread_id, checkpoint_ns, checkpoint_id)
            )
        """)
        conn.commit()
        conn.close()
        logger.info("🔄 Workflow checkpoint database initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize checkpoint database: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down LinkedIn Management System")
    
    # Stop scheduler if running
    try:
        from app.services.scheduler_service import linkedin_scheduler
        if linkedin_scheduler.is_running:
            await linkedin_scheduler.stop_automation()
            logger.info("📅 Scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="""
    AI-powered LinkedIn management system with automated content creation and engagement.
    
    ## Features
    
    * **🔍 Trend Analysis**: Automatically analyzes TechCrunch and other sources for trending topics
    * **✍️ Content Creation**: Generates engaging LinkedIn posts using OpenAI
    * **🤖 Automation**: Complete workflow automation with LangGraph
    * **📅 Scheduling**: Smart post scheduling and timing optimization
    * **📊 Analytics**: Performance tracking and engagement monitoring
    
    ## Automation Workflow
    
    The system runs automated workflows that:
    1. Analyze trending topics from news sources
    2. Filter and prioritize relevant trends
    3. Generate professional content in multiple tones
    4. Review content quality and engagement potential
    5. Schedule posts at optimal times
    6. Monitor engagement and performance
    
    ## Getting Started
    
    1. Use `/automation/start` to begin automated posting
    2. Check `/automation/status` to monitor the system
    3. View `/analytics/dashboard` for performance insights
    4. Use `/automation/run-now` for immediate workflow execution
    """,
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")
app.include_router(automation_router, prefix="/api/v1")
app.include_router(ui_router)

@app.get("/")
async def root():
    """Root endpoint with system overview."""
    return {
        "message": "LinkedIn Management System API",
        "version": settings.version,
        "status": "running",
        "features": [
            "🔍 Automated trend analysis",
            "✍️ AI-powered content generation", 
            "📅 Smart post scheduling",
            "📊 Performance analytics",
            "🤖 Complete workflow automation"
        ],
        "quick_start": {
            "1": "POST /api/v1/automation/start - Start automation",
            "2": "GET /api/v1/automation/status - Check status", 
            "3": "GET /api/v1/analytics/dashboard - View metrics",
            "4": "GET /docs - Interactive API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        from app.models.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check scheduler status
    try:
        from app.services.scheduler_service import linkedin_scheduler
        scheduler_status = linkedin_scheduler.get_scheduler_status()["status"]
    except Exception as e:
        scheduler_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "components": {
            "database": db_status,
            "scheduler": scheduler_status,
            "api": "healthy"
        },
        "timestamp": "2025-06-14T00:00:00Z"
    }


@app.get("/system-info")
async def get_system_info():
    """Get comprehensive system information."""
    try:
        from app.models.database import get_db, TrendTopic, Post, AgentActivity
        from app.services.scheduler_service import linkedin_scheduler
        from datetime import datetime, timedelta
        
        # Database stats
        db = next(get_db())
        
        total_trends = db.query(TrendTopic).count()
        total_posts = db.query(Post).count()
        recent_activities = db.query(AgentActivity).filter(
            AgentActivity.executed_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        db.close()
        
        # Scheduler info
        scheduler_info = linkedin_scheduler.get_scheduler_status()
        
        return {
            "system": {
                "name": settings.app_name,
                "version": settings.version,
                "uptime": "System running",
                "environment": "development" if settings.debug else "production"
            },
            "database": {
                "total_trends": total_trends,
                "total_posts": total_posts,
                "recent_activities_24h": recent_activities
            },
            "automation": {
                "status": scheduler_info["status"],
                "scheduled_jobs": len(scheduler_info.get("jobs", [])),
                "automation_enabled": scheduler_info["status"] == "running"
            },
            "features": {
                "trend_analysis": "✅ Active",
                "content_generation": "✅ Active", 
                "workflow_automation": "✅ Active",
                "engagement_monitoring": "🚧 In Development",
                "linkedin_posting": "🚧 In Development"
            }
        }
        
    except Exception as e:
        return {
            "system": {
                "name": settings.app_name,
                "version": settings.version,
                "status": "partial",
                "error": str(e)
            }
        }