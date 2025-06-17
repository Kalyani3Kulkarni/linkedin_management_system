"""
Pydantic schemas for request/response models.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class TrendTopicBase(BaseModel):
    """Base schema for trend topics."""
    topic: str = Field(..., min_length=1, max_length=255)
    hashtags: Optional[List[str]] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(..., min_length=1, max_length=100)


class TrendTopicCreate(TrendTopicBase):
    """Schema for creating trend topics."""
    pass


class TrendTopicResponse(TrendTopicBase):
    """Schema for trend topic responses."""
    id: int
    detected_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class PostBase(BaseModel):
    """Base schema for posts."""
    content: str = Field(..., min_length=1, max_length=3000)
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    
    @validator('hashtags')
    def validate_hashtags(cls, v):
        if v and len(v) > 5:
            raise ValueError('Maximum 5 hashtags allowed')
        return v


class PostCreate(PostBase):
    """Schema for creating posts."""
    trend_topic_id: Optional[int] = None


class PostResponse(PostBase):
    """Schema for post responses."""
    id: int
    character_count: int
    readability_score: Optional[float]
    status: str
    posted_at: Optional[datetime]
    linkedin_post_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    """Base schema for comments."""
    author_name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    author_linkedin_id: Optional[str] = None


class CommentCreate(CommentBase):
    """Schema for creating comments."""
    linkedin_comment_id: str = Field(..., min_length=1, max_length=255)
    post_id: Optional[int] = None


class CommentResponse(CommentBase):
    """Schema for comment responses."""
    id: int
    linkedin_comment_id: str
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    requires_response: bool
    response_generated: Optional[str]
    response_posted: bool
    received_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EngagementMetricCreate(BaseModel):
    """Schema for creating engagement metrics."""
    post_id: int
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0


class EngagementMetricResponse(EngagementMetricCreate):
    """Schema for engagement metric responses."""
    id: int
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class NewsArticleBase(BaseModel):
    """Base schema for news articles."""
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1, max_length=1000)
    summary: Optional[str] = None
    author: Optional[str] = None
    source: str = Field(..., min_length=1, max_length=100)
    published_at: datetime


class NewsArticleCreate(NewsArticleBase):
    """Schema for creating news articles."""
    keywords: Optional[List[str]] = None
    relevance_score: float = 0.0


class NewsArticleResponse(NewsArticleBase):
    """Schema for news article responses."""
    id: int
    keywords: Optional[List[str]]
    relevance_score: float
    processed: bool
    fetched_at: datetime
    
    class Config:
        from_attributes = True


class AgentActivityCreate(BaseModel):
    """Schema for creating agent activities."""
    agent_name: str = Field(..., min_length=1, max_length=100)
    activity_type: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(success|error|pending)$")
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


class AgentActivityResponse(AgentActivityCreate):
    """Schema for agent activity responses."""
    id: int
    executed_at: datetime
    
    class Config:
        from_attributes = True


class TrendAnalysisRequest(BaseModel):
    """Request schema for trend analysis."""
    sources: List[str] = Field(default=["techcrunch"], description="Sources to analyze")
    limit: int = Field(default=10, ge=1, le=50, description="Number of trends to return")


class ContentGenerationRequest(BaseModel):
    """Request schema for content generation."""
    trend_topic_id: Optional[int] = None
    custom_topic: Optional[str] = None
    tone: str = Field(default="professional", pattern="^(professional|casual|technical)$")
    include_hashtags: bool = True
    
    @validator('custom_topic')
    def validate_topic_input(cls, v, values):
        if not v and not values.get('trend_topic_id'):
            raise ValueError('Either trend_topic_id or custom_topic must be provided')
        return v


class EngagementAnalysisRequest(BaseModel):
    """Request schema for engagement analysis."""
    post_ids: Optional[List[int]] = None
    hours_back: int = Field(default=24, ge=1, le=168, description="Hours to look back")
    analyze_sentiment: bool = True