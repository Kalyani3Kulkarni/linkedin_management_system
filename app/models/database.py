"""
Database models and connection setup.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, 
    Float, Boolean, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from app.config.settings import settings
import sqlite3

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TrendTopic(Base):
    """Trending topics identified by the Trend Analysis Agent."""
    
    __tablename__ = "trend_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), nullable=False, index=True)
    hashtags = Column(JSON, nullable=True)  # List of related hashtags
    relevance_score = Column(Float, nullable=False, default=0.0)
    source = Column(String(100), nullable=False)  # e.g., "techcrunch", "linkedin"
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    posts = relationship("Post", back_populates="trend_topic")


class Post(Base):
    """Generated posts by the Content Creation Agent."""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    hashtags = Column(JSON, nullable=True)  # List of hashtags
    readability_score = Column(Float, nullable=True)
    character_count = Column(Integer, nullable=False)
    
    # Status tracking
    status = Column(String(50), default="draft")  # draft, scheduled, posted, failed
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    linkedin_post_id = Column(String(255), nullable=True)
    
    # Relationships
    trend_topic_id = Column(Integer, ForeignKey("trend_topics.id"), nullable=True)
    trend_topic = relationship("TrendTopic", back_populates="posts")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Engagement metrics
    engagement_metrics = relationship("EngagementMetric", back_populates="post")


class Comment(Base):
    """Comments on LinkedIn posts."""
    
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    linkedin_comment_id = Column(String(255), unique=True, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    
    # Comment content
    author_name = Column(String(255), nullable=False)
    author_linkedin_id = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    
    # Analysis
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)  # positive, negative, neutral
    
    # Response tracking
    requires_response = Column(Boolean, default=False)
    response_generated = Column(Text, nullable=True)
    response_posted = Column(Boolean, default=False)
    response_posted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    post = relationship("Post")


class EngagementMetric(Base):
    """Engagement metrics for posts."""
    
    __tablename__ = "engagement_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    
    # Metrics
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="engagement_metrics")


class NewsArticle(Base):
    """Tech news articles from RSS feeds."""
    
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False)
    
    # Analysis
    keywords = Column(JSON, nullable=True)  # Extracted keywords
    relevance_score = Column(Float, default=0.0)
    processed = Column(Boolean, default=False)
    
    # Timestamps
    fetched_at = Column(DateTime, default=datetime.utcnow)


class AgentActivity(Base):
    """Track agent activities and performance."""
    
    __tablename__ = "agent_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False)
    activity_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # success, error, pending
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    execution_time = Column(Float, nullable=True)  # in seconds
    
    # Timestamp
    executed_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with tables."""
    create_tables()