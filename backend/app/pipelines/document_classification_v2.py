"""
Enhanced Document Classification with Local LLM
ML-powered document type detection for construction documents.
"""

import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from app.core.logging import get_logger
from app.pipelines.ocr import EnhancedOCR

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = get_logger(__name__)


class DocumentType(Enum):
    """Construction document types."""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    CHANGE_ORDER = "change_order"
    SAFETY_REPORT = "safety_report"
    DAILY_REPORT = "daily_report"
    BLUEPRINT = "blueprint"
    SPECIFICATION = "specification"
    SUBMITTAL = "submittal"
    RFI = "rfi"
    RFQ = "rfq"
    PERMIT = "permit"
    MEETING_MINUTES = "meeting_minutes"
    CORRESPONDENCE = "correspondence"
    PHOTO = "photo"
    UNKNOWN = "unknown"


class DocumentCategory(Enum):
    """High-level document categories."""
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    SAFETY = "safety"
    ADMINISTRATIVE = "administrative"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class ClassificationResult:
    """Document classification result."""
    document_type: DocumentType
    category: DocumentCategory
    confidence: float
    subtype: Optional[str] = None
    key_indicators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "category": self.category.value,
            "confidence": self.confidence,
            "subtype": self.subtype,
            "key_indicators": self.key_indicators,
            "metadata": self.metadata
        }


class LocalLLMClassifier:
    """
    Document classifier using local LLM (Ollama).
    Classifies documents based on content analysis.
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    CLASSIFICATION_PROMPT = """You are a document classification expert for construction industry documents.

Analyze the following document text and classify it into ONE of these types:
- invoice: Billing document with line items, amounts, vendor info
- receipt: Proof of payment, typically shorter than invoice
- contract: Legal agreement with terms, parties, signatures
- change_order: Modification to existing contract
- safety_report: Incident reports, safety inspections, violations
- daily_report: Daily construction activity log
- blueprint: Technical drawings, architectural plans
- specification: Technical requirements, material specs
- submittal: Product data, samples, shop drawings for approval
- rfi: Request for Information, questions about project
- rfq: Request for Quote, asking for pricing
- permit: Government permits, licenses, approvals
- meeting_minutes: Notes from project meetings
- correspondence: General emails, letters, memos

Document Text (first 2000 characters):
{text}

Respond with ONLY this JSON format:
{{
  "document_type": "one_of_the_types_above",
  "category": "financial|legal|technical|safety|administrative|communication|other",
  "confidence": 0.0_to_1.0,
  "subtype": "optional_more_specific_type",
  "key_indicators": ["word1", "word2", "phrase3"],
  "reasoning": "brief explanation"
}}

If uncertain, use "unknown" for document_type and explain why."""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
        self.ocr = EnhancedOCR()
    
    async def _call_llm(self, prompt: str, temperature: float = 0.1) -> str:
        """Call local LLM via Ollama API."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for LLM classification")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "format": "json"
                }
                
                async with session.post(self.OLLAMA_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"Ollama API error: {resp.status}")
                        return ""
                        
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""
    
    async def classify_text(self, text: str) -> ClassificationResult:
        """
        Classify document from extracted text.
        
        Args:
            text: Document text content
        
        Returns:
            Classification result
        """
        # Truncate text for prompt
        truncated = text[:2000] if len(text) > 2000 else text
        
        prompt = self.CLASSIFICATION_PROMPT.format(text=truncated)
        
        try:
            response = await self._call_llm(prompt)
            data = json.loads(response)
            
            # Parse document type
            doc_type_str = data.get("document_type", "unknown").lower()
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.UNKNOWN
            
            # Parse category
            cat_str = data.get("category", "other").lower()
            try:
                category = DocumentCategory(cat_str)
            except ValueError:
                category = DocumentCategory.OTHER
            
            return ClassificationResult(
                document_type=doc_type,
                category=category,
                confidence=float(data.get("confidence", 0.5)),
                subtype=data.get("subtype"),
                key_indicators=data.get("key_indicators", []),
                metadata={"reasoning": data.get("reasoning", "")}
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                category=DocumentCategory.OTHER,
                confidence=0.0,
                metadata={"error": "Parse failed"}
            )
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                category=DocumentCategory.OTHER,
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    async def classify_document(
        self,
        file_data: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Classify document from file.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
        
        Returns:
            Classification result with metadata
        """
        import time
        start_time = time.time()
        
        # Step 1: OCR
        is_pdf = filename.lower().endswith('.pdf')
        
        try:
            if is_pdf:
                ocr_result = await self.ocr.process_pdf(file_data)
            else:
                ocr_result = await self.ocr.process_image(file_data)
            
            # Step 2: Classify
            classification = await self.classify_text(ocr_result.text)
            
            processing_time = time.time() - start_time
            
            return {
                "filename": filename,
                "document_type": classification.document_type.value,
                "category": classification.category.value,
                "confidence": classification.confidence,
                "subtype": classification.subtype,
                "key_indicators": classification.key_indicators,
                "ocr_confidence": ocr_result.confidence,
                "word_count": ocr_result.word_count,
                "page_count": ocr_result.page_count,
                "processing_time": processing_time,
                "method": "llm",
                "reasoning": classification.metadata.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return {
                "filename": filename,
                "document_type": DocumentType.UNKNOWN.value,
                "category": DocumentCategory.OTHER.value,
                "confidence": 0.0,
                "error": str(e),
                "processing_time": time.time() - start_time
            }


class RuleBasedClassifier:
    """
    Fallback rule-based classifier using keyword patterns.
    """
    
    KEYWORDS = {
        DocumentType.INVOICE: {
            "category": DocumentCategory.FINANCIAL,
            "keywords": ["invoice", "bill", "payment due", "total amount", "line item", "qty", "unit price"]
        },
        DocumentType.RECEIPT: {
            "category": DocumentCategory.FINANCIAL,
            "keywords": ["receipt", "paid", "payment received", "thank you for your purchase"]
        },
        DocumentType.CONTRACT: {
            "category": DocumentCategory.LEGAL,
            "keywords": ["contract", "agreement", "terms and conditions", "party of the first part", "hereby"]
        },
        DocumentType.CHANGE_ORDER: {
            "category": DocumentCategory.LEGAL,
            "keywords": ["change order", "modification", "amendment", "revised scope"]
        },
        DocumentType.SAFETY_REPORT: {
            "category": DocumentCategory.SAFETY,
            "keywords": ["safety", "incident", "accident", "injury", "osha", "violation", "hazard"]
        },
        DocumentType.DAILY_REPORT: {
            "category": DocumentCategory.ADMINISTRATIVE,
            "keywords": ["daily report", "daily log", "work performed today", "weather conditions"]
        },
        DocumentType.BLUEPRINT: {
            "category": DocumentCategory.TECHNICAL,
            "keywords": ["drawing", "plan", "elevation", "section", "detail", "scale", "dimension"]
        },
        DocumentType.SPECIFICATION: {
            "category": DocumentCategory.TECHNICAL,
            "keywords": ["specification", "spec", "section", "material", "product", "compliance"]
        },
        DocumentType.SUBMITTAL: {
            "category": DocumentCategory.TECHNICAL,
            "keywords": ["submittal", "shop drawing", "product data", "sample", "for approval"]
        },
        DocumentType.RFI: {
            "category": DocumentCategory.COMMUNICATION,
            "keywords": ["rfi", "request for information", "question", "clarification needed"]
        },
        DocumentType.RFQ: {
            "category": DocumentCategory.COMMUNICATION,
            "keywords": ["rfq", "request for quote", "pricing", "bid", "proposal"]
        },
        DocumentType.PERMIT: {
            "category": DocumentCategory.ADMINISTRATIVE,
            "keywords": ["permit", "license", "approval", "building department", "authority"]
        },
        DocumentType.MEETING_MINUTES: {
            "category": DocumentCategory.COMMUNICATION,
            "keywords": ["meeting minutes", "meeting notes", "attendees", "action items", "discussed"]
        },
        DocumentType.CORRESPONDENCE: {
            "category": DocumentCategory.COMMUNICATION,
            "keywords": ["dear", "sincerely", "regards", "email", "letter", "memo"]
        }
    }
    
    def classify_text(self, text: str) -> ClassificationResult:
        """Classify based on keyword matching."""
        text_lower = text.lower()
        
        scores = {}
        matched_keywords = {}
        
        for doc_type, info in self.KEYWORDS.items():
            score = 0
            keywords = []
            
            for keyword in info["keywords"]:
                if keyword in text_lower:
                    score += 1
                    keywords.append(keyword)
            
            # Normalize by number of keywords
            if info["keywords"]:
                scores[doc_type] = score / len(info["keywords"])
                matched_keywords[doc_type] = keywords
        
        if not scores:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                category=DocumentCategory.OTHER,
                confidence=0.0
            )
        
        # Get best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Scale confidence (0.3+ is good match)
        confidence = min(best_score * 3, 1.0)
        
        return ClassificationResult(
            document_type=best_type,
            category=self.KEYWORDS[best_type]["category"],
            confidence=confidence,
            key_indicators=matched_keywords.get(best_type, [])[:5]
        )


class DocumentClassificationPipeline:
    """
    Main pipeline for document classification.
    Uses LLM first, falls back to rule-based.
    """
    
    def __init__(self, use_llm: bool = True, model: str = "gemma3:270m"):
        self.use_llm = use_llm
        self.llm_classifier = LocalLLMClassifier(model) if use_llm else None
        self.rule_classifier = RuleBasedClassifier()
        self.ocr = EnhancedOCR()
    
    async def classify(
        self,
        file_data: bytes,
        filename: str,
        use_llm: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Classify document.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            use_llm: Override LLM usage
        
        Returns:
            Classification result
        """
        use_llm = use_llm if use_llm is not None else self.use_llm
        
        # Try LLM first
        if use_llm and self.llm_classifier:
            try:
                result = await self.llm_classifier.classify_document(file_data, filename)
                if result.get("confidence", 0) >= 0.5:
                    return result
            except Exception as e:
                logger.warning(f"LLM classification failed, using fallback: {e}")
        
        # Fallback to rule-based
        import time
        start_time = time.time()
        
        try:
            is_pdf = filename.lower().endswith('.pdf')
            if is_pdf:
                ocr_result = await self.ocr.process_pdf(file_data)
            else:
                ocr_result = await self.ocr.process_image(file_data)
            
            classification = self.rule_classifier.classify_text(ocr_result.text)
            
            return {
                "filename": filename,
                "document_type": classification.document_type.value,
                "category": classification.category.value,
                "confidence": classification.confidence,
                "key_indicators": classification.key_indicators,
                "ocr_confidence": ocr_result.confidence,
                "word_count": ocr_result.word_count,
                "page_count": ocr_result.page_count,
                "processing_time": time.time() - start_time,
                "method": "rule_based"
            }
            
        except Exception as e:
            logger.error(f"Rule-based classification failed: {e}")
            return {
                "filename": filename,
                "document_type": DocumentType.UNKNOWN.value,
                "category": DocumentCategory.OTHER.value,
                "confidence": 0.0,
                "error": str(e)
            }


# Convenience function
async def classify_document(
    file_data: bytes,
    filename: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Classify a document.
    
    Args:
        file_data: Raw file bytes
        filename: Original filename
        use_llm: Whether to use LLM classification
    
    Returns:
        Classification result
    """
    pipeline = DocumentClassificationPipeline(use_llm=use_llm)
    return await pipeline.classify(file_data, filename)


# Backward compatibility
classify = classify_document
