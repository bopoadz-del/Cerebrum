"""
Hybrid cloud-edge inference orchestration.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import time


class InferenceLocation(Enum):
    """Where inference should be performed."""
    CLOUD = "cloud"
    EDGE = "edge"
    HYBRID = "hybrid"
    AUTO = "auto"


class InferencePriority(Enum):
    """Priority for inference requests."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class InferenceRequest:
    """Inference request."""
    request_id: str
    model_name: str
    model_version: str
    input_data: Any
    preferred_location: InferenceLocation
    priority: InferencePriority
    max_latency_ms: Optional[int] = None
    fallback_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InferenceResult:
    """Inference result."""
    request_id: str
    location: InferenceLocation
    model_name: str
    model_version: str
    output: Any
    latency_ms: float
    confidence: Optional[float] = None
    fallback_used: bool = False
    error_message: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EdgeCapabilities:
    """Capabilities of an edge device."""
    device_id: str
    available_models: List[str]
    max_batch_size: int
    inference_latency_ms: Dict[str, float]
    current_load: float
    is_available: bool


class HybridInferenceOrchestrator:
    """Orchestrate inference between cloud and edge."""
    
    def __init__(self):
        self.cloud_inference_func: Optional[Callable] = None
        self.edge_capabilities: Dict[str, EdgeCapabilities] = {}
        self._inference_history: List[InferenceResult] = []
        self._latency_threshold_ms = 100  # Switch to edge if cloud > 100ms
        self._edge_load_threshold = 0.8  # Use cloud if edge load > 80%
    
    def register_cloud_inference(self, inference_func: Callable):
        """Register the cloud inference function."""
        self.cloud_inference_func = inference_func
    
    async def update_edge_capabilities(
        self,
        device_id: str,
        capabilities: EdgeCapabilities
    ):
        """Update capabilities for an edge device."""
        self.edge_capabilities[device_id] = capabilities
    
    async def infer(
        self,
        model_name: str,
        model_version: str,
        input_data: Any,
        preferred_location: InferenceLocation = InferenceLocation.AUTO,
        priority: InferencePriority = InferencePriority.NORMAL,
        max_latency_ms: Optional[int] = None,
        fallback_enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """Perform inference with automatic location selection."""
        
        request_id = str(uuid.uuid4())
        
        request = InferenceRequest(
            request_id=request_id,
            model_name=model_name,
            model_version=model_version,
            input_data=input_data,
            preferred_location=preferred_location,
            priority=priority,
            max_latency_ms=max_latency_ms,
            fallback_enabled=fallback_enabled,
            metadata=metadata or {}
        )
        
        # Determine inference location
        location = await self._select_inference_location(request)
        
        # Execute inference
        if location == InferenceLocation.EDGE:
            result = await self._execute_edge_inference(request)
        else:
            result = await self._execute_cloud_inference(request)
        
        # Store result
        self._inference_history.append(result)
        
        return result
    
    async def _select_inference_location(
        self,
        request: InferenceRequest
    ) -> InferenceLocation:
        """Select the best inference location."""
        
        # Respect explicit preference
        if request.preferred_location == InferenceLocation.CLOUD:
            return InferenceLocation.CLOUD
        elif request.preferred_location == InferenceLocation.EDGE:
            # Check if edge is available
            if await self._is_edge_available(request.model_name):
                return InferenceLocation.EDGE
            elif request.fallback_enabled:
                return InferenceLocation.CLOUD
            else:
                raise RuntimeError("Edge not available and fallback disabled")
        
        # Auto selection logic
        # Check if model is available on edge
        edge_available = await self._is_edge_available(request.model_name)
        
        if not edge_available:
            return InferenceLocation.CLOUD
        
        # Check edge load
        edge_load = await self._get_edge_load(request.model_name)
        if edge_load > self._edge_load_threshold:
            return InferenceLocation.CLOUD
        
        # Check latency requirements
        if request.max_latency_ms and request.max_latency_ms < self._latency_threshold_ms:
            # Low latency requirement - prefer edge
            return InferenceLocation.EDGE
        
        # Default to edge for available models
        return InferenceLocation.EDGE
    
    async def _is_edge_available(self, model_name: str) -> bool:
        """Check if edge can run the model."""
        
        for capabilities in self.edge_capabilities.values():
            if capabilities.is_available and model_name in capabilities.available_models:
                return True
        
        return False
    
    async def _get_edge_load(self, model_name: str) -> float:
        """Get average load for edge devices with the model."""
        
        loads = [
            cap.current_load
            for cap in self.edge_capabilities.values()
            if model_name in cap.available_models and cap.is_available
        ]
        
        return sum(loads) / len(loads) if loads else 1.0
    
    async def _execute_cloud_inference(
        self,
        request: InferenceRequest
    ) -> InferenceResult:
        """Execute inference in the cloud."""
        
        if not self.cloud_inference_func:
            raise RuntimeError("Cloud inference not configured")
        
        start_time = time.time()
        
        try:
            output = await self.cloud_inference_func(
                model_name=request.model_name,
                model_version=request.model_version,
                input_data=request.input_data
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return InferenceResult(
                request_id=request.request_id,
                location=InferenceLocation.CLOUD,
                model_name=request.model_name,
                model_version=request.model_version,
                output=output,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Try fallback to edge if enabled
            if request.fallback_enabled and await self._is_edge_available(request.model_name):
                return await self._execute_edge_inference(request, fallback=True)
            
            return InferenceResult(
                request_id=request.request_id,
                location=InferenceLocation.CLOUD,
                model_name=request.model_name,
                model_version=request.model_version,
                output=None,
                latency_ms=latency_ms,
                error_message=str(e)
            )
    
    async def _execute_edge_inference(
        self,
        request: InferenceRequest,
        fallback: bool = False
    ) -> InferenceResult:
        """Execute inference on edge device."""
        
        # Select best edge device
        device_id = await self._select_edge_device(request.model_name)
        
        if not device_id:
            if request.fallback_enabled and not fallback:
                return await self._execute_cloud_inference(request)
            else:
                raise RuntimeError("No edge device available")
        
        start_time = time.time()
        
        try:
            # Send inference request to edge device
            # In production, this would use the heartbeat manager or direct connection
            output = await self._send_edge_inference_request(device_id, request)
            
            latency_ms = (time.time() - start_time) * 1000
            
            return InferenceResult(
                request_id=request.request_id,
                location=InferenceLocation.EDGE,
                model_name=request.model_name,
                model_version=request.model_version,
                output=output,
                latency_ms=latency_ms,
                fallback_used=fallback
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Try fallback to cloud if enabled
            if request.fallback_enabled and not fallback:
                return await self._execute_cloud_inference(request)
            
            return InferenceResult(
                request_id=request.request_id,
                location=InferenceLocation.EDGE,
                model_name=request.model_name,
                model_version=request.model_version,
                output=None,
                latency_ms=latency_ms,
                fallback_used=fallback,
                error_message=str(e)
            )
    
    async def _select_edge_device(self, model_name: str) -> Optional[str]:
        """Select the best edge device for inference."""
        
        candidates = [
            (device_id, cap)
            for device_id, cap in self.edge_capabilities.items()
            if cap.is_available and model_name in cap.available_models
        ]
        
        if not candidates:
            return None
        
        # Sort by load (lowest first)
        candidates.sort(key=lambda x: x[1].current_load)
        
        return candidates[0][0]
    
    async def _send_edge_inference_request(
        self,
        device_id: str,
        request: InferenceRequest
    ) -> Any:
        """Send inference request to edge device."""
        # Placeholder - in production, use WebSocket or gRPC
        # This would communicate with the edge device
        return {"result": "placeholder"}
    
    async def batch_infer(
        self,
        requests: List[InferenceRequest]
    ) -> List[InferenceResult]:
        """Perform batch inference."""
        
        # Group by location
        cloud_requests = []
        edge_requests = []
        
        for request in requests:
            location = await self._select_inference_location(request)
            if location == InferenceLocation.EDGE:
                edge_requests.append(request)
            else:
                cloud_requests.append(request)
        
        # Execute in parallel
        results = await asyncio.gather(
            *[self._execute_cloud_inference(r) for r in cloud_requests],
            *[self._execute_edge_inference(r) for r in edge_requests],
            return_exceptions=True
        )
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                req = cloud_requests[i] if i < len(cloud_requests) else edge_requests[i - len(cloud_requests)]
                processed_results.append(InferenceResult(
                    request_id=req.request_id,
                    location=InferenceLocation.CLOUD,
                    model_name=req.model_name,
                    model_version=req.model_version,
                    output=None,
                    latency_ms=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def get_inference_stats(
        self,
        model_name: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get inference statistics."""
        
        cutoff_time = datetime.utcnow() - __import__('datetime').timedelta(hours=time_window_hours)
        
        filtered_history = [
            r for r in self._inference_history
            if r.processed_at > cutoff_time
            and (not model_name or r.model_name == model_name)
        ]
        
        if not filtered_history:
            return {"total_requests": 0}
        
        cloud_results = [r for r in filtered_history if r.location == InferenceLocation.CLOUD]
        edge_results = [r for r in filtered_history if r.location == InferenceLocation.EDGE]
        
        return {
            "total_requests": len(filtered_history),
            "cloud_requests": len(cloud_results),
            "edge_requests": len(edge_results),
            "edge_percentage": len(edge_results) / len(filtered_history) * 100,
            "average_latency_ms": {
                "overall": sum(r.latency_ms for r in filtered_history) / len(filtered_history),
                "cloud": sum(r.latency_ms for r in cloud_results) / len(cloud_results) if cloud_results else 0,
                "edge": sum(r.latency_ms for r in edge_results) / len(edge_results) if edge_results else 0
            },
            "fallback_count": sum(1 for r in filtered_history if r.fallback_used),
            "error_count": sum(1 for r in filtered_history if r.error_message)
        }
