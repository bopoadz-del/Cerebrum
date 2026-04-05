"""
Enhanced Document Extraction Pipeline
Extracts structured data from invoices, receipts, and construction documents using local LLM.
"""

import json
import re
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

from app.core.logging import get_logger
from app.pipelines.ocr import EnhancedOCR, OCRResult

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = get_logger(__name__)


class DocumentType(Enum):
    """Supported document types for extraction."""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    SAFETY_REPORT = "safety_report"
    BLUEPRINT = "blueprint"
    RFI = "rfi"
    SUBMITTAL = "submittal"
    UNKNOWN = "unknown"


@dataclass
class InvoiceLineItem:
    """Single line item from invoice."""
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total": self.total
        }


@dataclass
class InvoiceData:
    """Structured invoice data."""
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: str = "USD"
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor_name": self.vendor_name,
            "vendor_address": self.vendor_address,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "due_date": self.due_date,
            "total_amount": self.total_amount,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "currency": self.currency,
            "line_items": [item.to_dict() for item in self.line_items],
            "confidence": self.confidence
        }


class LocalLLMExtractor:
    """
    Extract structured data from documents using local LLM (Ollama).
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    # Extraction prompts for different document types
    INVOICE_PROMPT = """You are a document analysis expert. Extract structured data from this invoice text.

Extract the following fields in JSON format:
- vendor_name: Company name issuing the invoice
- vendor_address: Full address of the vendor
- invoice_number: The invoice identifier/number
- invoice_date: Date of the invoice (ISO format YYYY-MM-DD if possible)
- due_date: Payment due date (ISO format YYYY-MM-DD if possible)
- total_amount: Total amount due (numeric only)
- subtotal: Amount before tax (numeric only)
- tax_amount: Tax amount (numeric only)
- currency: Currency code (USD, EUR, SAR, etc.)
- line_items: Array of items with description, quantity, unit, unit_price, total

Invoice Text:
{text}

Respond ONLY with valid JSON. If a field is not found, use null. Example:
{
  "vendor_name": "ABC Construction",
  "invoice_number": "INV-001",
  "total_amount": 1500.00,
  "line_items": [...]
}"""

    CONTRACT_PROMPT = """You are a document analysis expert. Extract structured data from this contract text.

Extract the following fields in JSON format:
- contract_number: Contract identifier
- contract_date: Date signed
- parties: Array of party names with their roles
- project_name: Name of the project
- contract_value: Total contract value (numeric)
- start_date: Project start date
- end_date: Project completion date
- payment_terms: Payment schedule/terms
- key_clauses: Array of important clauses

Contract Text:
{text}

Respond ONLY with valid JSON."""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
        self.ocr = EnhancedOCR()
    
    async def _call_llm(self, prompt: str, temperature: float = 0.1) -> str:
        """Call local LLM via Ollama API."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for LLM extraction")
        
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
    
    async def extract_invoice(self, text: str) -> InvoiceData:
        """
        Extract structured invoice data using local LLM.
        
        Args:
            text: Raw text from invoice
        
        Returns:
            InvoiceData with extracted fields
        """
        prompt = self.INVOICE_PROMPT.format(text=text[:4000])  # Limit text length
        
        try:
            response = await self._call_llm(prompt)
            
            # Parse JSON response
            data = json.loads(response)
            
            # Parse line items
            line_items = []
            for item in data.get("line_items", []):
                line_items.append(InvoiceLineItem(
                    description=item.get("description", ""),
                    quantity=self._parse_number(item.get("quantity")),
                    unit=item.get("unit"),
                    unit_price=self._parse_number(item.get("unit_price")),
                    total=self._parse_number(item.get("total"))
                ))
            
            return InvoiceData(
                vendor_name=data.get("vendor_name"),
                vendor_address=data.get("vendor_address"),
                invoice_number=data.get("invoice_number"),
                invoice_date=self._normalize_date(data.get("invoice_date")),
                due_date=self._normalize_date(data.get("due_date")),
                total_amount=self._parse_number(data.get("total_amount")),
                subtotal=self._parse_number(data.get("subtotal")),
                tax_amount=self._parse_number(data.get("tax_amount")),
                currency=data.get("currency", "USD"),
                line_items=line_items,
                raw_text=text,
                confidence=0.85 if data.get("vendor_name") and data.get("total_amount") else 0.5
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return InvoiceData(raw_text=text, confidence=0.0)
        except Exception as e:
            logger.error(f"Invoice extraction failed: {e}")
            return InvoiceData(raw_text=text, confidence=0.0)
    
    async def extract_from_image(
        self,
        image_data: bytes,
        doc_type: DocumentType = DocumentType.INVOICE
    ) -> Dict[str, Any]:
        """
        Extract data from image using OCR + LLM.
        
        Args:
            image_data: Raw image bytes
            doc_type: Type of document
        
        Returns:
            Extracted structured data
        """
        # Step 1: OCR
        ocr_result = await self.ocr.process_image(image_data)
        
        # Step 2: Extract based on document type
        if doc_type == DocumentType.INVOICE:
            invoice_data = await self.extract_invoice(ocr_result.text)
            return {
                "document_type": doc_type.value,
                "ocr_confidence": ocr_result.confidence,
                "extraction": invoice_data.to_dict(),
                "raw_text": ocr_result.text
            }
        else:
            return {
                "document_type": doc_type.value,
                "ocr_confidence": ocr_result.confidence,
                "raw_text": ocr_result.text
            }
    
    async def extract_from_pdf(
        self,
        pdf_data: bytes,
        doc_type: DocumentType = DocumentType.INVOICE
    ) -> Dict[str, Any]:
        """
        Extract data from PDF using OCR + LLM.
        
        Args:
            pdf_data: Raw PDF bytes
            doc_type: Type of document
        
        Returns:
            Extracted structured data
        """
        # Step 1: OCR
        ocr_result = await self.ocr.process_pdf(pdf_data)
        
        # Step 2: Extract based on document type
        if doc_type == DocumentType.INVOICE:
            invoice_data = await self.extract_invoice(ocr_result.text)
            return {
                "document_type": doc_type.value,
                "ocr_confidence": ocr_result.confidence,
                "extraction": invoice_data.to_dict(),
                "page_count": ocr_result.page_count,
                "raw_text": ocr_result.text
            }
        else:
            return {
                "document_type": doc_type.value,
                "ocr_confidence": ocr_result.confidence,
                "page_count": ocr_result.page_count,
                "raw_text": ocr_result.text
            }
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse numeric value, removing currency symbols and commas."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove currency symbols, commas, whitespace
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """Normalize date to ISO format."""
        if not date_str:
            return None
        
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y"
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If already ISO format or unrecognized, return as-is
        return date_str if isinstance(date_str, str) else None


class RuleBasedExtractor:
    """
    Fallback rule-based extractor for when LLM is unavailable.
    Uses regex patterns for common invoice fields.
    """
    
    PATTERNS = {
        "invoice_number": [
            r'(?:invoice|inv|bill)[\s#:]*(\w{3,20})',
            r'(?:inv\.?|invoice)\s*#?\s*[:\-]?\s*(\w{3,20})',
        ],
        "date": [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        ],
        "amount": [
            r'(?:total|amount|due)[:\s]*[$€£]?\s*([\d,]+\.?\d*)',
            r'(?:balance|payment)[:\s]*[$€£]?\s*([\d,]+\.?\d*)',
        ],
        "vendor": [
            r'(?:from|vendor|billed by)[:\s]*\n?([^\n]{3,50})',
        ]
    }
    
    def extract_invoice(self, text: str) -> InvoiceData:
        """Extract invoice data using regex patterns."""
        data = InvoiceData(raw_text=text)
        
        # Extract invoice number
        for pattern in self.PATTERNS["invoice_number"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data.invoice_number = match.group(1).strip()
                break
        
        # Extract dates (first is invoice date, second is due date if present)
        dates = []
        for pattern in self.PATTERNS["date"]:
            for match in re.finditer(pattern, text):
                date_str = match.group(1)
                normalized = self._try_normalize_date(date_str)
                if normalized and normalized not in dates:
                    dates.append(normalized)
        
        if len(dates) >= 1:
            data.invoice_date = dates[0]
        if len(dates) >= 2:
            data.due_date = dates[1]
        
        # Extract amount
        for pattern in self.PATTERNS["amount"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    data.total_amount = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Extract vendor
        for pattern in self.PATTERNS["vendor"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data.vendor_name = match.group(1).strip()
                break
        
        # Calculate confidence based on how many fields were found
        fields_found = sum([
            1 for f in [data.invoice_number, data.invoice_date, 
                       data.total_amount, data.vendor_name] if f
        ])
        data.confidence = fields_found / 4.0
        
        return data
    
    def _try_normalize_date(self, date_str: str) -> Optional[str]:
        """Try to normalize date string."""
        formats = ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str


class DocumentExtractionPipeline:
    """
    Main pipeline for document extraction.
    Combines OCR, LLM extraction, and rule-based fallback.
    """
    
    def __init__(self, use_llm: bool = True, model: str = "gemma3:270m"):
        self.use_llm = use_llm
        self.llm_extractor = LocalLLMExtractor(model) if use_llm else None
        self.rule_extractor = RuleBasedExtractor()
        self.ocr = EnhancedOCR()
    
    async def extract_document(
        self,
        file_data: bytes,
        filename: str,
        doc_type: Optional[DocumentType] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from document.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            doc_type: Document type (auto-detected if None)
        
        Returns:
            Extracted structured data
        """
        # Detect document type if not specified
        if doc_type is None:
            doc_type = self._detect_document_type(filename)
        
        # Determine if PDF or image
        is_pdf = filename.lower().endswith('.pdf')
        
        try:
            # Try LLM extraction first if available
            if self.use_llm and self.llm_extractor:
                if is_pdf:
                    result = await self.llm_extractor.extract_from_pdf(file_data, doc_type)
                else:
                    result = await self.llm_extractor.extract_from_image(file_data, doc_type)
                
                # Check confidence
                extraction = result.get("extraction", {})
                confidence = extraction.get("confidence", 0)
                
                if confidence >= 0.5:
                    result["extraction_method"] = "llm"
                    return result
            
            # Fallback to rule-based
            if is_pdf:
                ocr_result = await self.ocr.process_pdf(file_data)
            else:
                ocr_result = await self.ocr.process_image(file_data)
            
            if doc_type == DocumentType.INVOICE:
                invoice_data = self.rule_extractor.extract_invoice(ocr_result.text)
                return {
                    "document_type": doc_type.value,
                    "extraction_method": "rule_based",
                    "ocr_confidence": ocr_result.confidence,
                    "extraction": invoice_data.to_dict(),
                    "page_count": getattr(ocr_result, 'page_count', 1),
                    "raw_text": ocr_result.text
                }
            else:
                return {
                    "document_type": doc_type.value,
                    "extraction_method": "ocr_only",
                    "ocr_confidence": ocr_result.confidence,
                    "page_count": getattr(ocr_result, 'page_count', 1),
                    "raw_text": ocr_result.text
                }
                
        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            return {
                "document_type": doc_type.value if doc_type else "unknown",
                "extraction_method": "failed",
                "error": str(e)
            }
    
    def _detect_document_type(self, filename: str) -> DocumentType:
        """Detect document type from filename."""
        fname_lower = filename.lower()
        
        if any(word in fname_lower for word in ['invoice', 'inv', 'bill']):
            return DocumentType.INVOICE
        elif any(word in fname_lower for word in ['receipt', 'rec', 'payment']):
            return DocumentType.RECEIPT
        elif any(word in fname_lower for word in ['contract', 'agreement']):
            return DocumentType.CONTRACT
        elif any(word in fname_lower for word in ['safety', 'incident']):
            return DocumentType.SAFETY_REPORT
        elif any(word in fname_lower for word in ['blueprint', 'drawing', 'plan']):
            return DocumentType.BLUEPRINT
        elif any(word in fname_lower for word in ['rfi', 'inquiry']):
            return DocumentType.RFI
        elif any(word in fname_lower for word in ['submittal', 'submittal']):
            return DocumentType.SUBMITTAL
        else:
            return DocumentType.UNKNOWN


# Convenience function
async def extract_document_data(
    file_data: bytes,
    filename: str,
    doc_type: Optional[str] = None,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Extract structured data from document.
    
    Args:
        file_data: Raw file bytes
        filename: Original filename
        doc_type: Document type (invoice, receipt, contract, etc.)
        use_llm: Whether to use LLM extraction
    
    Returns:
        Extracted structured data
    """
    pipeline = DocumentExtractionPipeline(use_llm=use_llm)
    
    doc_type_enum = None
    if doc_type:
        try:
            doc_type_enum = DocumentType(doc_type.lower())
        except ValueError:
            pass
    
    return await pipeline.extract_document(file_data, filename, doc_type_enum)
