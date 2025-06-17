"""
Text processing utilities for content analysis and optimization.
"""
import re
from typing import List, Dict, Any
from textblob import TextBlob

# Try to import spacy, fallback if not available
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# Try to import textstat for readability, fallback if not available
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False


class TextProcessor:
    """Utility class for text processing and analysis."""
    
    def __init__(self):
        """Initialize text processor with available models."""
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                # spaCy model not available
                self.nlp = None
    
    def calculate_readability(self, text: str) -> float:
        """Calculate readability score for text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Readability score (higher is more readable, 0-100 scale)
        """
        if not text or not text.strip():
            return 50.0
        
        try:
            if TEXTSTAT_AVAILABLE:
                # Use Flesch Reading Ease score (0-100, higher is better)
                score = textstat.flesch_reading_ease(text)
                # Ensure score is in 0-100 range
                return max(0.0, min(100.0, score))
            else:
                # Fallback to simple calculation
                return self._simple_readability_score(text)
                
        except Exception:
            # Fallback calculation using simple metrics
            return self._simple_readability_score(text)
    
    def _simple_readability_score(self, text: str) -> float:
        """Simple readability calculation as fallback.
        
        Args:
            text: Text to analyze
            
        Returns:
            Simple readability score (0-100)
        """
        if not text or not text.strip():
            return 50.0
        
        # Split into sentences and words
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = text.split()
        
        if not words or not sentences:
            return 50.0
        
        # Calculate metrics
        avg_words_per_sentence = len(words) / len(sentences)
        avg_chars_per_word = sum(len(word) for word in words) / len(words)
        
        # Simple heuristic: shorter sentences and words = more readable
        # Base score of 80, subtract for complexity
        score = 80.0
        
        # Penalty for long sentences (ideal: 15-20 words)
        if avg_words_per_sentence > 20:
            score -= (avg_words_per_sentence - 20) * 2
        elif avg_words_per_sentence < 10:
            score -= (10 - avg_words_per_sentence) * 1
        
        # Penalty for long words (ideal: 4-5 characters)
        if avg_chars_per_word > 6:
            score -= (avg_chars_per_word - 6) * 3
        
        return max(0.0, min(100.0, score))
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using NLP.
        
        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not self.nlp:
            return self._simple_keyword_extraction(text, max_keywords)
        
        try:
            doc = self.nlp(text)
            
            # Extract entities and important tokens
            keywords = set()
            
            # Add named entities
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'PRODUCT', 'TECHNOLOGY', 'GPE', 'PERSON']:
                    keywords.add(ent.text.lower())
            
            # Add important nouns and adjectives
            for token in doc:
                if (token.pos_ in ['NOUN', 'ADJ'] and 
                    not token.is_stop and 
                    not token.is_punct and 
                    len(token.text) > 2 and
                    token.text.isalpha()):
                    keywords.add(token.lemma_.lower())
            
            return list(keywords)[:max_keywords]
            
        except Exception:
            return self._simple_keyword_extraction(text, max_keywords)
    
    def _simple_keyword_extraction(self, text: str, max_keywords: int) -> List[str]:
        """Simple keyword extraction fallback.
        
        Args:
            text: Text to analyze
            max_keywords: Maximum keywords to return
            
        Returns:
            List of simple keywords
        """
        # Remove punctuation and convert to lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        # Simple stopwords list
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their', 'can', 'may', 'might', 'must', 'shall', 'get',
            'got', 'make', 'made', 'take', 'took', 'come', 'came', 'go', 'went'
        }
        
        # Filter out stopwords and short words
        keywords = [word for word in words 
                   if word not in stopwords and len(word) > 2 and word.isalpha()]
        
        # Count frequency and return most common
        word_counts = {}
        for word in keywords:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using TextBlob.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict containing sentiment analysis
        """
        try:
            blob = TextBlob(text)
            
            # TextBlob returns polarity (-1 to 1) and subjectivity (0 to 1)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Classify sentiment
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"
            
            return {
                "sentiment_score": polarity,
                "sentiment_label": label,
                "subjectivity": subjectivity,
                "confidence": abs(polarity)
            }
            
        except Exception as e:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "subjectivity": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'""]', '', text)
        
        # Fix common issues
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of mentioned usernames
        """
        mentions = re.findall(r'@(\w+)', text)
        return list(set(mentions))  # Remove duplicates
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of hashtags (without # symbol)
        """
        hashtags = re.findall(r'#(\w+)', text)
        return list(set(hashtags))  # Remove duplicates
    
    def format_for_linkedin(self, text: str, max_length: int = 3000) -> str:
        """Format text for LinkedIn posting.
        
        Args:
            text: Text to format
            max_length: Maximum character length
            
        Returns:
            LinkedIn-formatted text
        """
        # Clean the text
        formatted_text = self.clean_text(text)
        
        # Ensure proper line breaks for readability
        paragraphs = formatted_text.split('\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                # Break long paragraphs
                if len(paragraph) > 200:
                    sentences = paragraph.split('. ')
                    current_para = []
                    current_length = 0
                    
                    for sentence in sentences:
                        if current_length + len(sentence) > 200 and current_para:
                            formatted_paragraphs.append('. '.join(current_para) + '.')
                            current_para = [sentence]
                            current_length = len(sentence)
                        else:
                            current_para.append(sentence)
                            current_length += len(sentence) + 2
                    
                    if current_para:
                        formatted_paragraphs.append('. '.join(current_para))
                else:
                    formatted_paragraphs.append(paragraph)
        
        # Join with proper spacing
        formatted_text = '\n\n'.join(formatted_paragraphs)
        
        # Truncate if too long
        if len(formatted_text) > max_length:
            formatted_text = formatted_text[:max_length - 3] + "..."
        
        return formatted_text
    
    def validate_content(self, text: str) -> Dict[str, Any]:
        """Validate content for LinkedIn posting.
        
        Args:
            text: Text to validate
            
        Returns:
            Dict containing validation results
        """
        issues = []
        suggestions = []
        
        # Check length
        if len(text) > 3000:
            issues.append("Content exceeds LinkedIn's 3000 character limit")
            suggestions.append("Consider shortening the content or splitting into multiple posts")
        
        # Check readability
        readability_score = self.calculate_readability(text)
        if readability_score < 60:
            issues.append("Content may be difficult to read")
            suggestions.append("Try using shorter sentences and simpler words")
        
        # Check for excessive hashtags
        hashtags = self.extract_hashtags(text)
        if len(hashtags) > 5:
            issues.append("Too many hashtags may reduce engagement")
            suggestions.append("Limit hashtags to 3-5 most relevant ones")
        
        # Check for engagement elements
        has_question = '?' in text
        has_call_to_action = any(phrase in text.lower() for phrase in [
            'what do you think', 'share your thoughts', 'let me know',
            'comment below', 'thoughts?'
        ])
        
        if not has_question and not has_call_to_action:
            suggestions.append("Consider adding a question or call-to-action to encourage engagement")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "character_count": len(text),
            "readability_score": readability_score,
            "hashtag_count": len(hashtags),
            "has_engagement_elements": has_question or has_call_to_action
        }