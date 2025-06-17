"""
Configuration settings for LinkedIn Management System.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "LinkedIn Management System"
    debug: bool = False
    version: str = "1.0.0"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    
    # Database
    database_url: str = Field(
        default="sqlite:///./linkedin_management.db",
        env="DATABASE_URL"
    )
    
    # OpenAI API
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = "gpt-3.5-turbo"
    
    max_tokens: int = 4000
    temperature: float = 0.7
    
    # LinkedIn
    linkedin_client_id: Optional[str] = Field(None, env="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: Optional[str] = Field(None, env="LINKEDIN_CLIENT_SECRET")
    linkedin_access_token: Optional[str] = Field(None, env="LINKEDIN_ACCESS_TOKEN")
    linkedin_redirect_uri: Optional[str] = Field(None, env="LINKEDIN_REDIRECT_URI")
    
    # Content Settings
    max_post_length: int = 3000  # LinkedIn limit
    min_readability_score: int = 60
    max_hashtags: int = 5
    
    # RSS Feeds
    techcrunch_rss_url: str = "https://techcrunch.com/feed/"
    
    # Rate Limiting
    posts_per_day: int = 5
    comments_per_hour: int = 20
    
    # Sentiment Analysis
    positive_threshold: float = 0.1
    negative_threshold: float = -0.1
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()