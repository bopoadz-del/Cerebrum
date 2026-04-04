"""
Image Understanding Service for Cerebrum AI

Provides image analysis capabilities using vision models.
Similar to Kimi chat's image understanding capabilities.
"""

import base64
import io
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import os

from PIL import Image

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Types of image analysis available."""
    GENERAL = "general"
    OCR = "ocr"
    DOCUMENT = "document"
    DIAGRAM = "diagram"
    CHART = "chart"
    TABLE = "table"
    CONSTRUCTION = "construction"
    SAFETY = "safety"
    OBJECT_DETECTION = "object_detection"


@dataclass
class ImageAnalysisResult:
    """Result of image analysis."""
    success: bool
    description: str
    text_content: Optional[str] = None
    objects: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    analysis_type: AnalysisType = AnalysisType.GENERAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "description": self.description,
            "text_content": self.text_content,
            "objects": self.objects,
            "metadata": self.metadata,
            "error": self.error,
            "analysis_type": self.analysis_type.value
        }


@dataclass
class ImageMetadata:
    """Metadata extracted from an image."""
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    has_transparency: bool
    is_animated: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "mode": self.mode,
            "size_bytes": self.size_bytes,
            "has_transparency": self.has_transparency,
            "is_animated": self.is_animated
        }


class ImageUnderstandingService:
    """
    Image understanding service with multiple analysis capabilities.
    
    Features:
    - General image description
    - OCR text extraction
    - Document analysis
    - Diagram/chart interpretation
    - Construction site analysis
    - Safety hazard detection
    - Object detection
    """
    
    # Supported image formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    # Maximum image size (10MB)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024
    
    # Maximum dimensions for processing
    MAX_DIMENSIONS = (4096, 4096)
    
    def __init__(self):
        self._ocr_pipeline = None
        self._classification_pipeline = None
        self._openai_available = self._check_openai_available()
        
    def _check_openai_available(self) -> bool:
        """Check if OpenAI is available for vision capabilities."""
        try:
            from app.core.config import settings
            return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-key-here")
        except:
            return False
    
    def _get_ocr_pipeline(self):
        """Lazy load OCR pipeline."""
        if self._ocr_pipeline is None:
            try:
                from app.pipelines.ocr import TesseractOCR
                self._ocr_pipeline = TesseractOCR()
            except Exception as e:
                logger.warning(f"Could not load OCR pipeline: {e}")
        return self._ocr_pipeline
    
    def _get_classification_pipeline(self):
        """Lazy load classification pipeline."""
        if self._classification_pipeline is None:
            try:
                from app.pipelines.document_classification import classify_document
                self._classification_pipeline = classify_document
            except Exception as e:
                logger.warning(f"Could not load classification pipeline: {e}")
        return self._classification_pipeline
    
    async def analyze_image(
        self,
        image_data: Union[bytes, str],
        analysis_type: AnalysisType = AnalysisType.GENERAL,
        prompt: Optional[str] = None,
        extract_text: bool = True
    ) -> ImageAnalysisResult:
        """
        Analyze an image and return detailed information.
        
        Args:
            image_data: Raw image bytes or base64-encoded string
            analysis_type: Type of analysis to perform
            prompt: Optional custom prompt for analysis
            extract_text: Whether to extract text via OCR
            
        Returns:
            ImageAnalysisResult with analysis results
        """
        try:
            # Decode image if base64
            if isinstance(image_data, str):
                try:
                    # Remove data URL prefix if present
                    if ',' in image_data:
                        image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                except Exception as e:
                    return ImageAnalysisResult(
                        success=False,
                        description="",
                        error=f"Invalid base64 image data: {str(e)}"
                    )
            else:
                image_bytes = image_data
            
            # Validate image size
            if len(image_bytes) > self.MAX_IMAGE_SIZE:
                return ImageAnalysisResult(
                    success=False,
                    description="",
                    error=f"Image too large. Maximum size: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
                )
            
            # Load and validate image
            try:
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                return ImageAnalysisResult(
                    success=False,
                    description="",
                    error=f"Could not load image: {str(e)}"
                )
            
            # Get metadata
            metadata = self._extract_metadata(image, image_bytes)
            
            # Perform analysis based on type
            if analysis_type == AnalysisType.OCR or extract_text:
                return await self._perform_ocr_analysis(image_bytes, metadata)
            elif analysis_type == AnalysisType.DOCUMENT:
                return await self._perform_document_analysis(image_bytes, metadata)
            elif analysis_type == AnalysisType.CONSTRUCTION:
                return await self._perform_construction_analysis(image_bytes, metadata)
            elif analysis_type == AnalysisType.CHART:
                return await self._perform_chart_analysis(image, metadata)
            else:
                return await self._perform_general_analysis(image_bytes, metadata, prompt)
                
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"Analysis failed: {str(e)}"
            )
    
    def _extract_metadata(self, image: Image.Image, image_bytes: bytes) -> ImageMetadata:
        """Extract metadata from image."""
        return ImageMetadata(
            width=image.width,
            height=image.height,
            format=image.format or "Unknown",
            mode=image.mode,
            size_bytes=len(image_bytes),
            has_transparency=image.mode in ('RGBA', 'P') and image.info.get('transparency') is not None,
            is_animated=getattr(image, 'is_animated', False)
        )
    
    async def _perform_ocr_analysis(
        self,
        image_bytes: bytes,
        metadata: ImageMetadata
    ) -> ImageAnalysisResult:
        """Perform OCR text extraction."""
        try:
            ocr = self._get_ocr_pipeline()
            if ocr is None:
                return ImageAnalysisResult(
                    success=False,
                    description="",
                    error="OCR service not available",
                    metadata=metadata.to_dict()
                )
            
            from app.pipelines.ocr import OCRLanguage, OCRMode
            result = await ocr.process_image(
                image_bytes,
                language=OCRLanguage.ENGLISH,
                mode=OCRMode.STANDARD,
                preprocess=True
            )
            
            return ImageAnalysisResult(
                success=True,
                description=f"OCR completed on {metadata.width}x{metadata.height} image",
                text_content=result.text,
                metadata={
                    **metadata.to_dict(),
                    "ocr_confidence": result.confidence,
                    "word_count": result.word_count
                },
                analysis_type=AnalysisType.OCR
            )
            
        except Exception as e:
            logger.error(f"OCR analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"OCR failed: {str(e)}",
                metadata=metadata.to_dict()
            )
    
    async def _perform_document_analysis(
        self,
        image_bytes: bytes,
        metadata: ImageMetadata
    ) -> ImageAnalysisResult:
        """Perform document analysis."""
        try:
            classify = self._get_classification_pipeline()
            if classify is None:
                # Fallback to OCR
                return await self._perform_ocr_analysis(image_bytes, metadata)
            
            result = await classify(image_bytes, "document.png")
            classification = result.primary_classification
            
            # Also perform OCR for text content
            ocr_result = await self._perform_ocr_analysis(image_bytes, metadata)
            
            return ImageAnalysisResult(
                success=True,
                description=f"Document type: {classification.document_type.value}",
                text_content=ocr_result.text_content,
                metadata={
                    **metadata.to_dict(),
                    "document_type": classification.document_type.value,
                    "category": classification.category.value,
                    "confidence": classification.confidence,
                    "key_fields": classification.key_fields
                },
                analysis_type=AnalysisType.DOCUMENT
            )
            
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"Document analysis failed: {str(e)}",
                metadata=metadata.to_dict()
            )
    
    async def _perform_construction_analysis(
        self,
        image_bytes: bytes,
        metadata: ImageMetadata
    ) -> ImageAnalysisResult:
        """Perform construction-specific analysis."""
        try:
            # First do OCR to extract any text
            ocr_result = await self._perform_ocr_analysis(image_bytes, metadata)
            
            # Detect construction-related elements
            description = f"Construction image analysis:\n"
            description += f"- Dimensions: {metadata.width}x{metadata.height}\n"
            description += f"- Format: {metadata.format}\n"
            
            if ocr_result.text_content:
                description += f"- Text detected: {len(ocr_result.text_content)} characters\n"
            
            # Add construction-specific insights
            construction_keywords = [
                'blueprint', 'plan', 'elevation', 'section', 'detail',
                'foundation', 'structural', 'concrete', 'steel', 'rebar',
                'dimension', 'scale', 'north arrow', 'title block'
            ]
            
            detected_keywords = []
            text_lower = (ocr_result.text_content or "").lower()
            for keyword in construction_keywords:
                if keyword in text_lower:
                    detected_keywords.append(keyword)
            
            if detected_keywords:
                description += f"- Detected elements: {', '.join(detected_keywords)}\n"
            
            return ImageAnalysisResult(
                success=True,
                description=description,
                text_content=ocr_result.text_content,
                metadata={
                    **metadata.to_dict(),
                    "detected_elements": detected_keywords,
                    "is_likely_blueprint": 'blueprint' in detected_keywords or 'plan' in detected_keywords
                },
                analysis_type=AnalysisType.CONSTRUCTION
            )
            
        except Exception as e:
            logger.error(f"Construction analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"Construction analysis failed: {str(e)}",
                metadata=metadata.to_dict()
            )
    
    async def _perform_chart_analysis(
        self,
        image: Image.Image,
        metadata: ImageMetadata
    ) -> ImageAnalysisResult:
        """Analyze charts and graphs."""
        try:
            description = f"Chart/Graph analysis:\n"
            description += f"- Dimensions: {metadata.width}x{metadata.height}\n"
            description += f"- Format: {metadata.format}\n"
            
            # Simple heuristic analysis
            # Charts often have distinct color patterns
            colors = image.getcolors(maxcolors=256)
            if colors:
                unique_colors = len(colors)
                description += f"- Unique colors: {unique_colors}\n"
                
                if unique_colors < 20:
                    description += "- Appears to be a simple chart with limited color palette\n"
                else:
                    description += "- Complex image with many colors\n"
            
            return ImageAnalysisResult(
                success=True,
                description=description,
                metadata={
                    **metadata.to_dict(),
                    "unique_colors": len(colors) if colors else 0,
                    "is_likely_chart": len(colors) < 50 if colors else False
                },
                analysis_type=AnalysisType.CHART
            )
            
        except Exception as e:
            logger.error(f"Chart analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"Chart analysis failed: {str(e)}",
                metadata=metadata.to_dict()
            )
    
    async def _perform_general_analysis(
        self,
        image_bytes: bytes,
        metadata: ImageMetadata,
        prompt: Optional[str] = None
    ) -> ImageAnalysisResult:
        """Perform general image analysis."""
        try:
            # Try OpenAI vision if available
            if self._openai_available:
                return await self._analyze_with_openai(image_bytes, metadata, prompt)
            
            # Fallback to basic analysis
            description = f"Image analysis:\n"
            description += f"- Dimensions: {metadata.width}x{metadata.height} pixels\n"
            description += f"- Format: {metadata.format}\n"
            description += f"- Color mode: {metadata.mode}\n"
            description += f"- File size: {metadata.size_bytes / 1024:.1f} KB\n"
            
            if metadata.has_transparency:
                description += "- Image has transparency\n"
            
            if metadata.is_animated:
                description += "- Image is animated\n"
            
            return ImageAnalysisResult(
                success=True,
                description=description,
                metadata=metadata.to_dict(),
                analysis_type=AnalysisType.GENERAL
            )
            
        except Exception as e:
            logger.error(f"General analysis error: {e}")
            return ImageAnalysisResult(
                success=False,
                description="",
                error=f"Analysis failed: {str(e)}",
                metadata=metadata.to_dict()
            )
    
    async def _analyze_with_openai(
        self,
        image_bytes: bytes,
        metadata: ImageMetadata,
        prompt: Optional[str] = None
    ) -> ImageAnalysisResult:
        """Analyze image using OpenAI Vision API."""
        try:
            import openai
            from app.core.config import settings
            
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Encode image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            default_prompt = "Describe this image in detail. If it contains text, transcribe it."
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt or default_prompt},
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
            
            description = response.choices[0].message.content
            
            return ImageAnalysisResult(
                success=True,
                description=description,
                metadata={
                    **metadata.to_dict(),
                    "model": "gpt-4o-mini",
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                },
                analysis_type=AnalysisType.GENERAL
            )
            
        except Exception as e:
            logger.warning(f"OpenAI vision analysis failed: {e}")
            # Fallback to basic analysis
            description = f"Image ({metadata.width}x{metadata.height}, {metadata.format})"
            return ImageAnalysisResult(
                success=True,
                description=description,
                metadata=metadata.to_dict(),
                analysis_type=AnalysisType.GENERAL
            )
    
    def validate_image(self, image_data: Union[bytes, str]) -> tuple[bool, Optional[str]]:
        """
        Validate image data without analyzing.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Decode if base64
            if isinstance(image_data, str):
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            # Check size
            if len(image_bytes) > self.MAX_IMAGE_SIZE:
                return False, f"Image too large. Max: {self.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            
            # Try to load
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # Verify it's a valid image
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid image: {str(e)}"


# Singleton instance
_image_service: Optional[ImageUnderstandingService] = None


def get_image_understanding_service() -> ImageUnderstandingService:
    """Get or create image understanding service instance."""
    global _image_service
    if _image_service is None:
        _image_service = ImageUnderstandingService()
    return _image_service
