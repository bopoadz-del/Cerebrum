"""
Transcription Pipeline using Whisper API
Transcribes audio/video files to text with speaker identification.
"""

import os
import io
import json
from typing import Optional, Dict, List, Any, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
import asyncio

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class TranscriptionModel(Enum):
    """Available transcription models."""
    WHISPER_1 = "whisper-1"
    WHISPER_LARGE = "whisper-large-v3"


class AudioFormat(Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    MP4 = "mp4"
    MPEG = "mpeg"
    MPGA = "mpga"
    M4A = "m4a"
    WAV = "wav"
    WEBM = "webm"
    OGG = "ogg"


@dataclass
class TranscriptSegment:
    """A segment of transcribed text."""
    id: int
    start: float
    end: float
    text: str
    confidence: float
    speaker: Optional[str] = None
    words: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "confidence": self.confidence,
            "speaker": self.speaker,
            "words": self.words
        }


@dataclass
class TranscriptionResult:
    """Result of transcription."""
    text: str
    segments: List[TranscriptSegment]
    language: str
    duration: float
    processing_time: float
    word_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "segments": [s.to_dict() for s in self.segments],
            "language": self.language,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "word_count": self.word_count,
            "metadata": self.metadata
        }


class WhisperTranscriber:
    """
    Audio/video transcriber using OpenAI Whisper API.
    Supports multiple languages and speaker identification.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if OPENAI_AVAILABLE:
            openai.api_key = self.api_key
    
    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3",
        language: Optional[str] = None,
        model: TranscriptionModel = TranscriptionModel.WHISPER_1,
        prompt: Optional[str] = None,
        response_format: str = "verbose_json",
        timestamp_granularities: List[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio/video file.
        
        Args:
            audio_data: Raw audio/video bytes
            filename: Original filename
            language: Optional language code (e.g., 'en', 'es')
            model: Whisper model to use
            prompt: Optional prompt for context
            response_format: Output format
            timestamp_granularities: Level of timestamp detail
        
        Returns:
            TranscriptionResult with text and segments
        """
        import time
        start_time = time.time()
        
        try:
            # Save to temp file
            suffix = Path(filename).suffix or '.mp3'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Prepare parameters
                params = {
                    "model": model.value,
                    "file": open(temp_path, "rb"),
                }
                
                if language:
                    params["language"] = language
                
                if prompt:
                    params["prompt"] = prompt
                
                if response_format:
                    params["response_format"] = response_format
                
                if timestamp_granularities:
                    params["timestamp_granularities"] = timestamp_granularities
                
                # Call Whisper API
                response = await openai.Audio.atranscribe(**params)
                
                # Parse response
                if response_format == "verbose_json":
                    result = self._parse_verbose_response(response)
                else:
                    result = self._parse_simple_response(response)
                
                result.processing_time = time.time() - start_time
                
                return result
                
            finally:
                # Cleanup temp file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def _parse_verbose_response(self, response: Dict[str, Any]) -> TranscriptionResult:
        """Parse verbose JSON response from Whisper."""
        segments = []
        
        for i, seg_data in enumerate(response.get('segments', [])):
            segment = TranscriptSegment(
                id=i,
                start=seg_data.get('start', 0),
                end=seg_data.get('end', 0),
                text=seg_data.get('text', '').strip(),
                confidence=seg_data.get('avg_logprob', 0),
                words=seg_data.get('words', [])
            )
            segments.append(segment)
        
        return TranscriptionResult(
            text=response.get('text', ''),
            segments=segments,
            language=response.get('language', 'unknown'),
            duration=response.get('duration', 0),
            processing_time=0,
            word_count=len(response.get('text', '').split())
        )
    
    def _parse_simple_response(self, response: Any) -> TranscriptionResult:
        """Parse simple text response from Whisper."""
        text = response if isinstance(response, str) else response.get('text', '')
        
        return TranscriptionResult(
            text=text,
            segments=[],
            language='unknown',
            duration=0,
            processing_time=0,
            word_count=len(text.split())
        )
    
    async def transcribe_with_speakers(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3",
        num_speakers: Optional[int] = None,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe with speaker diarization.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            num_speakers: Optional hint for number of speakers
            language: Optional language code
        
        Returns:
            TranscriptionResult with speaker labels
        """
        # First get transcription
        result = await self.transcribe(audio_data, filename, language)
        
        # Then perform speaker diarization
        # This would integrate with a diarization service like pyannote.audio
        # For now, return without speaker labels
        
        return result
    
    async def translate(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3",
        model: TranscriptionModel = TranscriptionModel.WHISPER_1,
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Translate audio to English text.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            model: Whisper model to use
            prompt: Optional prompt
        
        Returns:
            TranscriptionResult with English translation
        """
        import time
        start_time = time.time()
        
        try:
            # Save to temp file
            suffix = Path(filename).suffix or '.mp3'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Call translation API
                params = {
                    "model": model.value,
                    "file": open(temp_path, "rb"),
                }
                
                if prompt:
                    params["prompt"] = prompt
                
                response = await openai.Audio.atranslate(**params)
                
                result = self._parse_simple_response(response)
                result.processing_time = time.time() - start_time
                
                return result
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise


class AudioChunker:
    """Chunks audio files for parallel processing."""
    
    def __init__(self, chunk_duration: int = 600):  # 10 minutes default
        self.chunk_duration = chunk_duration
    
    async def chunk_audio(
        self,
        audio_data: bytes,
        filename: str
    ) -> List[Tuple[int, bytes]]:
        """
        Split audio into chunks.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
        
        Returns:
            List of (chunk_index, chunk_data) tuples
        """
        try:
            from pydub import AudioSegment
            
            # Load audio
            suffix = Path(filename).suffix
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=suffix.lstrip('.'))
            
            chunks = []
            chunk_length = self.chunk_duration * 1000  # Convert to milliseconds
            
            for i in range(0, len(audio), chunk_length):
                chunk = audio[i:i + chunk_length]
                
                # Export chunk to bytes
                chunk_buffer = io.BytesIO()
                chunk.export(chunk_buffer, format='mp3')
                chunks.append((i // chunk_length, chunk_buffer.getvalue()))
            
            return chunks
            
        except ImportError:
            logger.warning("pydub not available, returning single chunk")
            return [(0, audio_data)]
        except Exception as e:
            logger.error(f"Audio chunking failed: {e}")
            return [(0, audio_data)]


class ParallelTranscriber:
    """Transcribe audio in parallel chunks."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.chunker = AudioChunker()
        self.transcriber = WhisperTranscriber()
    
    async def transcribe_large_file(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> TranscriptionResult:
        """
        Transcribe large audio file in parallel chunks.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            language: Optional language code
            progress_callback: Optional progress callback
        
        Returns:
            Combined TranscriptionResult
        """
        import time
        start_time = time.time()
        
        # Chunk audio
        chunks = await self.chunker.chunk_audio(audio_data, filename)
        logger.info(f"Split audio into {len(chunks)} chunks")
        
        # Transcribe chunks in parallel
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def transcribe_chunk(index: int, chunk_data: bytes) -> TranscriptionResult:
            async with semaphore:
                result = await self.transcriber.transcribe(
                    chunk_data,
                    f"chunk_{index}.mp3",
                    language
                )
                
                if progress_callback:
                    progress_callback(index + 1, len(chunks))
                
                return result
        
        # Run all transcriptions
        tasks = [transcribe_chunk(idx, data) for idx, data in chunks]
        results = await asyncio.gather(*tasks)
        
        # Merge results
        merged = self._merge_results(results)
        merged.processing_time = time.time() - start_time
        
        return merged
    
    def _merge_results(self, results: List[TranscriptionResult]) -> TranscriptionResult:
        """Merge multiple transcription results."""
        all_texts = []
        all_segments = []
        total_duration = 0
        
        for result in results:
            # Adjust segment timestamps
            for segment in result.segments:
                adjusted_segment = TranscriptSegment(
                    id=len(all_segments),
                    start=segment.start + total_duration,
                    end=segment.end + total_duration,
                    text=segment.text,
                    confidence=segment.confidence,
                    speaker=segment.speaker,
                    words=[
                        {**w, 'start': w.get('start', 0) + total_duration, 'end': w.get('end', 0) + total_duration}
                        for w in segment.words
                    ]
                )
                all_segments.append(adjusted_segment)
            
            all_texts.append(result.text)
            total_duration += result.duration
        
        return TranscriptionResult(
            text=' '.join(all_texts),
            segments=all_segments,
            language=results[0].language if results else 'unknown',
            duration=total_duration,
            processing_time=0,
            word_count=len(' '.join(all_texts).split())
        )


class TranscriptionPipeline:
    """Pipeline for transcription processing."""
    
    def __init__(self, use_parallel: bool = True, max_workers: int = 4):
        self.use_parallel = use_parallel
        if use_parallel:
            self.transcriber = ParallelTranscriber(max_workers)
        else:
            self.transcriber = WhisperTranscriber()
    
    async def process_audio(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> TranscriptionResult:
        """
        Process audio file for transcription.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            language: Optional language code
            progress_callback: Optional progress callback
        
        Returns:
            TranscriptionResult
        """
        if self.use_parallel:
            return await self.transcriber.transcribe_large_file(
                audio_data, filename, language, progress_callback
            )
        else:
            result = await self.transcriber.transcribe(audio_data, filename, language)
            if progress_callback:
                progress_callback(1, 1)
            return result


# Convenience function
async def transcribe_audio(
    audio_data: bytes,
    filename: str = "audio.mp3",
    language: Optional[str] = None,
    use_parallel: bool = True
) -> TranscriptionResult:
    """
    Transcribe audio file.
    
    Args:
        audio_data: Raw audio bytes
        filename: Original filename
        language: Optional language code
        use_parallel: Whether to use parallel processing for large files
    
    Returns:
        TranscriptionResult
    """
    pipeline = TranscriptionPipeline(use_parallel=use_parallel)
    return await pipeline.process_audio(audio_data, filename, language)
