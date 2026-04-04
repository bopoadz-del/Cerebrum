"""
Named Entity Extraction Pipeline using spaCy
Extracts entities like dates, amounts, organizations, people from documents.
"""

import re
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


class EntityType(Enum):
    """Types of named entities."""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOC"
    DATE = "DATE"
    TIME = "TIME"
    MONEY = "MONEY"
    PERCENT = "PERCENT"
    QUANTITY = "QUANTITY"
    CONTRACT_NUMBER = "CONTRACT_NUMBER"
    PROJECT_NAME = "PROJECT_NAME"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    ADDRESS = "ADDRESS"


@dataclass
class Entity:
    """A named entity with metadata."""
    text: str
    entity_type: EntityType
    start_char: int
    end_char: int
    confidence: float = 1.0
    normalized_value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entity_type": self.entity_type.value,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value,
            "metadata": self.metadata
        }


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: List[Entity]
    entity_counts: Dict[str, int]
    processing_time: float
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.entity_type == entity_type]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_counts": self.entity_counts,
            "processing_time": self.processing_time
        }


class SpacyNERExtractor:
    """
    Named entity extractor using spaCy.
    Extracts standard and custom entities from text.
    """
    
    # Custom patterns for construction domain
    CUSTOM_PATTERNS = {
        EntityType.CONTRACT_NUMBER: [
            r'(?:contract|agreement|po)[\s#:]*(\d{3,}[-\w]*)',
            r'(?:contract|agreement)[\s#:]*([A-Z]{2,}\d{2,})',
        ],
        EntityType.PROJECT_NAME: [
            r'(?:project|job)[\s:]*["\']?([^"\']{5,50})["\']?',
        ],
        EntityType.EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        EntityType.PHONE: [
            r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]\d{4}',
        ],
        EntityType.ADDRESS: [
            r'\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)',
        ],
    }
    
    def __init__(self, model_name: str = "en_core_web_lg"):
        self.model_name = model_name
        self.nlp = None
        
        if SPACY_AVAILABLE:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load spaCy model."""
        try:
            logger.info(f"Loading spaCy model: {self.model_name}")
            self.nlp = spacy.load(self.model_name)
            
            # Add custom entity ruler
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            
            # Add construction-specific patterns
            patterns = [
                {"label": "ORG", "pattern": [{"LOWER": "general"}, {"LOWER": "contractor"}]},
                {"label": "ORG", "pattern": [{"LOWER": "subcontractor"}]},
                {"label": "ORG", "pattern": [{"LOWER": "architect"}]},
                {"label": "ORG", "pattern": [{"LOWER": "engineer"}]},
                {"label": "ORG", "pattern": [{"LOWER": "consultant"}]},
            ]
            ruler.add_patterns(patterns)
            
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            # Try to download
            try:
                spacy.cli.download(self.model_name)
                self.nlp = spacy.load(self.model_name)
            except Exception as e2:
                logger.error(f"Failed to download spaCy model: {e2}")
    
    async def extract_entities(self, text: str) -> ExtractionResult:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
        
        Returns:
            ExtractionResult with all entities
        """
        import time
        start_time = time.time()
        
        entities = []
        
        try:
            # Extract spaCy entities
            if self.nlp:
                spacy_entities = await self._extract_spacy_entities(text)
                entities.extend(spacy_entities)
            
            # Extract custom entities
            custom_entities = await self._extract_custom_entities(text)
            entities.extend(custom_entities)
            
            # Remove duplicates and overlaps
            entities = self._deduplicate_entities(entities)
            
            # Calculate counts
            entity_counts = {}
            for entity in entities:
                type_name = entity.entity_type.value
                entity_counts[type_name] = entity_counts.get(type_name, 0) + 1
            
            processing_time = time.time() - start_time
            
            return ExtractionResult(
                entities=entities,
                entity_counts=entity_counts,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult(
                entities=[],
                entity_counts={},
                processing_time=time.time() - start_time
            )
    
    async def _extract_spacy_entities(self, text: str) -> List[Entity]:
        """Extract entities using spaCy."""
        entities = []
        
        doc = self.nlp(text)
        
        for ent in doc.ents:
            # Map spaCy entity types to our types
            entity_type = self._map_entity_type(ent.label_)
            
            if entity_type:
                entity = Entity(
                    text=ent.text,
                    entity_type=entity_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.9,
                    normalized_value=self._normalize_entity(ent.text, entity_type)
                )
                entities.append(entity)
        
        return entities
    
    async def _extract_custom_entities(self, text: str) -> List[Entity]:
        """Extract custom entities using regex patterns."""
        entities = []
        
        for entity_type, patterns in self.CUSTOM_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    entity = Entity(
                        text=match.group(0),
                        entity_type=entity_type,
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=0.85,
                        normalized_value=match.group(1) if match.groups() else match.group(0)
                    )
                    entities.append(entity)
        
        return entities
    
    def _map_entity_type(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity label to our entity type."""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,
            "LOC": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "MONEY": EntityType.MONEY,
            "PERCENT": EntityType.PERCENT,
            "QUANTITY": EntityType.QUANTITY,
            "CARDINAL": EntityType.QUANTITY,
        }
        return mapping.get(spacy_label)
    
    def _normalize_entity(self, text: str, entity_type: EntityType) -> Optional[str]:
        """Normalize entity value."""
        if entity_type == EntityType.DATE:
            # Try to parse date
            try:
                # Handle various date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y', '%b %d, %Y']:
                    try:
                        parsed = datetime.strptime(text.strip(), fmt)
                        return parsed.isoformat()
                    except ValueError:
                        continue
            except Exception:
                pass
        
        elif entity_type == EntityType.MONEY:
            # Extract numeric value
            match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
            if match:
                return match.group(0)
        
        elif entity_type == EntityType.PERCENT:
            # Extract percentage value
            match = re.search(r'[\d.]+', text)
            if match:
                return match.group(0)
        
        return None
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate and overlapping entities."""
        # Sort by confidence (highest first)
        sorted_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
        
        result = []
        covered_ranges: Set[Tuple[int, int]] = set()
        
        for entity in sorted_entities:
            # Check for overlap
            overlaps = False
            for start, end in covered_ranges:
                if not (entity.end_char <= start or entity.start_char >= end):
                    overlaps = True
                    break
            
            if not overlaps:
                result.append(entity)
                covered_ranges.add((entity.start_char, entity.end_char))
        
        # Sort by position
        result.sort(key=lambda e: e.start_char)
        
        return result


class EntityRelationshipExtractor:
    """Extract relationships between entities."""
    
    def __init__(self, ner_extractor: SpacyNERExtractor):
        self.ner = ner_extractor
    
    async def extract_relationships(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities.
        
        Args:
            text: Input text
        
        Returns:
            List of relationships
        """
        relationships = []
        
        # Extract entities
        result = await self.ner.extract_entities(text)
        entities = result.entities
        
        # Find relationships based on proximity and context
        orgs = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]
        people = [e for e in entities if e.entity_type == EntityType.PERSON]
        dates = [e for e in entities if e.entity_type == EntityType.DATE]
        amounts = [e for e in entities if e.entity_type == EntityType.MONEY]
        
        # Person-Organization relationships
        for person in people:
            for org in orgs:
                if abs(person.start_char - org.start_char) < 100:
                    relationships.append({
                        "type": "person_organization",
                        "person": person.text,
                        "organization": org.text,
                        "context": text[max(0, person.start_char - 20):min(len(text), org.end_char + 20)]
                    })
        
        # Date-Amount relationships (payments, deadlines)
        for date in dates:
            for amount in amounts:
                if abs(date.start_char - amount.start_char) < 50:
                    relationships.append({
                        "type": "date_amount",
                        "date": date.text,
                        "amount": amount.text,
                        "context": text[max(0, date.start_char - 20):min(len(text), amount.end_char + 20)]
                    })
        
        return relationships


class EntityExtractorPipeline:
    """Pipeline for entity extraction."""
    
    def __init__(self):
        self.ner = SpacyNERExtractor()
        self.relationships = EntityRelationshipExtractor(self.ner)
    
    async def process_document(
        self,
        text: str,
        extract_relationships: bool = False
    ) -> Dict[str, Any]:
        """
        Process document and extract entities.
        
        Args:
            text: Document text
            extract_relationships: Whether to extract relationships
        
        Returns:
            Dictionary with entities and relationships
        """
        # Extract entities
        entity_result = await self.ner.extract_entities(text)
        
        result = {
            "entities": entity_result.to_dict(),
        }
        
        # Extract relationships if requested
        if extract_relationships:
            relationships = await self.relationships.extract_relationships(text)
            result["relationships"] = relationships
        
        return result
    
    async def batch_process(
        self,
        documents: List[Tuple[str, str]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents.
        
        Args:
            documents: List of (doc_id, text) tuples
            progress_callback: Optional progress callback
        
        Returns:
            Dictionary mapping doc_id to results
        """
        results = {}
        
        for i, (doc_id, text) in enumerate(documents):
            result = await self.process_document(text)
            results[doc_id] = result
            
            if progress_callback:
                progress_callback(i + 1, len(documents))
        
        return results


# Convenience function
async def extract_entities(
    text: str,
    extract_relationships: bool = False
) -> Dict[str, Any]:
    """
    Extract named entities from text.
    
    Args:
        text: Input text
        extract_relationships: Whether to extract relationships
    
    Returns:
        Dictionary with entities and relationships
    """
    pipeline = EntityExtractorPipeline()
    return await pipeline.process_document(text, extract_relationships)
