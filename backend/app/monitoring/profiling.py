"""
Continuous Profiling
Pyroscope integration for performance profiling
"""

import time
import threading
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ProfileSample:
    """Profile sample"""
    timestamp: datetime
    function_name: str
    file_path: str
    line_number: int
    duration_ms: float
    call_count: int = 1


@dataclass
class Profile:
    """Aggregated profile"""
    start_time: datetime
    end_time: datetime
    samples: List[ProfileSample]
    total_duration_ms: float
    
    def get_top_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top functions by duration"""
        function_times = defaultdict(lambda: {'duration': 0, 'calls': 0})
        
        for sample in self.samples:
            key = (sample.function_name, sample.file_path)
            function_times[key]['duration'] += sample.duration_ms
            function_times[key]['calls'] += sample.call_count
        
        sorted_functions = sorted(
            function_times.items(),
            key=lambda x: x[1]['duration'],
            reverse=True
        )
        
        return [
            {
                'function': func[0],
                'file': func[1],
                'total_duration_ms': data['duration'],
                'call_count': data['calls'],
                'avg_duration_ms': data['duration'] / max(data['calls'], 1)
            }
            for func, data in sorted_functions[:limit]
        ]


class PyroscopeClient:
    """Pyroscope profiling client"""
    
    def __init__(self, server_url: str = 'http://localhost:4040'):
        self.server_url = server_url
        self.app_name = settings.SERVICE_NAME
        self.enabled = True
    
    async def upload_profile(self, profile: Profile, profile_type: str = 'cpu'):
        """Upload profile to Pyroscope"""
        try:
            # Convert profile to Pyroscope format
            data = self._convert_to_pyroscope_format(profile, profile_type)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.server_url}/ingest',
                    params={
                        'name': f'{self.app_name}.{profile_type}',
                        'from': int(profile.start_time.timestamp()),
                        'until': int(profile.end_time.timestamp())
                    },
                    content=data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to upload profile to Pyroscope: {e}")
    
    def _convert_to_pyroscope_format(self, profile: Profile, profile_type: str) -> bytes:
        """Convert profile to Pyroscope format"""
        # This would convert to Pyroscope's expected format
        # Simplified implementation
        lines = []
        
        for sample in profile.samples:
            line = f"{sample.function_name};{sample.file_path}:{sample.line_number} {sample.duration_ms}"
            lines.append(line)
        
        return '\n'.join(lines).encode()


class CPUProfiler:
    """CPU usage profiler"""
    
    def __init__(self, interval_ms: int = 10):
        self.interval_ms = interval_ms
        self.samples: List[ProfileSample] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start CPU profiling"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._profile_loop)
        self._thread.daemon = True
        self._thread.start()
        
        logger.info("CPU profiler started")
    
    def stop(self):
        """Stop CPU profiling"""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("CPU profiler stopped")
    
    def _profile_loop(self):
        """Main profiling loop"""
        import sys
        
        while self._running:
            # Sample current stack traces
            for thread_id, frame in sys._current_frames().items():
                self._sample_frame(frame)
            
            time.sleep(self.interval_ms / 1000)
    
    def _sample_frame(self, frame):
        """Sample a stack frame"""
        while frame:
            code = frame.f_code
            
            sample = ProfileSample(
                timestamp=datetime.utcnow(),
                function_name=code.co_name,
                file_path=code.co_filename,
                line_number=frame.f_lineno,
                duration_ms=self.interval_ms
            )
            
            self.samples.append(sample)
            frame = frame.f_back
    
    def get_profile(self, duration_seconds: int = 60) -> Profile:
        """Get profile for the last N seconds"""
        cutoff = datetime.utcnow() - timedelta(seconds=duration_seconds)
        
        recent_samples = [s for s in self.samples if s.timestamp > cutoff]
        
        # Clear old samples
        self.samples = recent_samples
        
        return Profile(
            start_time=cutoff,
            end_time=datetime.utcnow(),
            samples=recent_samples,
            total_duration_ms=sum(s.duration_ms for s in recent_samples)
        )


class MemoryProfiler:
    """Memory usage profiler"""
    
    def __init__(self):
        self.samples: List[Dict[str, Any]] = []
    
    def take_snapshot(self) -> Dict[str, Any]:
        """Take a memory snapshot"""
        import tracemalloc
        
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        snapshot = tracemalloc.take_snapshot()
        
        # Get top memory consumers
        top_stats = snapshot.statistics('lineno')[:10]
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_allocated': tracemalloc.get_traced_memory()[0],
            'peak_memory': tracemalloc.get_traced_memory()[1],
            'top_allocations': [
                {
                    'file': stat.traceback.format()[-1],
                    'size_bytes': stat.size,
                    'count': stat.count
                }
                for stat in top_stats
            ]
        }
        
        self.samples.append(result)
        
        return result
    
    def get_memory_profile(self) -> Dict[str, Any]:
        """Get memory profile summary"""
        if not self.samples:
            return {}
        
        return {
            'snapshots': len(self.samples),
            'latest': self.samples[-1],
            'peak_memory_bytes': max(s.get('peak_memory', 0) for s in self.samples)
        }


class ContinuousProfiler:
    """Continuous profiling manager"""
    
    def __init__(self):
        self.pyroscope: Optional[PyroscopeClient] = None
        self.cpu_profiler = CPUProfiler()
        self.memory_profiler = MemoryProfiler()
        self.enabled = False
        self.upload_interval_seconds = 60
        self._upload_task: Optional[asyncio.Task] = None
    
    def initialize(self):
        """Initialize continuous profiling"""
        if settings.PYROSCOPE_URL:
            self.pyroscope = PyroscopeClient(settings.PYROSCOPE_URL)
        
        self.enabled = True
        self.cpu_profiler.start()
        
        self._upload_task = asyncio.create_task(self._upload_loop())
        
        logger.info("Continuous profiling initialized")
    
    async def close(self):
        """Close continuous profiling"""
        self.enabled = False
        
        self.cpu_profiler.stop()
        
        if self._upload_task:
            self._upload_task.cancel()
        
        logger.info("Continuous profiling stopped")
    
    async def _upload_loop(self):
        """Upload profiles periodically"""
        while self.enabled:
            try:
                await asyncio.sleep(self.upload_interval_seconds)
                await self._upload_profiles()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error uploading profiles: {e}")
    
    async def _upload_profiles(self):
        """Upload profiles to Pyroscope"""
        if not self.pyroscope:
            return
        
        # Get and upload CPU profile
        cpu_profile = self.cpu_profiler.get_profile(duration_seconds=self.upload_interval_seconds)
        
        if cpu_profile.samples:
            await self.pyroscope.upload_profile(cpu_profile, 'cpu')
            logger.debug(f"Uploaded CPU profile with {len(cpu_profile.samples)} samples")
    
    def take_memory_snapshot(self) -> Dict[str, Any]:
        """Take a memory snapshot"""
        return self.memory_profiler.take_snapshot()
    
    def get_profiling_summary(self) -> Dict[str, Any]:
        """Get profiling summary"""
        cpu_profile = self.cpu_profiler.get_profile(duration_seconds=60)
        
        return {
            'cpu': {
                'samples_collected': len(cpu_profile.samples),
                'top_functions': cpu_profile.get_top_functions(10)
            },
            'memory': self.memory_profiler.get_memory_profile()
        }


# Global continuous profiler
continuous_profiler = ContinuousProfiler()
