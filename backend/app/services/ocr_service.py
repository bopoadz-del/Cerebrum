"""
Enhanced OCR Service with EasyOCR Support
Provides both Tesseract and EasyOCR engines for optimal text extraction.
"""

import io
import asyncio
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
import numpy as np

from app.core.logging import get_logger
from app.pipelines.ocr import (
    TesseractOCR, OCRResult, OCRBlock, OCRLanguage, OCRMode
)

logger = get_logger(__name__)

# EasyOCR availability
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available. Install with: pip install easyocr")

# OpenCV for preprocessing
try:
    import cv2
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class EnhancedOCRResult(OCRResult):
    """Extended OCR result with engine information."""
    engine: str = "tesseract"  # 'tesseract', 'easyocr', or 'combined'
    easyocr_confidence: float = 0.0
    tesseract_confidence: float = 0.0


class EasyOCREngine:
    """EasyOCR wrapper for better handwriting and scene text."""
    
    def __init__(self, languages: List[str] = None, gpu: bool = False):
        if not EASYOCR_AVAILABLE:
            raise ImportError("EasyOCR not installed. Run: pip install easyocr")
        
        self.languages = languages or ['en']
        self.gpu = gpu
        self._reader = None
    
    @property
    def reader(self):
        """Lazy initialization of EasyOCR reader."""
        if self._reader is None:
            logger.info(f"Initializing EasyOCR with languages: {self.languages}")
            self._reader = easyocr.Reader(self.languages, gpu=self.gpu, verbose=False)
        return self._reader
    
    async def process_image(
        self,
        image_data: bytes,
        detail: int = 1
    ) -> OCRResult:
        """
        Process image with EasyOCR.
        
        Args:
            image_data: Raw image bytes
            detail: 0=bbox only, 1=bbox+text, 2=bbox+text+conf
        
        Returns:
            OCRResult with extracted text
        """
        import time
        start_time = time.time()
        
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Run EasyOCR (CPU-intensive, run in thread pool)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: self.reader.readtext(image, detail=detail)
            )
            
            # Parse results
            blocks = []
            texts = []
            confidences = []
            
            for i, (bbox, text, conf) in enumerate(results):
                # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x = int(min(x_coords))
                y = int(min(y_coords))
                width = int(max(x_coords) - x)
                height = int(max(y_coords) - y)
                
                block = OCRBlock(
                    text=text,
                    confidence=float(conf) * 100,  # EasyOCR returns 0-1
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    block_num=i,
                    par_num=0,
                    line_num=i,
                    word_num=0
                )
                blocks.append(block)
                texts.append(text)
                confidences.append(block.confidence)
            
            full_text = '\n'.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=full_text,
                blocks=blocks,
                confidence=avg_confidence,
                language=','.join(self.languages),
                processing_time=processing_time,
                word_count=len(full_text.split()),
                metadata={"engine": "easyocr"}
            )
            
        except Exception as e:
            logger.error(f"EasyOCR processing failed: {e}")
            raise


class EnhancedOCRService:
    """
    Unified OCR service that combines Tesseract and EasyOCR.
    Automatically selects best engine based on content type.
    """
    
    def __init__(self):
        self.tesseract = None
        self.easyocr = None
        self._engines_available = {
            "tesseract": False,
            "easyocr": False
        }
    
    async def initialize(self):
        """Initialize available OCR engines."""
        # Try Tesseract
        try:
            self.tesseract = TesseractOCR()
            self._engines_available["tesseract"] = True
            logger.info("✓ Tesseract OCR initialized")
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
        
        # Try EasyOCR
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr = EasyOCREngine(languages=['en'], gpu=False)
                self._engines_available["easyocr"] = True
                logger.info("✓ EasyOCR initialized")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
    
    @property
    def available_engines(self) -> List[str]:
        """List of available OCR engines."""
        return [k for k, v in self._engines_available.items() if v]
    
    async def process_image(
        self,
        image_data: bytes,
        engine: str = "auto",
        language: str = "eng",
        mode: str = "standard"
    ) -> EnhancedOCRResult:
        """
        Process image with selected OCR engine.
        
        Args:
            image_data: Raw image bytes
            engine: 'tesseract', 'easyocr', 'auto', or 'combined'
            language: OCR language
            mode: Processing mode
        
        Returns:
            EnhancedOCRResult with extracted text
        """
        if not self.available_engines:
            raise RuntimeError("No OCR engines available")
        
        # Auto-select engine
        if engine == "auto":
            engine = self._select_engine(image_data)
        
        # Process with selected engine
        if engine == "tesseract" and self._engines_available["tesseract"]:
            result = await self._process_tesseract(image_data, language, mode)
            return EnhancedOCRResult(**result.to_dict(), engine="tesseract")
        
        elif engine == "easyocr" and self._engines_available["easyocr"]:
            result = await self.easyocr.process_image(image_data)
            return EnhancedOCRResult(**result.to_dict(), engine="easyocr")
        
        elif engine == "combined":
            return await self._process_combined(image_data, language)
        
        else:
            raise ValueError(f"Engine '{engine}' not available. Available: {self.available_engines}")
    
    def _select_engine(self, image_data: bytes) -> str:
        """Auto-select best engine based on image characteristics."""
        # Default to Tesseract for document text
        # Use EasyOCR for potential handwriting or scene text
        if self._engines_available["easyocr"]:
            # Could add image analysis here to detect handwriting/scene text
            return "tesseract"  # Default to Tesseract for reliability
        return "tesseract"
    
    async def _process_tesseract(
        self, 
        image_data: bytes, 
        language: str, 
        mode: str
    ) -> OCRResult:
        """Process with Tesseract."""
        lang = OCRLanguage(language) if language in [l.value for l in OCRLanguage] else OCRLanguage.ENGLISH
        proc_mode = OCRMode(mode) if mode in [m.value for m in OCRMode] else OCRMode.STANDARD
        
        return await self.tesseract.process_image(image_data, lang, proc_mode)
    
    async def _process_combined(
        self,
        image_data: bytes,
        language: str
    ) -> EnhancedOCRResult:
        """
        Process with both engines and combine results.
        Uses best confidence result.
        """
        results = {}
        
        # Run both engines
        if self._engines_available["tesseract"]:
            try:
                results["tesseract"] = await self._process_tesseract(
                    image_data, language, "accurate"
                )
            except Exception as e:
                logger.warning(f"Tesseract failed in combined mode: {e}")
        
        if self._engines_available["easyocr"]:
            try:
                results["easyocr"] = await self.easyocr.process_image(image_data)
            except Exception as e:
                logger.warning(f"EasyOCR failed in combined mode: {e}")
        
        if not results:
            raise RuntimeError("Both OCR engines failed")
        
        # Select best result by confidence
        best_engine = max(results.keys(), key=lambda k: results[k].confidence)
        best_result = results[best_engine]
        
        return EnhancedOCRResult(
            **best_result.to_dict(),
            engine="combined",
            tesseract_confidence=results.get("tesseract", OCRResult(
                text="", blocks=[], confidence=0, language="", processing_time=0
            )).confidence,
            easyocr_confidence=results.get("easyocr", OCRResult(
                text="", blocks=[], confidence=0, language="", processing_time=0
            )).confidence
        )
    
    async def extract_from_document(
        self,
        file_data: bytes,
        filename: str,
        engine: str = "auto"
    ) -> EnhancedOCRResult:
        """
        Extract text from document (image or PDF).
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            engine: OCR engine to use
        
        Returns:
            EnhancedOCRResult
        """
        if filename.lower().endswith('.pdf'):
            # Use Tesseract for PDFs (better multi-page support)
            if not self._engines_available["tesseract"]:
                raise RuntimeError("Tesseract required for PDF processing")
            
            result = await self.tesseract.process_pdf(file_data)
            return EnhancedOCRResult(**result.to_dict(), engine="tesseract")
        
        else:
            # Use selected engine for images
            return await self.process_image(file_data, engine)


# Global instance
_ocr_service: Optional[EnhancedOCRService] = None


async def get_ocr_service() -> EnhancedOCRService:
    """Get or initialize the OCR service."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = EnhancedOCRService()
        await _ocr_service.initialize()
    return _ocr_service


# Convenience functions
async def extract_text(
    image_data: bytes,
    engine: str = "auto",
    language: str = "eng"
) -> str:
    """
    Simple text extraction.
    
    Args:
        image_data: Raw image bytes
        engine: 'tesseract', 'easyocr', or 'auto'
        language: OCR language
    
    Returns:
        Extracted text
    """
    service = await get_ocr_service()
    result = await service.process_image(image_data, engine, language)
    return result.text


async def extract_text_advanced(
    image_data: bytes,
    engine: str = "combined"
) -> Dict[str, Any]:
    """
    Advanced extraction with metadata.
    
    Args:
        image_data: Raw image bytes
        engine: 'tesseract', 'easyocr', 'combined', or 'auto'
    
    Returns:
        Dict with text, confidence, engine used, and block positions
    """
    service = await get_ocr_service()
    result = await service.process_image(image_data, engine)
    return result.to_dict()
