"""
Content Creation Agent for generating LinkedIn posts.
"""
import re
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.models.database import Post, TrendTopic, get_db
from app.services.llm_service import LLMService
from app.utils.text_processing import TextProcessor


class ContentCreationAgent(BaseAgent):
    """Agent responsible for generating LinkedIn posts based on trends or custom topics."""
    
    def __init__(self):
        """Initialize the Content Creation Agent."""
        super().__init__("ContentCreationAgent")
        self.llm_service = LLMService()
        self.text_processor = TextProcessor()
    
    def _validate_input(self, **kwargs) -> None:
        """Validate input parameters for content generation.
        
        Args:
            **kwargs: Parameters to validate
            
        Raises:
            ValueError: If validation fails
        """
        trend_topic_id = kwargs.get('trend_topic_id')
        custom_topic = kwargs.get('custom_topic')
        tone = kwargs.get('tone', 'professional')
        
        if not trend_topic_id and not custom_topic:
            raise ValueError("Either trend_topic_id or custom_topic must be provided")
        
        if tone not in ['professional', 'casual', 'technical']:
            raise ValueError("Tone must be one of: professional, casual, technical")
    
    async def _execute_logic(self, **kwargs) -> Dict[str, Any]:
        """Execute content creation logic.
        
        Args:
            trend_topic_id: ID of trending topic to base content on
            custom_topic: Custom topic for content generation
            tone: Tone of the content (professional, casual, technical)
            include_hashtags: Whether to include hashtags
            target_length: Target character count (default: 1500)
            
        Returns:
            Dict containing generated content and metadata
        """
        trend_topic_id = kwargs.get('trend_topic_id')
        custom_topic = kwargs.get('custom_topic')
        tone = kwargs.get('tone', 'professional')
        include_hashtags = kwargs.get('include_hashtags', True)
        target_length = kwargs.get('target_length', 1500)
        
        self.logger.info(f"Generating content with tone: {tone}")
        
        # Step 1: Get topic information
        topic_info = await self._get_topic_info(trend_topic_id, custom_topic)
        
        # Step 2: Generate base content
        content = await self._generate_base_content(topic_info, tone, target_length)
        
        # Step 3: Optimize content for readability
        optimized_content = await self._optimize_content(content)
        
        # Step 4: Generate hashtags if requested
        hashtags = []
        if include_hashtags:
            hashtags = await self._generate_hashtags(optimized_content, topic_info)
        
        # Step 5: Analyze content quality
        quality_metrics = await self._analyze_content_quality(optimized_content)
        
        # Step 6: Store content in database
        post_data = await self._store_content(
            optimized_content, hashtags, quality_metrics, trend_topic_id
        )
        
        return {
            "post": post_data,
            "topic_info": topic_info,
            "quality_metrics": quality_metrics,
            "generation_params": {
                "tone": tone,
                "target_length": target_length,
                "include_hashtags": include_hashtags
            }
        }
    
    async def _get_topic_info(self, trend_topic_id: Optional[int], custom_topic: Optional[str]) -> Dict[str, Any]:
        """Get information about the topic for content generation."""
        if trend_topic_id:
            try:
                db = next(get_db())
                trend = db.query(TrendTopic).filter(TrendTopic.id == trend_topic_id).first()
                db.close()
                
                if not trend:
                    raise ValueError(f"Trend topic with ID {trend_topic_id} not found")
                
                return {
                    "topic": trend.topic,
                    "hashtags": trend.hashtags or [],
                    "relevance_score": trend.relevance_score,
                    "source": trend.source,
                    "is_trending": True
                }
            except Exception as e:
                self.logger.error(f"Failed to fetch trend topic: {str(e)}")
                raise
        else:
            # Extract topics from custom topic using LLM
            topics = await self.llm_service.extract_topics(custom_topic, max_topics=3)
            
            return {
                "topic": custom_topic,
                "hashtags": [],
                "relevance_score": 0.5,
                "source": "custom",
                "is_trending": False,
                "extracted_topics": topics
            }
    
    async def _generate_base_content(self, topic_info: Dict[str, Any], tone: str, target_length: int) -> str:
        """Generate base content using LLM."""
        # Create system prompt based on tone
        tone_instructions = {
            'professional': "Write in a professional, authoritative tone suitable for business leaders and industry experts. Focus on insights, best practices, and strategic implications.",
            'casual': "Write in a conversational, approachable tone that's still professional but more relatable. Use a friendly voice that encourages discussion.",
            'technical': "Write in a technical tone with detailed explanations suitable for developers and technical professionals. Include specific details and technical insights."
        }
        
        system_prompt = f"""You are an expert LinkedIn content creator specializing in technology and business topics.

Instructions:
- {tone_instructions[tone]}
- Target length: approximately {target_length} characters
- Create engaging content that provides value to LinkedIn's professional audience
- Include insights, actionable takeaways, or thought-provoking questions
- Use proper formatting with line breaks for readability
- Do NOT include hashtags in the content (they will be added separately)
- Make it likely to generate meaningful professional discussions
- Focus on current trends and industry relevance

The content should be informative, engaging, and encourage professional networking and discussion."""
        
        topic = topic_info['topic']
        context = ""
        
        if topic_info.get('is_trending'):
            context = f"This is currently a trending topic with relevance score: {topic_info['relevance_score']}"
        
        if topic_info.get('extracted_topics'):
            context += f" Related topics: {', '.join(topic_info['extracted_topics'])}"
        
        prompt = f"""Create a LinkedIn post about: {topic}

Context: {context}

Generate engaging content that will resonate with LinkedIn's tech professional audience and encourage meaningful engagement."""
        
        try:
            content = await self.llm_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate base content: {str(e)}")
            raise
    
    async def _optimize_content(self, content: str) -> str:
        """Optimize content for readability and engagement."""
        try:
            # Use LLM to improve readability
            optimized = await self.llm_service.improve_readability(content)
            
            # Ensure content meets LinkedIn requirements
            optimized = self._ensure_linkedin_compliance(optimized)
            
            return optimized
            
        except Exception as e:
            self.logger.warning(f"Content optimization failed: {str(e)}")
            return self._ensure_linkedin_compliance(content)
    
    def _ensure_linkedin_compliance(self, content: str) -> str:
        """Ensure content complies with LinkedIn requirements."""
        # Truncate if too long
        if len(content) > self.settings.max_post_length:
            content = content[:self.settings.max_post_length - 3] + "..."
        
        # Remove any existing hashtags from content
        content = re.sub(r'#\w+', '', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    async def _generate_hashtags(self, content: str, topic_info: Dict[str, Any]) -> list:
        """Generate relevant hashtags for the content."""
        try:
            # Start with hashtags from trending topic if available
            hashtags = list(topic_info.get('hashtags', []))
            
            # Generate additional hashtags based on content
            content_hashtags = await self.llm_service.generate_hashtags(
                content, max_hashtags=self.settings.max_hashtags
            )
            
            # Combine and deduplicate
            all_hashtags = list(dict.fromkeys(hashtags + content_hashtags))
            
            # Return up to max_hashtags
            return all_hashtags[:self.settings.max_hashtags]
            
        except Exception as e:
            self.logger.error(f"Failed to generate hashtags: {str(e)}")
            return []
    
    async def _analyze_content_quality(self, content: str) -> Dict[str, Any]:
        """Analyze the quality of generated content."""
        try:
            # Character and word counts
            char_count = len(content)
            word_count = len(content.split())
            
            # Readability score
            readability_score = self.text_processor.calculate_readability(content)
            
            # Engagement prediction using simple heuristics
            engagement_score = self._predict_engagement(content)
            
            # Validate content
            validation_results = self.text_processor.validate_content(content)
            
            return {
                "character_count": char_count,
                "word_count": word_count,
                "readability_score": readability_score,
                "engagement_score": engagement_score,
                "meets_length_requirements": char_count <= self.settings.max_post_length,
                "meets_readability_requirements": readability_score >= self.settings.min_readability_score,
                "validation": validation_results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze content quality: {str(e)}")
            return {
                "character_count": len(content),
                "word_count": len(content.split()),
                "readability_score": 50.0,
                "engagement_score": 0.5,
                "meets_length_requirements": True,
                "meets_readability_requirements": True
            }
    
    def _predict_engagement(self, content: str) -> float:
        """Predict engagement score based on content characteristics."""
        score = 0.5  # Base score
        
        # Check for engagement elements
        if '?' in content:  # Questions encourage engagement
            score += 0.15
        
        if any(phrase in content.lower() for phrase in [
            'what do you think', 'thoughts', 'agree', 'disagree', 'share your experience',
            'let me know', 'comment below', 'your thoughts?'
        ]):
            score += 0.15
        
        if any(word in content.lower() for word in [
            'tip', 'insight', 'learn', 'discover', 'revealed', 'secret', 'strategy'
        ]):
            score += 0.1
        
        # Check content length (optimal range for LinkedIn)
        char_count = len(content)
        if 800 <= char_count <= 2000:
            score += 0.1
        elif char_count < 500:
            score -= 0.1
        
        # Check for structure (line breaks indicate good formatting)
        if content.count('\n') >= 2:
            score += 0.1
        
        # Check for action words
        action_words = ['implement', 'build', 'create', 'develop', 'improve', 'optimize']
        if any(word in content.lower() for word in action_words):
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    async def _store_content(self, content: str, hashtags: list, quality_metrics: Dict[str, Any], trend_topic_id: Optional[int]) -> Dict[str, Any]:
        """Store generated content in database."""
        try:
            db = next(get_db())
            
            post = Post(
                content=content,
                hashtags=hashtags,
                readability_score=quality_metrics.get('readability_score'),
                character_count=quality_metrics.get('character_count'),
                trend_topic_id=trend_topic_id,
                status='draft'
            )
            
            db.add(post)
            db.commit()
            db.refresh(post)
            db.close()
            
            return {
                "id": post.id,
                "content": post.content,
                "hashtags": post.hashtags,
                "readability_score": post.readability_score,
                "character_count": post.character_count,
                "status": post.status,
                "created_at": post.created_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to store content: {str(e)}")
            raise
    
    async def generate_multiple_variants(self, topic_info: Dict[str, Any], count: int = 3) -> list[Dict[str, Any]]:
        """Generate multiple content variants for A/B testing."""
        variants = []
        tones = ['professional', 'casual', 'technical']
        
        for i in range(min(count, len(tones))):
            try:
                tone = tones[i]
                content = await self._generate_base_content(topic_info, tone, 1500)
                optimized = await self._optimize_content(content)
                hashtags = await self._generate_hashtags(optimized, topic_info)
                quality = await self._analyze_content_quality(optimized)
                
                variants.append({
                    "variant": i + 1,
                    "tone": tone,
                    "content": optimized,
                    "hashtags": hashtags,
                    "quality_metrics": quality
                })
                
            except Exception as e:
                self.logger.error(f"Failed to generate variant {i + 1}: {str(e)}")
        
        return variants