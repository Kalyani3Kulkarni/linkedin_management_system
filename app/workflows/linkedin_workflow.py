"""
LangGraph workflow for automated LinkedIn management.
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
from loguru import logger

from app.agents.trend_analysis_agent import TrendAnalysisAgent
from app.agents.content_creation_agent import ContentCreationAgent
from app.models.database import get_db, Post, TrendTopic
import sqlite3

class LinkedInWorkflowState(BaseModel):
    """State shared across all agents in the workflow."""
    
    # Input parameters
    sources: List[str] = ["techcrunch"]
    max_trends: int = 5
    max_posts_per_day: int = 3
    content_tones: List[str] = ["professional", "casual"]
    
    # Workflow data
    trends: List[Dict[str, Any]] = []
    generated_content: List[Dict[str, Any]] = []
    published_posts: List[Dict[str, Any]] = []
    
    # Status tracking
    workflow_id: str = ""
    started_at: str = ""
    current_step: str = ""
    errors: List[str] = []
    
    # Analytics
    trends_found: int = 0
    content_generated: int = 0
    posts_published: int = 0
    
    class Config:
        arbitrary_types_allowed = True


class LinkedInAutomationWorkflow:
    """Automated LinkedIn management workflow using LangGraph."""
    
    def __init__(self):
        """Initialize the workflow with agents and graph."""
        self.trend_agent = TrendAnalysisAgent()
        self.content_agent = ContentCreationAgent()
        self.logger = logger.bind(component="workflow")
        
        # Initialize checkpoint saver for state persistence
        self.checkpointer = MemorySaver()        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the state graph
        workflow = StateGraph(LinkedInWorkflowState)
        
        # Add nodes (agents)
        workflow.add_node("analyze_trends", self._analyze_trends_node)
        workflow.add_node("filter_trends", self._filter_trends_node)
        workflow.add_node("generate_content", self._generate_content_node)
        workflow.add_node("review_content", self._review_content_node)
        workflow.add_node("schedule_posts", self._schedule_posts_node)
        workflow.add_node("monitor_engagement", self._monitor_engagement_node)
        
        # Define the workflow edges
        workflow.set_entry_point("analyze_trends")
        
        workflow.add_edge("analyze_trends", "filter_trends")
        workflow.add_edge("filter_trends", "generate_content")
        workflow.add_edge("generate_content", "review_content")
        workflow.add_conditional_edges(
            "review_content",
            self._should_publish_content,
            {
                "publish": "schedule_posts",
                "regenerate": "generate_content",
                "skip": END
            }
        )
        workflow.add_edge("schedule_posts", "monitor_engagement")
        workflow.add_edge("monitor_engagement", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def _analyze_trends_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Analyze trending topics."""
        self.logger.info("🔍 Analyzing trends...")
        
        try:
            state.current_step = "analyzing_trends"
            
            # Execute trend analysis
            result = await self.trend_agent.execute(
                sources=state.sources,
                limit=state.max_trends
            )
            
            if result["success"]:
                state.trends = result["data"]["trends"]
                self.logger.info(f"Found {state.trends_found} trends")
            else:
                state.errors.append(f"Trend analysis failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            error_msg = f"Trend analysis error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    async def _filter_trends_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Filter and prioritize trends."""
        self.logger.info("🎯 Filtering trends...")
        
        try:
            state.current_step = "filtering_trends"
            
            if not state.trends:
                self.logger.warning("No trends to filter")
                return state
            
            # Sort by relevance score and take top trends
            filtered_trends = sorted(
                state.trends, 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )[:state.max_posts_per_day]
            
            # Check for recent posts on similar topics to avoid duplication
            # Skip duplicate filtering for now to test
            #filtered_trends = await self._avoid_duplicate_topics(filtered_trends)
            
            state.trends = filtered_trends
            self.logger.info(f"Filtered to {len(filtered_trends)} priority trends")
            
        except Exception as e:
            error_msg = f"Trend filtering error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    async def _generate_content_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Generate content for selected trends."""
        self.logger.info("✍️ Generating content...")
        
        try:
            state.current_step = "generating_content"
            state.generated_content = []
            
            for trend in state.trends:
                for tone in state.content_tones:
                    try:
                        # Generate content for this trend and tone
                        result = await self.content_agent.execute(
                            trend_topic_id=trend.get('id'),
                            tone=tone,
                            include_hashtags=True,
                            target_length=1500
                        )
                        
                        if result["success"]:
                            content_data = result["data"]
                            content_data["trend_info"] = trend
                            content_data["tone"] = tone
                            state.generated_content.append(content_data)
                            
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to generate content for trend {trend.get('topic', 'unknown')}: {str(e)}")
            
            self.logger.info(f"Generated {state.content_generated} content pieces")
            
        except Exception as e:
            error_msg = f"Content generation error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    async def _review_content_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Review and score generated content."""
        self.logger.info("📊 Reviewing content quality...")
        
        try:
            state.current_step = "reviewing_content"
            
            for content in state.generated_content:
                # Calculate composite score
                quality_metrics = content["post"].get("quality_metrics", {})
                
                readability_score = quality_metrics.get("readability_score", 0)
                engagement_score = quality_metrics.get("engagement_score", 0)
                trend_relevance = content["trend_info"].get("relevance_score", 0)
                
                # Composite score (weighted)
                composite_score = (
                    readability_score * 0.3 +
                    engagement_score * 100 * 0.4 +  # Convert 0-1 to 0-100
                    trend_relevance * 100 * 0.3
                )
                
                content["composite_score"] = composite_score
                content["approved"] = composite_score >= 40  # Threshold for approval
            
            # Sort by score
            state.generated_content.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
            
            approved_count = sum(1 for c in state.generated_content if c.get("approved", False))
            self.logger.info(f"Approved {approved_count}/{len(state.generated_content)} content pieces")
            
        except Exception as e:
            error_msg = f"Content review error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    async def _schedule_posts_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Schedule approved posts."""
        self.logger.info("📅 Scheduling posts...")
        
        try:
            state.current_step = "scheduling_posts"
            
            # Get approved content
            approved_content = [c for c in state.generated_content if c.get("approved", False)]
            
            # Limit to max posts per day
            posts_to_schedule = approved_content[:state.max_posts_per_day]
            
            # Schedule posts with optimal timing
            scheduled_times = self._calculate_optimal_post_times(len(posts_to_schedule))
            
            for i, content in enumerate(posts_to_schedule):
                try:
                    # Update post status to scheduled
                    db = next(get_db())
                    post_id = content["post"]["id"]
                    post = db.query(Post).filter(Post.id == post_id).first()
                    
                    if post:
                        post.status = "scheduled"
                        post.scheduled_at = scheduled_times[i]
                        db.commit()
                        
                        state.published_posts.append({
                            "post_id": post_id,
                            "scheduled_at": scheduled_times[i].isoformat(),
                            "content_preview": content["post"]["content"][:100] + "..."
                        })
                    
                    db.close()
                    
                except Exception as e:
                    self.logger.error(f"Failed to schedule post {post_id}: {str(e)}")
            
            state.posts_published = len(state.published_posts)
            self.logger.info(f"Scheduled {state.posts_published} posts")
            
        except Exception as e:
            error_msg = f"Post scheduling error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    async def _monitor_engagement_node(self, state: LinkedInWorkflowState) -> LinkedInWorkflowState:
        """Node: Monitor engagement and learn."""
        self.logger.info("📈 Setting up engagement monitoring...")
        
        try:
            state.current_step = "monitoring_engagement"
            
            # This would integrate with LinkedIn API to monitor actual engagement
            # For now, we'll set up the monitoring structure
            
            self.logger.info("Engagement monitoring configured")
            
        except Exception as e:
            error_msg = f"Engagement monitoring error: {str(e)}"
            state.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return state
    
    def _should_publish_content(self, state: LinkedInWorkflowState) -> str:
        """Conditional edge: Decide whether to publish, regenerate, or skip."""
        
        if not state.generated_content:
            return "skip"
        
        approved_count = sum(1 for c in state.generated_content if c.get("approved", False))
        
        if approved_count >= 1:
            return "publish"
        elif len(state.generated_content) < 5:  # Try regenerating if we haven't tried much
            return "regenerate"
        else:
            return "skip"
    
    async def _avoid_duplicate_topics(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out trends similar to recent posts."""
        try:
            db = next(get_db())
            
            # Get recent posts (last 7 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_posts = db.query(Post).filter(Post.created_at >= recent_cutoff).all()
            
            recent_topics = {post.trend_topic_id for post in recent_posts if post.trend_topic_id}
            
            # Filter out trends we've recently posted about
            filtered_trends = [
                trend for trend in trends 
                if trend.get('id') not in recent_topics
            ]
            
            db.close()
            return filtered_trends
            
        except Exception as e:
            self.logger.error(f"Error filtering duplicate topics: {str(e)}")
            return trends
    
    def _calculate_optimal_post_times(self, num_posts: int) -> List[datetime]:
        """Calculate optimal times to post based on LinkedIn best practices."""
        base_time = datetime.utcnow()
        
        # LinkedIn optimal posting hours: 8-10 AM, 12-2 PM, 5-6 PM (business days)
        optimal_hours = [8, 12, 17]  # 8 AM, 12 PM, 5 PM
        
        scheduled_times = []
        
        for i in range(num_posts):
            # Distribute posts across optimal hours
            hour = optimal_hours[i % len(optimal_hours)]
            
            # Schedule for today or tomorrow based on current time
            if base_time.hour >= hour:
                # Schedule for tomorrow
                schedule_time = base_time.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                # Schedule for today
                schedule_time = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Add some variation to avoid exact same times
            schedule_time += timedelta(minutes=i * 30)
            
            scheduled_times.append(schedule_time)
        
        return scheduled_times
    
    async def run_daily_automation(self) -> Dict[str, Any]:
        """Run the complete daily automation workflow."""
        
        # Initialize state
        initial_state = LinkedInWorkflowState(
            workflow_id=f"daily_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.utcnow().isoformat(),
            current_step="starting"
        )
        
        self.logger.info(f"🚀 Starting daily automation workflow: {initial_state.workflow_id}")
        
        try:
            # Run the workflow
            config = {
                "configurable": {"thread_id": initial_state.workflow_id},
                "recursion_limit": 50
            }
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            # Log results
            self.logger.info(
                f"✅ Workflow completed: {len(getattr(final_state, 'trends', []))} trends, "
                f"{len(getattr(final_state, 'generated_content', []))} content pieces, "
                f"{len(getattr(final_state, 'published_posts', []))} posts scheduled"
            )
            
            return {
                "success": True,    
                "workflow_id": getattr(final_state, 'workflow_id', 'unknown'),
                "summary": {
                    "trends_found": len(getattr(final_state, 'trends', [])),
                    "content_generated": len(getattr(final_state, 'generated_content', [])),
                    "posts_scheduled": len(getattr(final_state, 'published_posts', [])),
                    "errors": getattr(final_state, 'errors', [])
                },
                "scheduled_posts": getattr(final_state, 'published_posts', [])
            }
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "workflow_id": initial_state.workflow_id
            }