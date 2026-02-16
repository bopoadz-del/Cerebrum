"""
Audio Chunking and Parallel Processing Pipeline
Splits audio files and processes them in parallel for transcription.
"""

import io
import asyncio
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import os

try:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AudioChunk:
    """Represents an audio chunk."""
    index: int
    data: bytes
    start_time: float  # seconds
    end_time: float  # seconds
    duration: float  # seconds
    format: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "format": self.format
        }


@dataclass
class ChunkingResult:
    """Result of audio chunking."""
    chunks: List[AudioChunk]
    total_duration: float
    total_chunks: int
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "total_duration": self.total_duration,
            "total_chunks": self.total_chunks,
            "processing_time": self.processing_time
        }


class AudioChunker:
    """
    Audio chunking utility with multiple strategies.
    Supports fixed-duration, silence-based, and sentence-based chunking.
    """
    
    def __init__(
        self,
        chunk_duration: int = 600,  # 10 minutes default
        overlap: int = 5,  # 5 seconds overlap
        min_chunk_duration: int = 30,  # 30 seconds minimum
        max_chunk_duration: int = 600  # 10 minutes maximum
    ):
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.min_chunk_duration = min_chunk_duration
        self.max_chunk_duration = max_chunk_duration
        
        if not PYDUB_AVAILABLE:
            raise ImportError("pydub is required for audio chunking")
    
    async def chunk_by_duration(
        self,
        audio_data: bytes,
        filename: str,
        target_duration: Optional[int] = None
    ) -> ChunkingResult:
        """
        Chunk audio by fixed duration.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            target_duration: Target chunk duration in seconds
        
        Returns:
            ChunkingResult with audio chunks
        """
        import time
        start_time = time.time()
        
        target = target_duration or self.chunk_duration
        
        try:
            # Load audio
            audio = await self._load_audio(audio_data, filename)
            
            total_duration = len(audio) / 1000  # Convert to seconds
            chunks = []
            
            chunk_length = target * 1000  # Convert to milliseconds
            overlap_length = self.overlap * 1000
            
            chunk_index = 0
            position = 0
            
            while position < len(audio):
                # Calculate chunk boundaries
                chunk_start = max(0, position - overlap_length)
                chunk_end = min(len(audio), position + chunk_length)
                
                # Extract chunk
                chunk_audio = audio[chunk_start:chunk_end]
                
                # Export to bytes
                chunk_data = await self._export_chunk(chunk_audio, "mp3")
                
                chunk = AudioChunk(
                    index=chunk_index,
                    data=chunk_data,
                    start_time=chunk_start / 1000,
                    end_time=chunk_end / 1000,
                    duration=(chunk_end - chunk_start) / 1000,
                    format="mp3"
                )
                chunks.append(chunk)
                
                position += chunk_length
                chunk_index += 1
            
            processing_time = time.time() - start_time
            
            return ChunkingResult(
                chunks=chunks,
                total_duration=total_duration,
                total_chunks=len(chunks),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Duration-based chunking failed: {e}")
            raise
    
    async def chunk_by_silence(
        self,
        audio_data: bytes,
        filename: str,
        min_silence_len: int = 500,  # ms
        silence_thresh: int = -40,  # dBFS
        keep_silence: int = 300  # ms
    ) -> ChunkingResult:
        """
        Chunk audio based on silence detection.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            min_silence_len: Minimum silence length to consider
            silence_thresh: Silence threshold in dBFS
            keep_silence: Amount of silence to keep at boundaries
        
        Returns:
            ChunkingResult with audio chunks
        """
        import time
        start_time = time.time()
        
        try:
            # Load audio
            audio = await self._load_audio(audio_data, filename)
            total_duration = len(audio) / 1000
            
            # Detect non-silent ranges
            nonsilent_ranges = detect_nonsilent(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh
            )
            
            chunks = []
            chunk_index = 0
            
            for start, end in nonsilent_ranges:
                # Add padding
                chunk_start = max(0, start - keep_silence)
                chunk_end = min(len(audio), end + keep_silence)
                
                # Extract chunk
                chunk_audio = audio[chunk_start:chunk_end]
                
                # Skip if too short
                if len(chunk_audio) < self.min_chunk_duration * 1000:
                    continue
                
                # Split if too long
                if len(chunk_audio) > self.max_chunk_duration * 1000:
                    sub_chunks = await self._split_large_chunk(
                        chunk_audio, chunk_index, chunk_start / 1000
                    )
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                else:
                    # Export to bytes
                    chunk_data = await self._export_chunk(chunk_audio, "mp3")
                    
                    chunk = AudioChunk(
                        index=chunk_index,
                        data=chunk_data,
                        start_time=chunk_start / 1000,
                        end_time=chunk_end / 1000,
                        duration=(chunk_end - chunk_start) / 1000,
                        format="mp3"
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            
            processing_time = time.time() - start_time
            
            return ChunkingResult(
                chunks=chunks,
                total_duration=total_duration,
                total_chunks=len(chunks),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Silence-based chunking failed: {e}")
            raise
    
    async def chunk_by_sentences(
        self,
        audio_data: bytes,
        filename: str,
        transcript_segments: List[Dict[str, Any]]
    ) -> ChunkingResult:
        """
        Chunk audio based on sentence boundaries from transcript.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            transcript_segments: Transcript segments with timestamps
        
        Returns:
            ChunkingResult with audio chunks
        """
        import time
        start_time = time.time()
        
        try:
            # Load audio
            audio = await self._load_audio(audio_data, filename)
            total_duration = len(audio) / 1000
            
            chunks = []
            current_chunk_segments = []
            current_duration = 0
            chunk_index = 0
            chunk_start_time = 0
            
            for segment in transcript_segments:
                segment_duration = segment.get('end', 0) - segment.get('start', 0)
                
                # Start new chunk if current would exceed target
                if current_duration + segment_duration > self.chunk_duration:
                    if current_chunk_segments:
                        # Create chunk from accumulated segments
                        chunk = await self._create_chunk_from_segments(
                            audio, current_chunk_segments, chunk_index, chunk_start_time
                        )
                        chunks.append(chunk)
                        chunk_index += 1
                    
                    # Start new chunk
                    current_chunk_segments = [segment]
                    current_duration = segment_duration
                    chunk_start_time = segment.get('start', 0)
                else:
                    current_chunk_segments.append(segment)
                    current_duration += segment_duration
            
            # Don't forget the last chunk
            if current_chunk_segments:
                chunk = await self._create_chunk_from_segments(
                    audio, current_chunk_segments, chunk_index, chunk_start_time
                )
                chunks.append(chunk)
            
            processing_time = time.time() - start_time
            
            return ChunkingResult(
                chunks=chunks,
                total_duration=total_duration,
                total_chunks=len(chunks),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Sentence-based chunking failed: {e}")
            raise
    
    async def _load_audio(self, audio_data: bytes, filename: str) -> AudioSegment:
        """Load audio from bytes."""
        suffix = Path(filename).suffix.lstrip('.') or 'mp3'
        return AudioSegment.from_file(io.BytesIO(audio_data), format=suffix)
    
    async def _export_chunk(self, audio: AudioSegment, format: str) -> bytes:
        """Export audio chunk to bytes."""
        buffer = io.BytesIO()
        audio.export(buffer, format=format)
        return buffer.getvalue()
    
    async def _split_large_chunk(
        self,
        audio: AudioSegment,
        start_index: int,
        start_time: float
    ) -> List[AudioChunk]:
        """Split a large chunk into smaller pieces."""
        chunks = []
        chunk_length = self.max_chunk_duration * 1000
        
        for i in range(0, len(audio), chunk_length):
            chunk_audio = audio[i:i + chunk_length]
            chunk_data = await self._export_chunk(chunk_audio, "mp3")
            
            chunk = AudioChunk(
                index=start_index + i // chunk_length,
                data=chunk_data,
                start_time=start_time + i / 1000,
                end_time=start_time + min(i + chunk_length, len(audio)) / 1000,
                duration=min(chunk_length, len(audio) - i) / 1000,
                format="mp3"
            )
            chunks.append(chunk)
        
        return chunks
    
    async def _create_chunk_from_segments(
        self,
        audio: AudioSegment,
        segments: List[Dict[str, Any]],
        index: int,
        start_time: float
    ) -> AudioChunk:
        """Create audio chunk from transcript segments."""
        first_segment = segments[0]
        last_segment = segments[-1]
        
        chunk_start = int(first_segment.get('start', 0) * 1000)
        chunk_end = int(last_segment.get('end', 0) * 1000)
        
        chunk_audio = audio[chunk_start:chunk_end]
        chunk_data = await self._export_chunk(chunk_audio, "mp3")
        
        return AudioChunk(
            index=index,
            data=chunk_data,
            start_time=first_segment.get('start', 0),
            end_time=last_segment.get('end', 0),
            duration=last_segment.get('end', 0) - first_segment.get('start', 0),
            format="mp3"
        )


class ParallelProcessor:
    """Process audio chunks in parallel."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    async def process_chunks(
        self,
        chunks: List[AudioChunk],
        processor: Callable[[AudioChunk], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Process chunks in parallel.
        
        Args:
            chunks: List of audio chunks
            processor: Async function to process each chunk
            progress_callback: Optional progress callback
        
        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_limit(chunk: AudioChunk) -> Any:
            async with semaphore:
                result = await processor(chunk)
                return result
        
        # Create tasks
        tasks = [process_with_limit(chunk) for chunk in chunks]
        
        # Process with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            if progress_callback:
                progress_callback(len(results), len(chunks))
        
        return results


class AudioProcessingPipeline:
    """Complete audio processing pipeline with chunking and parallel processing."""
    
    def __init__(
        self,
        chunking_strategy: str = "duration",
        max_workers: int = 4,
        chunk_duration: int = 600
    ):
        self.chunking_strategy = chunking_strategy
        self.chunker = AudioChunker(chunk_duration=chunk_duration)
        self.parallel_processor = ParallelProcessor(max_workers)
    
    async def process(
        self,
        audio_data: bytes,
        filename: str,
        processor: Callable[[AudioChunk], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **chunking_kwargs
    ) -> Dict[str, Any]:
        """
        Process audio file with chunking and parallel processing.
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            processor: Async function to process each chunk
            progress_callback: Optional progress callback
            **chunking_kwargs: Additional arguments for chunking
        
        Returns:
            Dictionary with chunking info and processing results
        """
        # Chunk audio
        if self.chunking_strategy == "duration":
            chunking_result = await self.chunker.chunk_by_duration(
                audio_data, filename, **chunking_kwargs
            )
        elif self.chunking_strategy == "silence":
            chunking_result = await self.chunker.chunk_by_silence(
                audio_data, filename, **chunking_kwargs
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {self.chunking_strategy}")
        
        logger.info(f"Created {chunking_result.total_chunks} chunks")
        
        # Process chunks in parallel
        results = await self.parallel_processor.process_chunks(
            chunking_result.chunks,
            processor,
            progress_callback
        )
        
        return {
            "chunking": chunking_result.to_dict(),
            "results": results
        }


# Convenience function
async def chunk_and_process_audio(
    audio_data: bytes,
    filename: str,
    processor: Callable[[AudioChunk], Any],
    strategy: str = "duration",
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    """
    Chunk audio and process in parallel.
    
    Args:
        audio_data: Raw audio bytes
        filename: Original filename
        processor: Async function to process each chunk
        strategy: Chunking strategy (duration, silence)
        max_workers: Maximum parallel workers
        progress_callback: Optional progress callback
    
    Returns:
        Dictionary with chunking info and processing results
    """
    pipeline = AudioProcessingPipeline(
        chunking_strategy=strategy,
        max_workers=max_workers
    )
    return await pipeline.process(audio_data, filename, processor, progress_callback)
