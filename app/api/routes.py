"""
API routes for LinkedIn Management System.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import (
    TrendAnalysisRequest, ContentGenerationRequest, EngagementAnalysisRequest,
    TrendTopicResponse, PostResponse, CommentResponse
)
from app.agents.trend_analysis_agent import TrendAnalysisAgent
from app.agents.content_creation_agent import ContentCreationAgent

# Create router
router = APIRouter()

# Initialize agents
trend_agent = TrendAnalysisAgent()
content_agent = ContentCreationAgent()


@router.post("/trends/analyze")
async def analyze_trends(
    request: TrendAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Analyze trending topics from specified sources."""
    try:
        result = await trend_agent.execute(
            sources=request.sources,
            limit=request.limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "data": result["data"],
            "execution_time": result["execution_time"],
            "agent": result["agent"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.get("/trends")
async def get_trends(
    limit: int = 10,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get stored trending topics."""
    from app.models.database import TrendTopic
    
    query = db.query(TrendTopic)
    
    if active_only:
        query = query.filter(TrendTopic.is_active == True)
    
    trends = query.order_by(TrendTopic.relevance_score.desc()).limit(limit).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": trend.id,
                "topic": trend.topic,
                "hashtags": trend.hashtags,
                "relevance_score": trend.relevance_score,
                "source": trend.source,
                "detected_at": trend.detected_at.isoformat(),
                "is_active": trend.is_active
            }
            for trend in trends
        ],
        "count": len(trends)
    }


@router.post("/content/generate")
async def generate_content(
    request: ContentGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate LinkedIn content based on trends or custom topics."""
    try:
        # Execute content generation
        result = await content_agent.execute(
            trend_topic_id=request.trend_topic_id,
            custom_topic=request.custom_topic,
            tone=request.tone,
            include_hashtags=request.include_hashtags
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "data": result["data"],
            "execution_time": result["execution_time"],
            "agent": result["agent"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.post("/content/generate-variants")
async def generate_content_variants(
    request: ContentGenerationRequest,
    background_tasks: BackgroundTasks,
    count: int = 3,
    db: Session = Depends(get_db)
):
    """Generate multiple content variants for A/B testing."""
    try:
        # Get topic info first
        topic_info = await content_agent._get_topic_info(
            request.trend_topic_id, 
            request.custom_topic
        )
        
        # Generate variants
        variants = await content_agent.generate_multiple_variants(topic_info, count)
        
        return {
            "status": "success",
            "data": {
                "topic_info": topic_info,
                "variants": variants,
                "count": len(variants)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant generation failed: {str(e)}")


@router.post("/engagement/analyze")
async def analyze_engagement(
    request: EngagementAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Analyze engagement on posts and comments."""
    try:
        # This would be implemented by EngagementAgent
        # For now, return a placeholder response
        return {
            "status": "success",
            "message": "Engagement Agent not yet implemented",
            "data": {
                "total_posts_analyzed": 0,
                "total_comments_analyzed": 0,
                "average_sentiment": 0.0,
                "engagement_metrics": {
                    "likes": 0,
                    "comments": 0,
                    "shares": 0
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engagement analysis failed: {str(e)}")


@router.get("/posts")
async def get_posts(
    status: str = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get posts from database."""
    from app.models.database import Post
    
    query = db.query(Post)
    
    if status:
        query = query.filter(Post.status == status)
    
    posts = query.order_by(Post.created_at.desc()).limit(limit).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": post.id,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "hashtags": post.hashtags,
                "status": post.status,
                "character_count": post.character_count,
                "readability_score": post.readability_score,
                "created_at": post.created_at.isoformat(),
                "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
                "posted_at": post.posted_at.isoformat() if post.posted_at else None
            }
            for post in posts
        ],
        "count": len(posts)
    }


@router.get("/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific post by ID."""
    from app.models.database import Post
    
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "status": "success",
        "data": {
            "id": post.id,
            "content": post.content,
            "hashtags": post.hashtags,
            "status": post.status,
            "character_count": post.character_count,
            "readability_score": post.readability_score,
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
            "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
            "posted_at": post.posted_at.isoformat() if post.posted_at else None,
            "linkedin_post_id": post.linkedin_post_id
        }
    }


@router.get("/comments")
async def get_comments(
    sentiment: str = None,
    requires_response: bool = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get comments from database."""
    from app.models.database import Comment
    
    query = db.query(Comment)
    
    if sentiment:
        query = query.filter(Comment.sentiment_label == sentiment)
    
    if requires_response is not None:
        query = query.filter(Comment.requires_response == requires_response)
    
    comments = query.order_by(Comment.received_at.desc()).limit(limit).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": comment.id,
                "author_name": comment.author_name,
                "content": comment.content[:200] + "..." if len(comment.content) > 200 else comment.content,
                "sentiment_score": comment.sentiment_score,
                "sentiment_label": comment.sentiment_label,
                "requires_response": comment.requires_response,
                "response_posted": comment.response_posted,
                "received_at": comment.received_at.isoformat()
            }
            for comment in comments
        ],
        "count": len(comments)
    }


@router.get("/agents/health")
async def check_agents_health():
    """Check health status of all agents."""
    agents_health = []
    
    # Check Trend Analysis Agent
    trend_health = await trend_agent.health_check()
    agents_health.append(trend_health)
    
    # Check Content Creation Agent
    content_health = await content_agent.health_check()
    agents_health.append(content_health)
    
    # Add other agents when implemented
    # engagement_health = await engagement_agent.health_check()
    
    all_healthy = all(agent["status"] == "healthy" for agent in agents_health)
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "agents": agents_health,
        "timestamp": agents_health[0]["timestamp"] if agents_health else None
    }


@router.get("/agents/{agent_name}/info")
async def get_agent_info(agent_name: str):
    """Get information about a specific agent."""
    agents = {
        "trend": trend_agent,
        "content": content_agent,
        # Add other agents when implemented
        # "engagement": engagement_agent
    }
    
    if agent_name not in agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    agent = agents[agent_name]
    return {
        "status": "success",
        "data": agent.get_agent_info()
    }


@router.get("/analytics/dashboard")
async def get_dashboard_data(db: Session = Depends(get_db)):
    """Get dashboard analytics data."""
    from app.models.database import TrendTopic, Post, Comment, AgentActivity
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Get counts
    total_trends = db.query(TrendTopic).count()
    active_trends = db.query(TrendTopic).filter(TrendTopic.is_active == True).count()
    total_posts = db.query(Post).count()
    draft_posts = db.query(Post).filter(Post.status == "draft").count()
    total_comments = db.query(Comment).count()
    
    # Get recent activity (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_activities = db.query(AgentActivity).filter(
        AgentActivity.executed_at >= yesterday
    ).order_by(AgentActivity.executed_at.desc()).limit(10).all()
    
    # Get top trends
    top_trends = db.query(TrendTopic).filter(
        TrendTopic.is_active == True
    ).order_by(TrendTopic.relevance_score.desc()).limit(5).all()
    
    # Get recent posts
    recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(5).all()
    
    return {
        "status": "success",
        "data": {
            "summary": {
                "total_trends": total_trends,
                "active_trends": active_trends,
                "total_posts": total_posts,
                "draft_posts": draft_posts,
                "total_comments": total_comments
            },
            "top_trends": [
                {
                    "topic": trend.topic,
                    "relevance_score": trend.relevance_score,
                    "hashtags": trend.hashtags
                }
                for trend in top_trends
            ],
            "recent_posts": [
                {
                    "id": post.id,
                    "content": post.content[:100] + "..." if len(post.content) > 100 else post.content,
                    "status": post.status,
                    "readability_score": post.readability_score,
                    "created_at": post.created_at.isoformat()
                }
                for post in recent_posts
            ],
            "recent_activities": [
                {
                    "agent": activity.agent_name,
                    "activity": activity.activity_type,
                    "status": activity.status,
                    "timestamp": activity.executed_at.isoformat()
                }
                for activity in recent_activities
            ]
        }
    }