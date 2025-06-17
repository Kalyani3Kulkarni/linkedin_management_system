"""
Trend Analysis Agent for identifying trending topics and hashtags.
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.models.database import TrendTopic, NewsArticle, get_db
from app.services.llm_service import LLMService
from app.services.news_service import NewsService


class TrendAnalysisAgent(BaseAgent):
    """Agent responsible for identifying trending topics and hashtags from various sources."""
    
    def __init__(self):
        """Initialize the Trend Analysis Agent."""
        super().__init__("TrendAnalysisAgent")
        self.llm_service = LLMService()
        self.news_service = NewsService()
    
    def _validate_input(self, **kwargs) -> None:
        """Validate input parameters for trend analysis.
        
        Args:
            **kwargs: Parameters to validate
            
        Raises:
            ValueError: If validation fails
        """
        sources = kwargs.get('sources', ['techcrunch'])
        limit = kwargs.get('limit', 10)
        
        if not isinstance(sources, list) or not sources:
            raise ValueError("Sources must be a non-empty list")
        
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("Limit must be an integer between 1 and 50")
    
    async def _execute_logic(self, **kwargs) -> Dict[str, Any]:
        """Execute trend analysis logic.
        
        Args:
            sources: List of sources to analyze (default: ['techcrunch'])
            limit: Maximum number of trends to return (default: 10)
            hours_back: Hours to look back for trends (default: 24)
            
        Returns:
            Dict containing identified trends
        """
        sources = kwargs.get('sources', ['techcrunch'])
        limit = kwargs.get('limit', 10)
        hours_back = kwargs.get('hours_back', 24)
        
        self.logger.info(f"Analyzing trends from sources: {sources}")
        
        # Step 1: Fetch recent news articles
        articles = await self._fetch_recent_articles(sources, hours_back)
        
        if not articles:
            self.logger.warning("No recent articles found")
            return {"trends": [], "articles_analyzed": 0}
        
        # Step 2: Extract topics from articles
        topics = await self._extract_topics_from_articles(articles)
        
        # Step 3: Analyze and rank topics
        ranked_trends = await self._rank_trends(topics, limit)
        
        # Step 4: Store trends in database
        stored_trends = await self._store_trends(ranked_trends)
        
        return {
            "trends": stored_trends,
            "articles_analyzed": len(articles),
            "topics_extracted": len(topics),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _fetch_recent_articles(self, sources: List[str], hours_back: int) -> List[Dict[str, Any]]:
        """Fetch recent articles from specified sources.
        
        Args:
            sources: List of news sources
            hours_back: Hours to look back
            
        Returns:
            List of article dictionaries
        """
        articles = []
        
        for source in sources:
            try:
                if source.lower() == 'techcrunch':
                    source_articles = await self.news_service.fetch_techcrunch_articles(hours_back)
                    articles.extend(source_articles)
                else:
                    self.logger.warning(f"Unsupported source: {source}")
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch articles from {source}: {str(e)}")
        
        return articles
    
    async def _extract_topics_from_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract topics from articles using LLM.
        
        Args:
            articles: List of articles
            
        Returns:
            List of extracted topics with metadata
        """
        topics = []
        
        for article in articles:
            try:
                # Combine title and summary for topic extraction
                content = f"{article['title']} {article.get('summary', '')}"
                
                # Extract topics using LLM
                extracted_topics = await self.llm_service.extract_topics(content, max_topics=3)
                
                # Generate hashtags for each topic
                for topic in extracted_topics:
                    hashtags = await self.llm_service.generate_hashtags(topic, max_hashtags=3)
                    
                    topics.append({
                        'topic': topic,
                        'hashtags': hashtags,
                        'source_article': {
                            'title': article['title'],
                            'url': article['url'],
                            'published_at': article['published_at']
                        },
                        'source': article['source']
                    })
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to extract topics from article: {str(e)}")
        
        return topics
    
    async def _rank_trends(self, topics: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Rank and filter trends based on relevance and frequency.
        
        Args:
            topics: List of extracted topics
            limit: Maximum number of trends to return
            
        Returns:
            List of ranked trends
        """
        # Count topic frequency
        topic_counts = {}
        topic_data = {}
        counter = 0

        self.logger.info(f"Ranking {len(topics)} extracted topics")
        for topic_info in topics:
            if counter >= 10:
                break
            topic = topic_info['topic'].lower()
            
            if topic not in topic_counts:
                topic_counts[topic] = 0
                topic_data[topic] = topic_info
            
            topic_counts[topic] += 1
            counter += 1

        # Calculate relevance scores using LLM
        ranked_trends = []
        
        for topic, count in topic_counts.items():
            try:
                # Use LLM to assess topic relevance for LinkedIn tech audience
                relevance_prompt = f"""Rate the relevance of this topic for LinkedIn's tech professional audience on a scale of 0-1:
Topic: {topic}

Consider:
- Professional relevance
- Technology focus
- Business impact
- Current interest level

Respond with just a number between 0 and 1."""
                
                relevance_response = await self.llm_service.generate_text(
                    prompt=relevance_prompt,
                    temperature=0.1
                )
                
                try:
                    relevance_score = float(relevance_response.strip())
                    relevance_score = max(0.0, min(1.0, relevance_score))  # Clamp to 0-1
                except ValueError:
                    relevance_score = 0.5  # Default score if parsing fails
                
                # Combine frequency and relevance for final score
                final_score = (relevance_score * 0.7) + (min(count / 5, 1.0) * 0.3)
                
                trend_info = topic_data[topic].copy()
                trend_info['relevance_score'] = final_score
                trend_info['mention_count'] = count
                
                ranked_trends.append(trend_info)
                self.logger.debug(f"Topic data: {trend_info}")


                 # ADD THIS LINE AFTER THE API CALL:
                await asyncio.sleep(1)  # Add 1 second delay between API calls
                
            except Exception as e:
                self.logger.error(f"Failed to rank topic {topic}: {str(e)}")
        
        # Sort by relevance score and return top trends
        ranked_trends.sort(key=lambda x: x['relevance_score'], reverse=True)
        return ranked_trends[:limit]
    
    async def _store_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store trends in database.
        
        Args:
            trends: List of trend data
            
        Returns:
            List of stored trend data with IDs
        """
        stored_trends = []
        
        try:
            db = next(get_db())
            
            for trend_data in trends:
                # Check if trend already exists (within last 24 hours)
                existing_trend = db.query(TrendTopic).filter(
                    TrendTopic.topic == trend_data['topic'],
                    TrendTopic.detected_at >= datetime.utcnow() - timedelta(hours=24)
                ).first()
                
                if existing_trend:
                    # Update existing trend
                    existing_trend.relevance_score = trend_data['relevance_score']
                    existing_trend.hashtags = trend_data['hashtags']
                    existing_trend.is_active = True
                    db.commit()
                    
                    stored_trends.append({
                        'id': existing_trend.id,
                        'topic': existing_trend.topic,
                        'hashtags': existing_trend.hashtags,
                        'relevance_score': existing_trend.relevance_score,
                        'source': existing_trend.source,
                        'detected_at': existing_trend.detected_at.isoformat(),
                        'is_active': existing_trend.is_active
                    })
                else:
                    # Create new trend
                    new_trend = TrendTopic(
                        topic=trend_data['topic'],
                        hashtags=trend_data['hashtags'],
                        relevance_score=trend_data['relevance_score'],
                        source=trend_data['source']
                    )
                    
                    db.add(new_trend)
                    db.commit()
                    db.refresh(new_trend)
                    
                    stored_trends.append({
                        'id': new_trend.id,
                        'topic': new_trend.topic,
                        'hashtags': new_trend.hashtags,
                        'relevance_score': new_trend.relevance_score,
                        'source': new_trend.source,
                        'detected_at': new_trend.detected_at.isoformat(),
                        'is_active': new_trend.is_active
                    })
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store trends: {str(e)}")
            raise
        
        return stored_trends