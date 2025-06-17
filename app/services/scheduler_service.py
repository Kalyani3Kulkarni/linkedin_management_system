"""
Scheduler service for automated LinkedIn workflow execution.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.workflows.linkedin_workflow import LinkedInAutomationWorkflow
from app.models.database import get_db, AgentActivity
from loguru import logger

class LinkedInSchedulerService:
    """Service for scheduling and managing automated LinkedIn workflows."""
    
    def __init__(self):
        """Initialize the scheduler service."""
        self.scheduler = AsyncIOScheduler()
        self.workflow = LinkedInAutomationWorkflow()
        self.logger = logger.bind(component="scheduler")
        self.is_running = False
    
    async def start_automation(self) -> Dict[str, Any]:
        """Start the automated LinkedIn management system."""
        try:
            if self.is_running:
                return {"success": False, "message": "Automation already running"}
            
            # Schedule daily automation
            self.scheduler.add_job(
                self._run_daily_workflow,
                CronTrigger(hour=8, minute=0),  # Run daily at 8 AM
                id="daily_linkedin_automation",
                name="Daily LinkedIn Automation",
                replace_existing=True
            )
            
            # Schedule trend analysis (every 4 hours)
            self.scheduler.add_job(
                self._run_trend_analysis,
                CronTrigger(hour="8,12,16,20", minute=0),
                id="hourly_trend_analysis",
                name="Trend Analysis",
                replace_existing=True
            )
            
            # Schedule engagement monitoring (every hour)
            self.scheduler.add_job(
                self._monitor_engagement,
                CronTrigger(minute=0),  # Every hour
                id="engagement_monitoring",
                name="Engagement Monitoring",
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            self.logger.info("🚀 LinkedIn automation started successfully")
            
            return {
                "success": True,
                "message": "LinkedIn automation started",
                "scheduled_jobs": [
                    {
                        "name": "Daily Automation",
                        "schedule": "Daily at 8:00 AM",
                        "next_run": "Tomorrow 8:00 AM"
                    },
                    {
                        "name": "Trend Analysis", 
                        "schedule": "Every 4 hours",
                        "next_run": "Next scheduled time"
                    },
                    {
                        "name": "Engagement Monitoring",
                        "schedule": "Every hour",
                        "next_run": "Top of next hour"
                    }
                ]
            }
            
        except Exception as e:
            error_msg = f"Failed to start automation: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def stop_automation(self) -> Dict[str, Any]:
        """Stop the automated LinkedIn management system."""
        try:
            if not self.is_running:
                return {"success": False, "message": "Automation not running"}
            
            self.scheduler.shutdown()
            self.is_running = False
            
            self.logger.info("🛑 LinkedIn automation stopped")
            
            return {
                "success": True,
                "message": "LinkedIn automation stopped"
            }
            
        except Exception as e:
            error_msg = f"Failed to stop automation: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def run_workflow_now(self) -> Dict[str, Any]:
        """Run the complete workflow immediately."""
        try:
            self.logger.info("🚀 Running LinkedIn workflow on demand")
            
            result = await self.workflow.run_daily_automation()
            
            # Log the execution
            await self._log_workflow_execution(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to run workflow: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def _run_daily_workflow(self):
        """Scheduled job: Run the complete daily workflow."""
        try:
            self.logger.info("📅 Running scheduled daily LinkedIn automation")
            
            result = await self.workflow.run_daily_automation()
            
            # Log the execution
            await self._log_workflow_execution(result)
            
            if result["success"]:
                self.logger.info(
                    f"✅ Daily automation completed: "
                    f"{result['summary']['posts_scheduled']} posts scheduled"
                )
            else:
                self.logger.error(f"❌ Daily automation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Daily workflow execution failed: {str(e)}")
    
    async def _run_trend_analysis(self):
        """Scheduled job: Run trend analysis only."""
        try:
            self.logger.info("🔍 Running scheduled trend analysis")
            
            from app.agents.trend_analysis_agent import TrendAnalysisAgent
            
            trend_agent = TrendAnalysisAgent()
            result = await trend_agent.execute(sources=["techcrunch"], limit=10)
            
            if result["success"]:
                trends_found = len(result["data"]["trends"])
                self.logger.info(f"Found {trends_found} new trends")
            else:
                self.logger.error(f"Trend analysis failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Trend analysis execution failed: {str(e)}")
    
    async def _monitor_engagement(self):
        """Scheduled job: Monitor engagement on recent posts."""
        try:
            # This would integrate with LinkedIn API to check engagement
            # For now, just log that monitoring is active
            self.logger.debug("📊 Monitoring post engagement")
            
            # TODO: Implement actual engagement monitoring
            # - Fetch recent posts from LinkedIn API
            # - Update engagement metrics in database
            # - Trigger responses if needed
            
        except Exception as e:
            self.logger.error(f"Engagement monitoring failed: {str(e)}")
    
    async def _log_workflow_execution(self, result: Dict[str, Any]):
        """Log workflow execution to database."""
        try:
            db = next(get_db())
            
            activity = AgentActivity(
                agent_name="LinkedInWorkflow",
                activity_type="daily_automation",
                status="success" if result["success"] else "error",
                details=result.get("summary", {}),
                error_message=result.get("error"),
                execution_time=None  # TODO: Track execution time
            )
            
            db.add(activity)
            db.commit()
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log workflow execution: {str(e)}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and job information."""
        try:
            if not self.is_running:
                return {
                    "status": "stopped",
                    "jobs": [],
                    "message": "Scheduler is not running"
                }
            
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            
            return {
                "status": "running",
                "jobs": jobs,
                "scheduler_info": {
                    "state": str(self.scheduler.state),
                    "timezone": str(self.scheduler.timezone)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def schedule_custom_workflow(
        self, 
        sources: list = None, 
        max_posts: int = 3,
        content_tones: list = None,
        schedule_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Schedule a custom workflow with specific parameters."""
        try:
            # Set defaults
            sources = sources or ["techcrunch"]
            content_tones = content_tones or ["professional"]
            schedule_time = schedule_time or (datetime.utcnow() + timedelta(minutes=5))
            
            # Create job ID
            job_id = f"custom_workflow_{schedule_time.strftime('%Y%m%d_%H%M%S')}"
            
            # Schedule the custom workflow
            self.scheduler.add_job(
                self._run_custom_workflow,
                "date",
                run_date=schedule_time,
                args=[sources, max_posts, content_tones],
                id=job_id,
                name=f"Custom Workflow - {schedule_time.strftime('%Y-%m-%d %H:%M')}"
            )
            
            self.logger.info(f"Scheduled custom workflow for {schedule_time}")
            
            return {
                "success": True,
                "job_id": job_id,
                "scheduled_time": schedule_time.isoformat(),
                "parameters": {
                    "sources": sources,
                    "max_posts": max_posts,
                    "content_tones": content_tones
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to schedule custom workflow: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def _run_custom_workflow(self, sources: list, max_posts: int, content_tones: list):
        """Run a custom workflow with specific parameters."""
        try:
            self.logger.info(f"Running custom workflow with {sources}, {max_posts} posts, {content_tones} tones")
            
            # Create custom state
            from app.workflows.linkedin_workflow import LinkedInWorkflowState
            
            custom_state = LinkedInWorkflowState(
                sources=sources,
                max_posts_per_day=max_posts,
                content_tones=content_tones,
                workflow_id=f"custom_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Run the workflow
            config = {"configurable": {"thread_id": custom_state.workflow_id}}
            result = await self.workflow.workflow.ainvoke(custom_state, config=config)
            
            self.logger.info(f"Custom workflow completed: {result.posts_published} posts scheduled")
            
        except Exception as e:
            self.logger.error(f"Custom workflow execution failed: {str(e)}")


# Global scheduler instance
linkedin_scheduler = LinkedInSchedulerService()