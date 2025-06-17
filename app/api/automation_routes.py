"""
API routes for LinkedIn automation and workflow management.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.scheduler_service import linkedin_scheduler
from loguru import logger

# Pydantic models for requests
class AutomationConfigRequest(BaseModel):
    """Request model for automation configuration."""
    sources: List[str] = ["techcrunch"]
    max_posts_per_day: int = 3
    content_tones: List[str] = ["professional", "casual"]
    auto_start: bool = True


class CustomWorkflowRequest(BaseModel):
    """Request model for custom workflow scheduling."""
    sources: List[str] = ["techcrunch"]
    max_posts: int = 3
    content_tones: List[str] = ["professional"]
    schedule_in_minutes: Optional[int] = 5  # Schedule X minutes from now


# Create router
automation_router = APIRouter(prefix="/automation", tags=["automation"])


@automation_router.post("/run-now")
async def run_workflow_now(background_tasks: BackgroundTasks):
    """Run the complete LinkedIn workflow immediately."""
    try:
        # Run in background to avoid timeout
        background_tasks.add_task(linkedin_scheduler.run_workflow_now)
        
        return {
            "status": "success",
            "message": "LinkedIn workflow started - running in background",
            "estimated_duration": "2-5 minutes"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@automation_router.post("/schedule-custom")
async def schedule_custom_workflow(request: CustomWorkflowRequest):
    """Schedule a custom workflow with specific parameters."""
    try:
        # Calculate schedule time
        schedule_time = datetime.utcnow() + timedelta(minutes=request.schedule_in_minutes)
        
        result = await linkedin_scheduler.schedule_custom_workflow(
            sources=request.sources,
            max_posts=request.max_posts,
            content_tones=request.content_tones,
            schedule_time=schedule_time
        )
        
        if result["success"]:
            return {
                "status": "success",
                "message": f"Custom workflow scheduled for {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to schedule workflow"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom workflow scheduling failed: {str(e)}")


@automation_router.get("/status")
async def get_automation_status():
    """Get current automation status and scheduled jobs."""
    try:
        status = linkedin_scheduler.get_scheduler_status()
        
        return {
            "status": "success",
            "data": {
                "automation_status": status["status"],
                "is_running": status["status"] == "running",
                "scheduled_jobs": status.get("jobs", []),
                "scheduler_info": status.get("scheduler_info", {})
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get automation status: {str(e)}")


@automation_router.get("/workflow-history")
async def get_workflow_history(limit: int = 10):
    """Get recent workflow execution history."""
    try:
        from app.models.database import get_db, AgentActivity
        from datetime import datetime, timedelta
        
        db = next(get_db())
        
        # Get recent workflow activities
        recent_activities = db.query(AgentActivity).filter(
            AgentActivity.agent_name == "LinkedInWorkflow",
            AgentActivity.executed_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(AgentActivity.executed_at.desc()).limit(limit).all()
        
        history = []
        for activity in recent_activities:
            history.append({
                "id": activity.id,
                "workflow_type": activity.activity_type,
                "status": activity.status,
                "executed_at": activity.executed_at.isoformat(),
                "execution_time": activity.execution_time,
                "summary": activity.details,
                "error": activity.error_message
            })
        
        db.close()
        
        return {
            "status": "success",
            "data": {
                "workflow_history": history,
                "total_executions": len(history)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow history: {str(e)}")


@automation_router.get("/metrics")
async def get_automation_metrics():
    """Get automation performance metrics."""
    try:
        from app.models.database import get_db, TrendTopic, Post, AgentActivity
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        db = next(get_db())
        
        # Calculate metrics for last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Trends analyzed
        trends_count = db.query(TrendTopic).filter(
            TrendTopic.detected_at >= week_ago
        ).count()
        
        # Content generated
        posts_count = db.query(Post).filter(
            Post.created_at >= week_ago
        ).count()
        
        # Successful workflows
        successful_workflows = db.query(AgentActivity).filter(
            AgentActivity.agent_name == "LinkedInWorkflow",
            AgentActivity.status == "success",
            AgentActivity.executed_at >= week_ago
        ).count()
        
        # Average content quality
        avg_readability = db.query(func.avg(Post.readability_score)).filter(
            Post.created_at >= week_ago,
            Post.readability_score.isnot(None)
        ).scalar() or 0
        
        # Posts by status
        posts_by_status = db.query(
            Post.status, func.count(Post.id)
        ).filter(
            Post.created_at >= week_ago
        ).group_by(Post.status).all()
        
        status_breakdown = {status: count for status, count in posts_by_status}
        
        db.close()
        
        return {
            "status": "success",
            "data": {
                "period": "Last 7 days",
                "metrics": {
                    "trends_analyzed": trends_count,
                    "content_pieces_generated": posts_count,
                    "successful_workflows": successful_workflows,
                    "average_readability_score": round(avg_readability, 2),
                    "posts_by_status": status_breakdown
                },
                "efficiency": {
                    "content_per_trend": round(posts_count / max(trends_count, 1), 2),
                    "workflow_success_rate": f"{(successful_workflows / max(successful_workflows + 1, 1)) * 100:.1f}%"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get automation metrics: {str(e)}")


@automation_router.post("/configure")
async def configure_automation(config: AutomationConfigRequest):
    """Configure automation parameters."""
    try:
        # Store configuration (in a real app, this would persist to database)
        configuration = {
            "sources": config.sources,
            "max_posts_per_day": config.max_posts_per_day,
            "content_tones": config.content_tones,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # TODO: Persist configuration to database
        # TODO: Update scheduler jobs with new configuration
        
        return {
            "status": "success",
            "message": "Automation configuration updated",
            "data": {
                "configuration": configuration,
                "restart_required": True  # Indicates automation needs restart to apply changes
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")


@automation_router.delete("/jobs/{job_id}")
async def cancel_scheduled_job(job_id: str):
    """Cancel a specific scheduled job."""
    try:
        scheduler = linkedin_scheduler.scheduler
        
        # Check if job exists
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        
        # Remove the job
        scheduler.remove_job(job_id)
        
        return {
            "status": "success",
            "message": f"Job '{job_id}' cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@automation_router.get("/preview-workflow")
async def preview_workflow_plan(
    sources: List[str] = ["techcrunch"],
    max_posts: int = 3
):
    """Preview what a workflow would do without executing it."""
    try:
        from app.agents.trend_analysis_agent import TrendAnalysisAgent
        
        # Get current trends to preview
        trend_agent = TrendAnalysisAgent()
        result = await trend_agent.execute(sources=sources, limit=max_posts * 2)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch trends for preview")
        
        trends = result["data"]["trends"][:max_posts]
        
        preview = {
            "workflow_steps": [
                "1. Analyze trends from sources",
                "2. Filter and prioritize trends", 
                "3. Generate content for top trends",
                "4. Review content quality",
                "5. Schedule approved posts",
                "6. Monitor engagement"
            ],
            "estimated_execution_time": "3-5 minutes",
            "sources_to_analyze": sources,
            "trends_found": len(result["data"]["trends"]),
            "top_trends_for_content": [
                {
                    "topic": trend["topic"],
                    "relevance_score": trend["relevance_score"],
                    "hashtags": trend["hashtags"][:3]  # Show first 3 hashtags
                }
                for trend in trends
            ],
            "estimated_posts": len(trends),
            "content_tones": ["professional", "casual"]
        }
        
        return {
            "status": "success",
            "data": preview
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@automation_router.post("/test-workflow")
async def test_workflow_component(
    component: str,
    background_tasks: BackgroundTasks
):
    """Test individual workflow components."""
    try:
        valid_components = ["trends", "content", "scheduling"]
        
        if component not in valid_components:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid component. Must be one of: {valid_components}"
            )
        
        # Run component test in background
        if component == "trends":
            background_tasks.add_task(_test_trend_analysis)
        elif component == "content":
            background_tasks.add_task(_test_content_generation)
        elif component == "scheduling":
            background_tasks.add_task(_test_scheduling)
        
        return {
            "status": "success",
            "message": f"Testing {component} component - running in background",
            "component": component
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Component test failed: {str(e)}")


# Helper functions for testing
async def _test_trend_analysis():
    """Test trend analysis component."""
    try:
        from app.agents.trend_analysis_agent import TrendAnalysisAgent
        
        agent = TrendAnalysisAgent()
        result = await agent.execute(sources=["techcrunch"], limit=3)
        
        logger.info(f"Trend analysis test: {'SUCCESS' if result['success'] else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Trend analysis test failed: {str(e)}")


async def _test_content_generation():
    """Test content generation component."""
    try:
        from app.agents.content_creation_agent import ContentCreationAgent
        
        agent = ContentCreationAgent()
        result = await agent.execute(
            custom_topic="AI automation in business",
            tone="professional",
            include_hashtags=True
        )
        
        logger.info(f"Content generation test: {'SUCCESS' if result['success'] else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Content generation test failed: {str(e)}")


async def _test_scheduling():
    """Test scheduling component."""
    try:
        # Test scheduler status
        status = linkedin_scheduler.get_scheduler_status()
        success = status["status"] in ["running", "stopped"]
        
        logger.info(f"Scheduling test: {'SUCCESS' if success else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Scheduling test failed: {str(e)}")
        
@automation_router.post("/start")
async def start_automation(
    config: AutomationConfigRequest = AutomationConfigRequest(),
    background_tasks: BackgroundTasks = None
):
    """Start the automated LinkedIn management system."""
    try:
        result = await linkedin_scheduler.start_automation()
        
        if result["success"]:
            return {
                "status": "success",
                "message": "LinkedIn automation started successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to start automation"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation start failed: {str(e)}")


@automation_router.post("/stop")
async def stop_automation():
    """Stop the automated LinkedIn management system."""
    try:
        result = await linkedin_scheduler.stop_automation()
        
        if result["success"]:
            return {
                "status": "success",
                "message": "LinkedIn automation stopped successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to stop automation"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation stop failed: {str(e)}")