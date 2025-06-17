"""
LLM service for interacting with OPENAI via OPENAI API.
"""
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger

from app.config.settings import settings


class LLMService:
    """Service for interacting with Chatgpt LLM."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self.logger = logger.bind(service="llm")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate text using OPENAI.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            
        Returns:
            Generated text
            
        Raises:
            Exception: If API call fails
        """
        try:
            self.logger.info("Generating text with OPENAI", prompt_length=len(prompt))
            
            messages = [{"role": "user", "content": prompt}]
            
            messages_formatted = []
            if system_prompt:
                 messages_formatted.append({"role": "system", "content": system_prompt})
            messages_formatted.extend(messages)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_formatted,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature
            )
            generated_text = response.choices[0].message.content
            
            self.logger.info(
                "Text generated successfully",
                response_length=len(generated_text),
                tokens_used=response.usage.total_tokens
            )
            
            return generated_text
            
        except Exception as e:
            self.logger.error(f"Failed to generate text: {str(e)}")
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using OPENAI.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict containing sentiment analysis results
        """
        system_prompt = """You are a sentiment analysis expert. Analyze the sentiment of the given text and provide:
1. A sentiment score between -1 (very negative) and 1 (very positive)
2. A sentiment label (positive, negative, or neutral)
3. A brief explanation of the sentiment

Respond in JSON format:
{
    "sentiment_score": float,
    "sentiment_label": "positive|negative|neutral",
    "explanation": "brief explanation"
}"""
        
        prompt = f"Analyze the sentiment of this text: {text}"
        
        try:
            response = await self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1  # Lower temperature for consistent analysis
            )
            
            # Parse JSON response
            import json
            sentiment_data = json.loads(response)
            
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Failed to analyze sentiment: {str(e)}")
            # Fallback to basic sentiment classification
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "explanation": "Analysis failed, defaulting to neutral"
            }
    
    async def extract_topics(self, text: str, max_topics: int = 5) -> List[str]:
        """Extract main topics from text.
        
        Args:
            text: Text to analyze
            max_topics: Maximum number of topics to extract
            
        Returns:
            List of extracted topics
        """
        system_prompt = f"""You are a topic extraction expert. Extract the main topics from the given text.
Return up to {max_topics} topics as a JSON array of strings.
Focus on technology, business, and professional topics relevant to LinkedIn.

Example response: ["artificial intelligence", "startup funding", "remote work"]"""
        
        prompt = f"Extract the main topics from this text: {text}"
        
        try:
            response = await self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            import json
            topics = json.loads(response)
            
            return topics[:max_topics]
            
        except Exception as e:
            self.logger.error(f"Failed to extract topics: {str(e)}")
            return []
    
    async def generate_hashtags(self, content: str, max_hashtags: int = 5) -> List[str]:
        """Generate relevant hashtags for content.
        
        Args:
            content: Content to generate hashtags for
            max_hashtags: Maximum number of hashtags
            
        Returns:
            List of hashtags (without # symbol)
        """
        system_prompt = f"""You are a LinkedIn hashtag expert. Generate relevant hashtags for the given content.
Return up to {max_hashtags} hashtags as a JSON array of strings (without the # symbol).
Focus on professional, technology, and business hashtags that would be relevant on LinkedIn.

Example response: ["tech", "innovation", "startup", "AI", "productivity"]"""
        
        prompt = f"Generate relevant hashtags for this content: {content}"
        
        try:
            response = await self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            import json
            hashtags = json.loads(response)
            
            return hashtags[:max_hashtags]
            
        except Exception as e:
            self.logger.error(f"Failed to generate hashtags: {str(e)}")
            return []
    
    async def improve_readability(self, text: str) -> str:
        """Improve the readability of text for LinkedIn.
        
        Args:
            text: Text to improve
            
        Returns:
            Improved text
        """
        system_prompt = """You are a professional LinkedIn content editor. Improve the readability and engagement of the given text while maintaining its core message.

Guidelines:
- Keep it professional but engaging
- Use shorter sentences and paragraphs
- Add line breaks for better readability
- Maintain the original tone and key points
- Ensure it's suitable for LinkedIn audience (professionals and tech enthusiasts)
- Keep within LinkedIn's character limits"""
        
        prompt = f"Improve the readability of this LinkedIn post: {text}"
        
        try:
            improved_text = await self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )
            
            return improved_text.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to improve readability: {str(e)}")
            return text  # Return original if improvement fails