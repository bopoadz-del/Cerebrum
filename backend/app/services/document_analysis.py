"""
Enhanced Document Analysis Service for Cerebrum AI

Provides AI-powered document analysis including:
- Intelligent summarization
- Key information extraction
- Topic classification
- Sentiment analysis
- Entity relationship mapping
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class DocumentSummary:
    """Document summary with key information."""
    overview: str
    key_points: List[str]
    topics: List[str]
    word_count: int
    reading_time_minutes: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overview": self.overview,
            "key_points": self.key_points,
            "topics": self.topics,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes
        }


@dataclass
class DocumentAnalysisResult:
    """Complete document analysis result."""
    success: bool
    summary: Optional[DocumentSummary] = None
    entities: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: Optional[Dict[str, Any]] = None
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "summary": self.summary.to_dict() if self.summary else None,
            "entities": self.entities,
            "sentiment": self.sentiment,
            "relationships": self.relationships,
            "action_items": self.action_items,
            "metadata": self.metadata,
            "error": self.error
        }


class DocumentAnalysisService:
    """
    AI-powered document analysis service.
    
    Features:
    - Intelligent summarization using extractive and abstractive methods
    - Named entity recognition
    - Sentiment analysis
    - Topic extraction
    - Action item extraction
    - Relationship mapping
    """
    
    def __init__(self):
        self._openai_available = self._check_openai_available()
        
    def _check_openai_available(self) -> bool:
        """Check if OpenAI is available for AI-powered analysis."""
        try:
            from app.core.config import settings
            return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-key-here")
        except:
            return False
    
    async def analyze_document(
        self,
        text: str,
        document_type: Optional[str] = None,
        analysis_depth: str = "standard"
    ) -> DocumentAnalysisResult:
        """
        Perform comprehensive document analysis.
        
        Args:
            text: Document text content
            document_type: Optional document type hint
            analysis_depth: "basic", "standard", or "deep"
            
        Returns:
            DocumentAnalysisResult with all analysis components
        """
        try:
            # Generate summary
            summary = await self._generate_summary(text, analysis_depth)
            
            # Extract entities
            entities = await self._extract_entities(text)
            
            # Analyze sentiment
            sentiment = await self._analyze_sentiment(text)
            
            # Extract action items
            action_items = await self._extract_action_items(text, document_type)
            
            # Map relationships
            relationships = await self._map_relationships(text, entities)
            
            # Build metadata
            metadata = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "analysis_depth": analysis_depth,
                "document_type": document_type or "unknown",
                "char_count": len(text),
                "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
            }
            
            return DocumentAnalysisResult(
                success=True,
                summary=summary,
                entities=entities,
                sentiment=sentiment,
                relationships=relationships,
                action_items=action_items,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return DocumentAnalysisResult(
                success=False,
                error=f"Analysis failed: {str(e)}"
            )
    
    async def _generate_summary(
        self,
        text: str,
        depth: str = "standard"
    ) -> DocumentSummary:
        """Generate document summary using AI or fallback methods."""
        word_count = len(text.split())
        reading_time = max(1, word_count // 200)  # ~200 words per minute
        
        # Try AI-powered summarization if available
        if self._openai_available and depth in ["standard", "deep"]:
            try:
                return await self._generate_ai_summary(text, depth)
            except Exception as e:
                logger.warning(f"AI summary failed, using fallback: {e}")
        
        # Fallback: Extractive summarization
        return self._generate_extractive_summary(text, word_count, reading_time)
    
    async def _generate_ai_summary(
        self,
        text: str,
        depth: str
    ) -> DocumentSummary:
        """Generate summary using OpenAI."""
        import openai
        from app.core.config import settings
        
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Truncate text if too long
        max_chars = 8000 if depth == "deep" else 4000
        truncated_text = text[:max_chars]
        if len(text) > max_chars:
            truncated_text += "\n... [content truncated]"
        
        key_points_count = 5 if depth == "deep" else 3
        
        prompt = f"""Analyze the following document and provide:
1. A concise overview (2-3 sentences)
2. {key_points_count} key points
3. Main topics (up to 5)

Document:
{truncated_text}

Format your response as:
OVERVIEW: [overview text]
KEY POINTS:
- [point 1]
- [point 2]
...
TOPICS: [topic1, topic2, ...]"""
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a document analysis assistant. Provide clear, structured summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        # Parse response
        overview = ""
        key_points = []
        topics = []
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('OVERVIEW:'):
                overview = line.replace('OVERVIEW:', '').strip()
                current_section = 'overview'
            elif line.startswith('KEY POINTS:'):
                current_section = 'key_points'
            elif line.startswith('TOPICS:'):
                topics_text = line.replace('TOPICS:', '').strip()
                topics = [t.strip() for t in topics_text.split(',')]
                current_section = None
            elif line.startswith('- ') and current_section == 'key_points':
                key_points.append(line[2:].strip())
            elif current_section == 'overview' and line:
                overview += " " + line
        
        return DocumentSummary(
            overview=overview or "Summary not available",
            key_points=key_points or ["No key points extracted"],
            topics=topics or ["General"],
            word_count=len(text.split()),
            reading_time_minutes=max(1, len(text.split()) // 200)
        )
    
    def _generate_extractive_summary(
        self,
        text: str,
        word_count: int,
        reading_time: int
    ) -> DocumentSummary:
        """Generate summary using extractive methods."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Score sentences (simple TF-IDF-like scoring)
        word_freq = {}
        for sentence in sentences:
            for word in sentence.lower().split():
                word = re.sub(r'[^\w]', '', word)
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Score sentences based on word frequency
        sentence_scores = []
        for sentence in sentences:
            score = sum(word_freq.get(w, 0) for w in sentence.lower().split())
            sentence_scores.append((sentence, score))
        
        # Get top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:3]]
        
        # Extract key points (first sentence of each paragraph)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        key_points = []
        for para in paragraphs[:5]:
            first_sentence = para.split('.')[0].strip()
            if len(first_sentence) > 20:
                key_points.append(first_sentence)
        
        # Extract topics (common keywords)
        topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        topic_names = [t[0].capitalize() for t in topics]
        
        overview = " ".join(top_sentences[:2]) if top_sentences else "Document overview not available."
        
        return DocumentSummary(
            overview=overview,
            key_points=key_points[:5] or ["No key points extracted"],
            topics=topic_names or ["General"],
            word_count=word_count,
            reading_time_minutes=reading_time
        )
    
    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        try:
            from app.pipelines.ner_extraction import extract_entities
            result = await extract_entities(text)
            return result.get("entities", {}).get("entities", [])
        except Exception as e:
            logger.warning(f"NER extraction failed: {e}")
            return []
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze document sentiment."""
        try:
            # Simple keyword-based sentiment
            positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'improvement', 'benefit', 'advantage']
            negative_words = ['bad', 'poor', 'negative', 'failure', 'problem', 'issue', 'concern', 'risk']
            
            text_lower = text.lower()
            positive_count = sum(1 for w in positive_words if w in text_lower)
            negative_count = sum(1 for w in negative_words if w in text_lower)
            
            total = positive_count + negative_count
            if total == 0:
                sentiment = "neutral"
                score = 0.5
            else:
                score = positive_count / total
                if score > 0.6:
                    sentiment = "positive"
                elif score < 0.4:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
            
            return {
                "sentiment": sentiment,
                "score": round(score, 2),
                "positive_indicators": positive_count,
                "negative_indicators": negative_count
            }
            
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {"sentiment": "unknown", "score": 0.5}
    
    async def _extract_action_items(
        self,
        text: str,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract action items from text."""
        try:
            from app.pipelines.action_extraction import extract_action_items
            result = await extract_action_items(text, document_type or "general")
            return [a.to_dict() for a in result.actions]
        except Exception as e:
            logger.warning(f"Action extraction failed: {e}")
            return []
    
    async def _map_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Map relationships between entities."""
        relationships = []
        
        try:
            # Simple co-occurrence based relationship detection
            sentences = re.split(r'[.!?]+', text)
            
            for sentence in sentences:
                sentence_entities = []
                for entity in entities:
                    entity_text = entity.get("text", "").lower()
                    if entity_text and entity_text in sentence.lower():
                        sentence_entities.append(entity)
                
                # If multiple entities in same sentence, they might be related
                if len(sentence_entities) >= 2:
                    for i in range(len(sentence_entities)):
                        for j in range(i + 1, len(sentence_entities)):
                            relationships.append({
                                "source": sentence_entities[i].get("text"),
                                "source_type": sentence_entities[i].get("type"),
                                "target": sentence_entities[j].get("text"),
                                "target_type": sentence_entities[j].get("type"),
                                "context": sentence.strip()[:100]
                            })
            
            # Remove duplicates
            seen = set()
            unique_relationships = []
            for rel in relationships:
                key = (rel["source"], rel["target"])
                if key not in seen:
                    seen.add(key)
                    unique_relationships.append(rel)
            
            return unique_relationships[:20]  # Limit to 20 relationships
            
        except Exception as e:
            logger.warning(f"Relationship mapping failed: {e}")
            return []
    
    async def quick_summarize(self, text: str, max_sentences: int = 3) -> str:
        """Quick document summarization."""
        try:
            summary = await self._generate_summary(text, "basic")
            return summary.overview
        except Exception as e:
            logger.error(f"Quick summarize failed: {e}")
            # Fallback: return first few sentences
            sentences = re.split(r'[.!?]+', text)
            return ". ".join(sentences[:max_sentences]) + "."


# Singleton instance
_document_analysis_service: Optional[DocumentAnalysisService] = None


def get_document_analysis_service() -> DocumentAnalysisService:
    """Get or create document analysis service instance."""
    global _document_analysis_service
    if _document_analysis_service is None:
        _document_analysis_service = DocumentAnalysisService()
    return _document_analysis_service
