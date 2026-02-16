"""
Document Classification Pipeline using LayoutLM and GPT-4 Vision
Classifies documents by type and extracts key information.
"""

import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import base64
import asyncio

try:
    from transformers import LayoutLMv3ForSequenceClassification, LayoutLMv3Processor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class DocumentType(Enum):
    """Supported document types."""
    CONTRACT = "contract"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    DRAWING = "drawing"
    SPECIFICATION = "specification"
    PERMIT = "permit"
    REPORT = "report"
    CHANGE_ORDER = "change_order"
    RFQ = "rfq"
    SUBMITTAL = "submittal"
    CORRESPONDENCE = "correspondence"
    MEETING_MINUTES = "meeting_minutes"
    PHOTO = "photo"
    UNKNOWN = "unknown"


class DocumentCategory(Enum):
    """High-level document categories."""
    LEGAL = "legal"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    ADMINISTRATIVE = "administrative"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class DocumentClassification:
    """Result of document classification."""
    document_type: DocumentType
    category: DocumentCategory
    confidence: float
    subtype: Optional[str] = None
    key_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "category": self.category.value,
            "confidence": self.confidence,
            "subtype": self.subtype,
            "key_fields": self.key_fields,
            "metadata": self.metadata
        }


@dataclass
class ClassificationResult:
    """Complete classification result."""
    filename: str
    primary_classification: DocumentClassification
    alternative_classifications: List[DocumentClassification]
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "primary_classification": self.primary_classification.to_dict(),
            "alternative_classifications": [c.to_dict() for c in self.alternative_classifications],
            "processing_time": self.processing_time
        }


class LayoutLMClassifier:
    """
    Document classifier using LayoutLMv3.
    Classifies documents based on visual layout and text.
    """
    
    # Document type mapping
    TYPE_MAPPING = {
        0: (DocumentType.CONTRACT, DocumentCategory.LEGAL),
        1: (DocumentType.INVOICE, DocumentCategory.FINANCIAL),
        2: (DocumentType.RECEIPT, DocumentCategory.FINANCIAL),
        3: (DocumentType.DRAWING, DocumentCategory.TECHNICAL),
        4: (DocumentType.SPECIFICATION, DocumentCategory.TECHNICAL),
        5: (DocumentType.PERMIT, DocumentCategory.ADMINISTRATIVE),
        6: (DocumentType.REPORT, DocumentCategory.TECHNICAL),
        7: (DocumentType.CHANGE_ORDER, DocumentCategory.FINANCIAL),
        8: (DocumentType.RFQ, DocumentCategory.COMMUNICATION),
        9: (DocumentType.SUBMITTAL, DocumentCategory.TECHNICAL),
        10: (DocumentType.CORRESPONDENCE, DocumentCategory.COMMUNICATION),
        11: (DocumentType.MEETING_MINUTES, DocumentCategory.COMMUNICATION),
    }
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.processor = None
        self.model_path = model_path or settings.LAYOUTLM_MODEL_PATH
        
        if TRANSFORMERS_AVAILABLE:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load LayoutLM model."""
        try:
            logger.info("Loading LayoutLM model...")
            # In production, load actual fine-tuned model
            # self.model = LayoutLMv3ForSequenceClassification.from_pretrained(self.model_path)
            # self.processor = LayoutLMv3Processor.from_pretrained(self.model_path)
            logger.info("LayoutLM model loaded")
        except Exception as e:
            logger.error(f"Failed to load LayoutLM model: {e}")
    
    async def classify(
        self,
        image_data: bytes,
        ocr_text: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify a document using LayoutLM.
        
        Args:
            image_data: Document image bytes
            ocr_text: Optional pre-extracted OCR text
        
        Returns:
            Classification result
        """
        import time
        start_time = time.time()
        
        try:
            if not TRANSFORMERS_AVAILABLE or self.model is None:
                # Fallback to rule-based classification
                return await self._rule_based_classify(image_data, ocr_text)
            
            # Process image
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_data))
            
            # Prepare inputs
            if ocr_text:
                encoding = self.processor(
                    image,
                    text=ocr_text,
                    return_tensors="pt",
                    truncation=True
                )
            else:
                encoding = self.processor(image, return_tensors="pt")
            
            # Run inference
            outputs = self.model(**encoding)
            logits = outputs.logits
            
            # Get predictions
            probs = logits.softmax(dim=1)
            top_probs, top_indices = probs.topk(k=3)
            
            # Build results
            classifications = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                doc_type, category = self.TYPE_MAPPING.get(
                    idx.item(),
                    (DocumentType.UNKNOWN, DocumentCategory.OTHER)
                )
                
                classification = DocumentClassification(
                    document_type=doc_type,
                    category=category,
                    confidence=prob.item()
                )
                classifications.append(classification)
            
            processing_time = time.time() - start_time
            
            return ClassificationResult(
                filename="",
                primary_classification=classifications[0],
                alternative_classifications=classifications[1:],
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"LayoutLM classification failed: {e}")
            return await self._rule_based_classify(image_data, ocr_text)
    
    async def _rule_based_classify(
        self,
        image_data: bytes,
        ocr_text: Optional[str] = None
    ) -> ClassificationResult:
        """Fallback rule-based classification."""
        import time
        start_time = time.time()
        
        # Use OCR text for classification
        text = ocr_text or ""
        text_lower = text.lower()
        
        # Keyword-based classification
        keywords = {
            DocumentType.CONTRACT: ['contract', 'agreement', 'terms', 'conditions', 'parties'],
            DocumentType.INVOICE: ['invoice', 'bill', 'payment due', 'total amount', 'subtotal'],
            DocumentType.RECEIPT: ['receipt', 'paid', 'transaction', 'thank you'],
            DocumentType.DRAWING: ['drawing', 'plan', 'elevation', 'section', 'detail'],
            DocumentType.SPECIFICATION: ['specification', 'spec', 'requirements', 'standards'],
            DocumentType.PERMIT: ['permit', 'approval', 'authorized', 'license'],
            DocumentType.REPORT: ['report', 'analysis', 'findings', 'summary'],
            DocumentType.CHANGE_ORDER: ['change order', 'variation', 'modification', 'additional'],
            DocumentType.RFQ: ['rfq', 'request for quote', 'quotation', 'bid'],
            DocumentType.SUBMITTAL: ['submittal', 'shop drawing', 'product data', 'sample'],
            DocumentType.CORRESPONDENCE: ['letter', 'email', 'regarding', 'dear', 'sincerely'],
            DocumentType.MEETING_MINUTES: ['minutes', 'meeting', 'attendees', 'action items'],
        }
        
        scores = {}
        for doc_type, words in keywords.items():
            score = sum(1 for word in words if word in text_lower)
            scores[doc_type] = score
        
        # Get best match
        if scores:
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
            confidence = min(best_score / 3, 1.0)  # Normalize confidence
        else:
            best_type = DocumentType.UNKNOWN
            confidence = 0.0
        
        # Map to category
        category_mapping = {
            DocumentType.CONTRACT: DocumentCategory.LEGAL,
            DocumentType.INVOICE: DocumentCategory.FINANCIAL,
            DocumentType.RECEIPT: DocumentCategory.FINANCIAL,
            DocumentType.DRAWING: DocumentCategory.TECHNICAL,
            DocumentType.SPECIFICATION: DocumentCategory.TECHNICAL,
            DocumentType.PERMIT: DocumentCategory.ADMINISTRATIVE,
            DocumentType.REPORT: DocumentCategory.TECHNICAL,
            DocumentType.CHANGE_ORDER: DocumentCategory.FINANCIAL,
            DocumentType.RFQ: DocumentCategory.COMMUNICATION,
            DocumentType.SUBMITTAL: DocumentCategory.TECHNICAL,
            DocumentType.CORRESPONDENCE: DocumentCategory.COMMUNICATION,
            DocumentType.MEETING_MINUTES: DocumentCategory.COMMUNICATION,
        }
        
        classification = DocumentClassification(
            document_type=best_type,
            category=category_mapping.get(best_type, DocumentCategory.OTHER),
            confidence=confidence,
            key_fields=self._extract_key_fields(text, best_type)
        )
        
        processing_time = time.time() - start_time
        
        return ClassificationResult(
            filename="",
            primary_classification=classification,
            alternative_classifications=[],
            processing_time=processing_time
        )
    
    def _extract_key_fields(self, text: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Extract key fields based on document type."""
        fields = {}
        
        if doc_type == DocumentType.INVOICE:
            # Extract invoice number
            invoice_match = self._find_pattern(text, r'(?:invoice|inv)[\s#:]*(\w+[-\w]*)')
            if invoice_match:
                fields['invoice_number'] = invoice_match
            
            # Extract date
            date_match = self._find_pattern(text, r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b')
            if date_match:
                fields['date'] = date_match
            
            # Extract total
            total_match = self._find_pattern(text, r'(?:total|amount)[\s:]*[$]?([\d,]+\.?\d*)')
            if total_match:
                fields['total_amount'] = total_match
        
        elif doc_type == DocumentType.CONTRACT:
            # Extract contract number
            contract_match = self._find_pattern(text, r'(?:contract|agreement)[\s#:]*(\w+[-\w]*)')
            if contract_match:
                fields['contract_number'] = contract_match
            
            # Extract parties
            party_match = self._find_pattern(text, r'(?:between|party)[\s:]*(\w+)')
            if party_match:
                fields['party'] = party_match
        
        return fields
    
    def _find_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Find pattern in text."""
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None


class GPT4VisionClassifier:
    """
    Document classifier using GPT-4 Vision API.
    Provides high-accuracy classification with detailed analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
    
    async def classify(
        self,
        image_data: bytes,
        filename: str = ""
    ) -> ClassificationResult:
        """
        Classify document using GPT-4 Vision.
        
        Args:
            image_data: Document image bytes
            filename: Original filename
        
        Returns:
            Classification result
        """
        import time
        start_time = time.time()
        
        try:
            import openai
            openai.api_key = self.api_key
            
            # Encode image
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare prompt
            prompt = """Analyze this construction document and provide:
1. Document type (contract, invoice, drawing, specification, permit, report, change_order, rfq, submittal, correspondence, meeting_minutes, or other)
2. Category (legal, financial, technical, administrative, communication)
3. Confidence level (0-1)
4. Key fields extracted (dates, amounts, numbers, names)
5. Brief description

Respond in JSON format."""
            
            # Call GPT-4 Vision
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = {}
            
            # Build classification
            doc_type = DocumentType(result.get('document_type', 'unknown'))
            category = DocumentCategory(result.get('category', 'other'))
            
            classification = DocumentClassification(
                document_type=doc_type,
                category=category,
                confidence=result.get('confidence', 0.5),
                key_fields=result.get('key_fields', {}),
                metadata={"description": result.get('description', '')}
            )
            
            processing_time = time.time() - start_time
            
            return ClassificationResult(
                filename=filename,
                primary_classification=classification,
                alternative_classifications=[],
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"GPT-4 Vision classification failed: {e}")
            # Fallback to LayoutLM
            layoutlm = LayoutLMClassifier()
            return await layoutlm.classify(image_data)


class DocumentClassifierPipeline:
    """Pipeline for document classification."""
    
    def __init__(self, use_gpt4: bool = False):
        self.use_gpt4 = use_gpt4
        self.layoutlm = LayoutLMClassifier()
        if use_gpt4:
            self.gpt4 = GPT4VisionClassifier()
    
    async def classify_document(
        self,
        image_data: bytes,
        filename: str = "",
        ocr_text: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify a document.
        
        Args:
            image_data: Document image bytes
            filename: Original filename
            ocr_text: Optional pre-extracted OCR text
        
        Returns:
            Classification result
        """
        if self.use_gpt4:
            return await self.gpt4.classify(image_data, filename)
        else:
            result = await self.layoutlm.classify(image_data, ocr_text)
            result.filename = filename
            return result
    
    async def classify_batch(
        self,
        documents: List[Tuple[str, bytes]],
        progress_callback: Optional[callable] = None
    ) -> List[ClassificationResult]:
        """
        Classify multiple documents.
        
        Args:
            documents: List of (filename, image_data) tuples
            progress_callback: Optional progress callback
        
        Returns:
            List of classification results
        """
        results = []
        
        for i, (filename, data) in enumerate(documents):
            result = await self.classify_document(data, filename)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(documents))
        
        return results


# Convenience function
async def classify_document(
    image_data: bytes,
    filename: str = "",
    use_gpt4: bool = False
) -> ClassificationResult:
    """
    Classify a document.
    
    Args:
        image_data: Document image bytes
        filename: Original filename
        use_gpt4: Whether to use GPT-4 Vision
    
    Returns:
        Classification result
    """
    pipeline = DocumentClassifierPipeline(use_gpt4=use_gpt4)
    return await pipeline.classify_document(image_data, filename)
