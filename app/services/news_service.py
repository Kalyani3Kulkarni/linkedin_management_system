"""
News service for fetching and processing RSS feeds.
"""
import feedparser
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger

from app.config.settings import settings


class NewsService:
    """Service for fetching news from RSS feeds."""
    
    def __init__(self):
        """Initialize the news service."""
        self.logger = logger.bind(service="news")
        self.techcrunch_url = settings.techcrunch_rss_url
    
    async def fetch_techcrunch_articles(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Fetch recent articles from TechCrunch RSS feed.
        
        Args:
            hours_back: Hours to look back for articles
            
        Returns:
            List of article dictionaries
        """
        try:
            self.logger.info(f"Fetching TechCrunch articles from last {hours_back} hours")
            
            # Run RSS parsing in thread pool since feedparser is synchronous
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, self.techcrunch_url)
            
            if feed.bozo:
                self.logger.warning("RSS feed parsing had issues", error=feed.bozo_exception)
            
            articles = []
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    published_at = self._parse_date(entry.get('published', ''))
                    
                    if published_at and published_at > cutoff_time:
                        article = {
                            'title': entry.get('title', '').strip(),
                            'url': entry.get('link', ''),
                            'summary': entry.get('summary', '').strip(),
                            'author': entry.get('author', ''),
                            'published_at': published_at,
                            'source': 'techcrunch',
                            'tags': [tag.term for tag in entry.get('tags', [])]
                        }
                        
                        # Filter for tech-relevant content
                        if self._is_tech_relevant(article):
                            articles.append(article)
                
                except Exception as e:
                    self.logger.error(f"Error processing RSS entry: {str(e)}")
            
            self.logger.info(f"Fetched {len(articles)} relevant TechCrunch articles")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to fetch TechCrunch articles: {str(e)}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string from RSS feed.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed datetime object or None
        """
        if not date_str:
            return None
        
        try:
            # Try common RSS date formats
            import email.utils
            timestamp = email.utils.parsedate_to_datetime(date_str)
            return timestamp.replace(tzinfo=None)  # Convert to naive datetime
            
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return None
    
    def _is_tech_relevant(self, article: Dict[str, Any]) -> bool:
        """Check if article is relevant for tech professionals.
        
        Args:
            article: Article dictionary
            
        Returns:
            True if article is tech-relevant
        """
        tech_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'startup', 'funding',
            'software', 'technology', 'tech', 'programming', 'developer', 'cloud',
            'cybersecurity', 'blockchain', 'cryptocurrency', 'fintech', 'saas',
            'api', 'mobile', 'app', 'platform', 'innovation', 'digital', 'automation',
            'robotics', 'iot', 'internet of things', 'big data', 'analytics',
            'venture capital', 'ipo', 'acquisition', 'merger', 'enterprise'
        ]
        
        # Combine title, summary, and tags for relevance check
        content = f"{article.get('title', '')} {article.get('summary', '')}"
        tags = ' '.join(article.get('tags', []))
        full_content = f"{content} {tags}".lower()
        
        # Check if any tech keywords are present
        return any(keyword in full_content for keyword in tech_keywords)
    
    async def get_trending_hashtags(self, articles: List[Dict[str, Any]]) -> List[str]:
        """Extract trending hashtags from articles.
        
        Args:
            articles: List of articles
            
        Returns:
            List of trending hashtags
        """
        hashtag_counts = {}
        
        for article in articles:
            tags = article.get('tags', [])
            
            for tag in tags:
                # Clean and format as hashtag
                hashtag = tag.lower().replace(' ', '').replace('-', '')
                
                if len(hashtag) > 2 and hashtag.isalnum():
                    hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
        
        # Sort by frequency and return top hashtags
        sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
        return [hashtag for hashtag, count in sorted_hashtags[:10]]