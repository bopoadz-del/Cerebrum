from PIL import Image
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

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class OCREngine(Enum):
    """Available OCR engines."""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    AUTO = "auto"  # Select best based on content


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
        if hasattr(settings, 'TESSERACT_CMD') and settings.TESSERACT_CMD:
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
            logger.debug(f"Loading image ({len(image_data)} bytes)")
            try:
                image = Image.open(io.BytesIO(image_data))
                logger.debug(f"Image loaded: {image.format}, {image.size}, {image.mode}")
            except Exception as e:
                logger.error(f"Failed to load image: {type(e).__name__}: {e}")
                raise ValueError(f"Invalid image file: {str(e)}")
            
            # Preprocess if requested
            if preprocess:
                logger.debug("Preprocessing image...")
                try:
                    image = await self._preprocess_image(image)
                except Exception as e:
                    logger.warning(f"Image preprocessing failed, continuing with original: {e}")
            
            # Get OCR config
            config = self.CONFIGS.get(mode, self.CONFIGS[OCRMode.STANDARD])
            logger.debug(f"OCR config: {config}, language: {language.value}")
            
            # Perform OCR with detailed output
            try:
                data = pytesseract.image_to_data(
                    image,
                    lang=language.value,
                    config=config,
                    output_type=pytesseract.Output.DICT
                )
            except Exception as e:
                logger.error(f"Tesseract OCR failed: {type(e).__name__}: {e}")
                raise RuntimeError(f"Tesseract OCR error: {str(e)}")
            
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
            logger.info(f"Image OCR completed: {len(full_text.split())} words, {avg_confidence:.1f}% confidence, {processing_time:.2f}s")
            
            return OCRResult(
                text=full_text,
                blocks=blocks,
                confidence=avg_confidence,
                language=language.value,
                processing_time=processing_time,
                word_count=len(full_text.split())
            )
            
        except Exception as e:
            logger.error(f"Image OCR processing failed: {type(e).__name__}: {e}")
            raise
    
    def _validate_pdf(self, pdf_data: bytes) -> Tuple[bool, str]:
        """
        Validate PDF before processing.
        
        Args:
            pdf_data: Raw PDF bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not PYPDF2_AVAILABLE:
            return True, ""  # Skip validation if PyPDF2 not available
            
        try:
            pdf_file = io.BytesIO(pdf_data)
            reader = PyPDF2.PdfReader(pdf_file)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                return False, "PDF is encrypted/password protected"
            
            # Check if PDF has pages
            if len(reader.pages) == 0:
                return False, "PDF has no pages"
            
            # Check if PDF is corrupted by trying to read first page
            try:
                _ = reader.pages[0].extract_text()
            except Exception as e:
                logger.warning(f"PDF first page extraction failed: {e}")
                # Not a hard failure - might still be processable
            
            return True, ""
            
        except PyPDF2.errors.PdfReadError as e:
            return False, f"Invalid or corrupted PDF: {str(e)}"
        except Exception as e:
            return False, f"PDF validation failed: {str(e)}"

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
            raise ImportError("pdf2image is required for PDF OCR. Install with: pip install pdf2image")
        
        # Validate PDF first
        is_valid, error_msg = self._validate_pdf(pdf_data)
        if not is_valid:
            logger.error(f"PDF validation failed: {error_msg}")
            raise ValueError(f"PDF validation failed: {error_msg}")
        
        import time
        start_time = time.time()
        
        try:
            # Convert PDF to images
            logger.info(f"Converting PDF to images (dpi={dpi}, size={len(pdf_data)} bytes)")
            try:
                images = pdf2image.convert_from_bytes(pdf_data, dpi=dpi)
                logger.info(f"PDF converted to {len(images)} images")
            except Exception as e:
                logger.error(f"pdf2image conversion failed: {type(e).__name__}: {e}")
                raise RuntimeError(f"PDF to image conversion failed: {str(e)}")
            
            all_blocks = []
            all_texts = []
            all_confidences = []
            
            # Process each page
            for page_num, image in enumerate(images):
                logger.info(f"Processing page {page_num + 1}/{len(images)}")
                
                try:
                    # Convert PIL to bytes
                    img_buffer = io.BytesIO()
                    image.save(img_buffer, format='PNG')
                    img_data = img_buffer.getvalue()
                    
                    # Process page
                    result = await self.process_image(img_data, language, mode)
                    
                    all_blocks.extend(result.blocks)
                    all_texts.append(result.text)
                    all_confidences.append(result.confidence)
                    logger.debug(f"Page {page_num + 1} processed: {result.word_count} words, {result.confidence:.1f}% confidence")
                except Exception as e:
                    logger.error(f"Failed to process page {page_num + 1}: {type(e).__name__}: {e}")
                    raise RuntimeError(f"OCR failed on page {page_num + 1}: {str(e)}")
            
            # Combine results
            full_text = '\n\n'.join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            processing_time = time.time() - start_time
            logger.info(f"PDF OCR completed: {len(images)} pages, {len(full_text.split())} words, {processing_time:.2f}s")
            
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
            logger.error(f"PDF OCR processing failed: {type(e).__name__}: {e}")
            raise
    
    async def _preprocess_image(self, image: Image.Image, deskew: bool = True) -> Image.Image:
        """
        Preprocess image for better OCR results with deskewing and enhancement.
        
        Args:
            image: PIL Image
            deskew: Whether to apply deskewing
        
        Returns:
            Preprocessed image
        """
        if not CV2_AVAILABLE:
            return image
        
        try:
            # Convert PIL to OpenCV format
            img_array = np.array(image)
            
            # Deskew if requested
            if deskew:
                img_array = await self._deskew_image(img_array)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Enhance contrast with CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # Adaptive thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 15, 10
            )
            
            # Morphological cleanup
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to PIL
            return Image.fromarray(cleaned)
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
    
    async def _deskew_image(self, image) -> Any:
        """
        Deskew image using contour detection.
        
        Args:
            image: OpenCV image array
        
        Returns:
            Deskewed image
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Threshold to binary
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find all contours
            contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            # Find the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[-1]
            
            # Adjust angle
            if angle < -45:
                angle = 90 + angle
            
            # Ignore small angles
            if abs(angle) < 0.5:
                return image
            
            # Rotate image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(255, 255, 255))
            
            logger.info(f"Deskewed image by {angle:.2f} degrees")
            return rotated
            
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
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


class EnhancedOCR:
    """
    Enhanced OCR with multiple engines and advanced preprocessing.
    Supports Tesseract (documents), EasyOCR (handwriting/scene text), and auto-selection.
    """
    
    # Language mapping between Tesseract and EasyOCR
    LANG_MAP = {
        "eng": "en",
        "spa": "es",
        "fra": "fr",
        "deu": "de",
        "chi_sim": "ch_sim",
        "chi_tra": "ch_tra",
        "jpn": "ja",
        "kor": "ko",
        "ara": "ar",
        "rus": "ru"
    }
    
    def __init__(self, default_engine: OCREngine = OCREngine.AUTO):
        self.default_engine = default_engine
        self.tesseract = TesseractOCR() if TESSERACT_AVAILABLE else None
        self._easyocr_reader = None
        
        if not self.tesseract:
            logger.error("Tesseract not available - document OCR will fail")
    
    def _get_easyocr_reader(self, languages: List[str] = None):
        """Lazy initialization of EasyOCR reader."""
        if not EASYOCR_AVAILABLE:
            raise ImportError("EasyOCR not installed")
        
        if self._easyocr_reader is None:
            langs = languages or ['en']
            logger.info(f"Initializing EasyOCR with languages: {langs}")
            self._easyocr_reader = easyocr.Reader(langs, gpu=False)
        
        return self._easyocr_reader
    
    async def _deskew_image(self, image) -> Any:
        """
        Deskew image using contour detection.
        
        Args:
            image: OpenCV image array
        
        Returns:
            Deskewed image
        """
        if not CV2_AVAILABLE:
            return image
        
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Threshold to binary
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find all contours
            contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            # Find the largest contour (likely the text block)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[-1]
            
            # Adjust angle
            if angle < -45:
                angle = 90 + angle
            
            # Ignore small angles
            if abs(angle) < 0.5:
                return image
            
            # Rotate image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(255, 255, 255))
            
            logger.info(f"Deskewed image by {angle:.2f} degrees")
            return rotated
            
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
            return image
    
    async def _enhance_contrast(self, image) -> Any:
        """
        Enhance image contrast using CLAHE.
        
        Args:
            image: OpenCV image array
        
        Returns:
            Enhanced image
        """
        if not CV2_AVAILABLE:
            return image
        
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    async def _preprocess_enhanced(self, image: Image.Image, deskew: bool = True) -> Image.Image:
        """
        Enhanced preprocessing pipeline.
        
        Args:
            image: PIL Image
            deskew: Whether to apply deskewing
        
        Returns:
            Preprocessed PIL Image
        """
        if not CV2_AVAILABLE:
            return image
        
        try:
            # Convert to OpenCV format
            img_array = np.array(image)
            
            # Deskew if requested
            if deskew:
                img_array = await self._deskew_image(img_array)
            
            # Enhance contrast
            enhanced = await self._enhance_contrast(img_array)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # Adaptive thresholding with larger block size for better results
            binary = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 15, 10
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return Image.fromarray(cleaned)
            
        except Exception as e:
            logger.warning(f"Enhanced preprocessing failed: {e}")
            return image
    
    def _detect_content_type(self, image: Image.Image) -> str:
        """
        Detect if image contains printed text or handwriting/scene text.
        
        Args:
            image: PIL Image
        
        Returns:
            "document" or "scene"
        """
        if not CV2_AVAILABLE:
            return "document"
        
        try:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Calculate edge density
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Calculate texture using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # High edge density and variance suggest scene text/handwriting
            if edge_density > 0.1 or laplacian_var > 500:
                return "scene"
            
            return "document"
            
        except Exception as e:
            logger.warning(f"Content type detection failed: {e}")
            return "document"
    
    async def process_with_tesseract(
        self,
        image_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD
    ) -> OCRResult:
        """Process with Tesseract OCR."""
        if not self.tesseract:
            raise RuntimeError("Tesseract not available")
        
        return await self.tesseract.process_image(image_data, language, mode, preprocess=True)
    
    async def process_with_easyocr(
        self,
        image_data: bytes,
        language: str = "en"
    ) -> OCRResult:
        """Process with EasyOCR for handwriting/scene text."""
        if not EASYOCR_AVAILABLE:
            raise ImportError("EasyOCR not installed")
        
        import time
        start_time = time.time()
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            
            # Get EasyOCR reader
            reader = self._get_easyocr_reader([language])
            
            # Run OCR
            results = reader.readtext(img_array)
            
            # Parse results
            blocks = []
            texts = []
            confidences = []
            
            for i, (bbox, text, conf) in enumerate(results):
                # Calculate bbox coordinates
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x = int(min(x_coords))
                y = int(min(y_coords))
                width = int(max(x_coords) - x)
                height = int(max(y_coords) - y)
                
                block = OCRBlock(
                    text=text,
                    confidence=float(conf) * 100,
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
                confidences.append(float(conf) * 100)
            
            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return OCRResult(
                text=full_text,
                blocks=blocks,
                confidence=avg_confidence,
                language=language,
                processing_time=time.time() - start_time,
                word_count=len(full_text.split()),
                metadata={"engine": "easyocr"}
            )
            
        except Exception as e:
            logger.error(f"EasyOCR processing failed: {e}")
            raise
    
    async def process_image(
        self,
        image_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD,
        engine: OCREngine = OCREngine.AUTO
    ) -> OCRResult:
        """
        Process image with selected or auto-detected OCR engine.
        
        Args:
            image_data: Raw image bytes
            language: OCR language
            mode: Processing mode
            engine: OCR engine to use (AUTO selects best)
        
        Returns:
            OCRResult with extracted text
        """
        # Map language for EasyOCR
        easy_lang = self.LANG_MAP.get(language.value, "en")
        
        # Auto-select engine
        if engine == OCREngine.AUTO:
            image = Image.open(io.BytesIO(image_data))
            content_type = self._detect_content_type(image)
            
            if content_type == "scene" and EASYOCR_AVAILABLE:
                logger.info("Auto-selected EasyOCR for scene text/handwriting")
                engine = OCREngine.EASYOCR
            else:
                logger.info("Auto-selected Tesseract for document text")
                engine = OCREngine.TESSERACT
        
        # Process with selected engine
        if engine == OCREngine.EASYOCR:
            try:
                return await self.process_with_easyocr(image_data, easy_lang)
            except Exception as e:
                logger.warning(f"EasyOCR failed, falling back to Tesseract: {e}")
                return await self.process_with_tesseract(image_data, language, mode)
        else:
            return await self.process_with_tesseract(image_data, language, mode)
    
    async def process_pdf(
        self,
        pdf_data: bytes,
        language: OCRLanguage = OCRLanguage.ENGLISH,
        mode: OCRMode = OCRMode.STANDARD,
        dpi: int = 300
    ) -> OCRResult:
        """
        Process PDF with enhanced OCR.
        Uses Tesseract (best for documents) regardless of auto setting.
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
            
            for page_num, image in enumerate(images):
                logger.info(f"Processing PDF page {page_num + 1}/{len(images)}")
                
                # Convert PIL to bytes
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='PNG')
                img_data = img_buffer.getvalue()
                
                # Process page with Tesseract (best for documents)
                result = await self.process_with_tesseract(image_data=img_data, language=language, mode=mode)
                
                all_blocks.extend(result.blocks)
                all_texts.append(result.text)
                all_confidences.append(result.confidence)
            
            full_text = '\n\n'.join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            return OCRResult(
                text=full_text,
                blocks=all_blocks,
                confidence=avg_confidence,
                language=language.value,
                processing_time=time.time() - start_time,
                page_count=len(images),
                word_count=len(full_text.split()),
                metadata={"engine": "tesseract", "enhanced_preprocessing": True}
            )
            
        except Exception as e:
            logger.error(f"Enhanced PDF OCR failed: {e}")
            raise
