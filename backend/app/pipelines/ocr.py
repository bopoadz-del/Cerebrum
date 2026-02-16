"""
OCR Pipeline with Tesseract Integration
Extracts text from images and PDFs using Tesseract OCR.
"""

import io
import re
from typing import Optional, Dict, List, Any, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
import asyncio

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class OCRLanguage(Enum):
    """Supported OCR languages."""
    ENGLISH = "eng"
    SPANISH = "spa"
    FRENCH = "fra"
    GERMAN = "deu"
    CHINESE_SIMPLIFIED = "chi_sim"
    CHINESE_TRADITIONAL = "chi_tra"
    JAPANESE = "jpn"
    KOREAN = "kor"
    ARABIC = "ara"
    RUSSIAN = "rus"


class OCRMode(Enum):
    """OCR processing modes."""
    STANDARD = "standard"
    FAST = "fast"
    ACCURATE = "accurate"
    TABLE = "table"
    HANDWRITING = "handwriting"


@dataclass
class OCRBlock:
    """A block of recognized text with position."""
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    block_num: int
    par_num: int
    line_num: int
    word_num: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height
            },
            "block_num": self.block_num,
            "par_num": self.par_num,
            "line_num": self.line_num,
            "word_num": self.word_num
        }


@dataclass
class OCRResult:
    """Result of OCR processing."""
    text: str
    blocks: List[OCRBlock]
    confidence: float
    language: str
    processing_time: float
    page_count: int = 1
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "processing_time": self.processing_time,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "blocks": [b.to_dict() for b in self.blocks],
            "metadata": self.metadata
        }


class TesseractOCR:
    """
    Tesseract OCR processor with advanced features.
    Supports multiple languages, preprocessing, and structured output.
    """
    
    # Tesseract config presets
    CONFIGS = {
        OCRMode.STANDARD: '--psm 6',  # Assume uniform block of text
        OCRMode.FAST: '--psm 6 --oem 1',  # LSTM only, faster
        OCRMode.ACCURATE: '--psm 6 --oem 3',  # Default, most accurate
        OCRMode.TABLE: '--psm 6',  # For table extraction
        OCRMode.HANDWRITING: '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvw'
    }
    
    def __init__(self):
        if not TESSERACT_AVAILABLE:
            raise ImportError("Tesseract and pytesseract are required for OCR")
        
        # Set tesseract path if configured
        if hasattr(settings, 'TESSERACT_CMD'):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    
    async def process_image(
        self,
        image_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD,
        preprocess: bool = True
    ) -> OCRResult:
        """
        Process an image with OCR.
        
        Args:
            image_data: Raw image bytes
            language: OCR language
            mode: Processing mode
            preprocess: Whether to apply image preprocessing
        
        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess if requested
            if preprocess:
                image = await self._preprocess_image(image)
            
            # Get OCR config
            config = self.CONFIGS.get(mode, self.CONFIGS[OCRMode.STANDARD])
            
            # Perform OCR with detailed output
            data = pytesseract.image_to_data(
                image,
                lang=language.value,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Parse results
            blocks = []
            full_text_parts = []
            confidences = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:  # Filter low confidence
                    text = data['text'][i].strip()
                    if text:
                        confidence = float(data['conf'][i])
                        block = OCRBlock(
                            text=text,
                            confidence=confidence,
                            x=data['left'][i],
                            y=data['top'][i],
                            width=data['width'][i],
                            height=data['height'][i],
                            block_num=data['block_num'][i],
                            par_num=data['par_num'][i],
                            line_num=data['line_num'][i],
                            word_num=data['word_num'][i]
                        )
                        blocks.append(block)
                        full_text_parts.append(text)
                        confidences.append(confidence)
            
            # Calculate overall confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Join text with proper spacing
            full_text = self._reconstruct_text(blocks)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=full_text,
                blocks=blocks,
                confidence=avg_confidence,
                language=language.value,
                processing_time=processing_time,
                word_count=len(full_text.split())
            )
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise
    
    async def process_pdf(
        self,
        pdf_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD,
        dpi: int = 300
    ) -> OCRResult:
        """
        Process a PDF with OCR.
        
        Args:
            pdf_data: Raw PDF bytes
            language: OCR language
            mode: Processing mode
            dpi: Resolution for PDF to image conversion
        
        Returns:
            OCRResult with combined text from all pages
        """
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image is required for PDF OCR")
        
        import time
        start_time = time.time()
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_bytes(pdf_data, dpi=dpi)
            
            all_blocks = []
            all_texts = []
            all_confidences = []
            
            # Process each page
            for page_num, image in enumerate(images):
                logger.info(f"Processing page {page_num + 1}/{len(images)}")
                
                # Convert PIL to bytes
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='PNG')
                img_data = img_buffer.getvalue()
                
                # Process page
                result = await self.process_image(img_data, language, mode)
                
                all_blocks.extend(result.blocks)
                all_texts.append(result.text)
                all_confidences.append(result.confidence)
            
            # Combine results
            full_text = '\n\n'.join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=full_text,
                blocks=all_blocks,
                confidence=avg_confidence,
                language=language.value,
                processing_time=processing_time,
                page_count=len(images),
                word_count=len(full_text.split())
            )
            
        except Exception as e:
            logger.error(f"PDF OCR processing failed: {e}")
            raise
    
    async def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: PIL Image
        
        Returns:
            Preprocessed image
        """
        if not CV2_AVAILABLE:
            return image
        
        try:
            # Convert PIL to OpenCV format
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Adaptive thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL
            return Image.fromarray(binary)
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
    
    def _reconstruct_text(self, blocks: List[OCRBlock]) -> str:
        """
        Reconstruct text from OCR blocks with proper spacing.
        
        Args:
            blocks: List of OCR blocks
        
        Returns:
            Reconstructed text
        """
        if not blocks:
            return ""
        
        # Sort blocks by position
        sorted_blocks = sorted(blocks, key=lambda b: (b.block_num, b.par_num, b.line_num, b.word_num))
        
        lines = []
        current_line = []
        current_line_num = sorted_blocks[0].line_num
        
        for block in sorted_blocks:
            if block.line_num != current_line_num:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [block.text]
                current_line_num = block.line_num
            else:
                current_line.append(block.text)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    async def extract_table(
        self,
        image_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH
    ) -> List[List[str]]:
        """
        Extract table structure from image.
        
        Args:
            image_data: Raw image bytes
            language: OCR language
        
        Returns:
            2D list representing table cells
        """
        try:
            # Load and preprocess image
            image = Image.open(io.BytesIO(image_data))
            
            if CV2_AVAILABLE:
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
                
                # Detect table structure using line detection
                binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                
                # Find horizontal and vertical lines
                horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
                vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
                
                horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
                vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
                
                # Combine lines
                table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Use OCR with table mode
            result = await self.process_image(image_data, language, OCRMode.TABLE)
            
            # Simple table extraction - split by newlines and whitespace
            lines = result.text.strip().split('\n')
            table = [line.split() for line in lines if line.strip()]
            
            return table
            
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return []


class OCRPipeline:
    """Pipeline for batch OCR processing."""
    
    def __init__(self):
        self.ocr = TesseractOCR()
    
    async def process_batch(
        self,
        files: List[Tuple[str, bytes]],
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, OCRResult]:
        """
        Process multiple files with OCR.
        
        Args:
            files: List of (filename, data) tuples
            language: OCR language
            mode: Processing mode
            progress_callback: Optional callback(current, total)
        
        Returns:
            Dictionary mapping filenames to OCR results
        """
        results = {}
        
        for i, (filename, data) in enumerate(files):
            try:
                # Determine file type
                if filename.lower().endswith('.pdf'):
                    result = await self.ocr.process_pdf(data, language, mode)
                else:
                    result = await self.ocr.process_image(data, language, mode)
                
                results[filename] = result
                
                if progress_callback:
                    progress_callback(i + 1, len(files))
                    
            except Exception as e:
                logger.error(f"Failed to process {filename}: {e}")
                results[filename] = OCRResult(
                    text="",
                    blocks=[],
                    confidence=0,
                    language=language.value,
                    processing_time=0,
                    metadata={"error": str(e)}
                )
        
        return results


# Convenience function
async def extract_text_from_image(
    image_data: bytes,
    language: str = "eng",
    mode: str = "standard"
) -> OCRResult:
    """
    Extract text from image using OCR.
    
    Args:
        image_data: Raw image bytes
        language: OCR language code
        mode: Processing mode
    
    Returns:
        OCRResult with extracted text
    """
    ocr = TesseractOCR()
    
    lang = OCRLanguage(language) if language in [l.value for l in OCRLanguage] else OCRLanguage.ENGLISH
    proc_mode = OCRMode(mode) if mode in [m.value for m in OCRMode] else OCRMode.STANDARD
    
    result = await ocr.process_image(image_data, lang, proc_mode)
    return result
