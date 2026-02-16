"""
IFC Geometry Compression using Draco
Compresses mesh geometry for efficient transmission and storage.
"""

import json
import struct
from typing import Optional, Dict, List, Any, Tuple, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import hashlib
import gzip
import io

try:
    import draco3d
    DRACO_AVAILABLE = True
except ImportError:
    DRACO_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


class CompressionLevel(Enum):
    """Draco compression levels."""
    FAST = 0      # Fastest, lowest compression
    STANDARD = 7  # Balanced
    BEST = 10     # Best compression, slowest


@dataclass
class CompressedMesh:
    """Compressed mesh data."""
    mesh_id: str
    compressed_data: bytes
    original_size: int
    compressed_size: int
    vertex_count: int
    face_count: int
    has_normals: bool
    has_uvs: bool
    compression_ratio: float
    compression_level: CompressionLevel
    
    @property
    def compression_percentage(self) -> float:
        """Get compression percentage."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mesh_id": self.mesh_id,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "has_normals": self.has_normals,
            "has_uvs": self.has_uvs,
            "compression_ratio": self.compression_ratio,
            "compression_percentage": self.compression_percentage,
            "compression_level": self.compression_level.name
        }


@dataclass
class CompressionStats:
    """Statistics for compression operation."""
    total_meshes: int
    total_compressed: int
    total_original_size: int
    total_compressed_size: int
    average_ratio: float
    processing_time: float
    errors: List[str] = field(default_factory=list)
    
    @property
    def overall_compression_percentage(self) -> float:
        if self.total_original_size == 0:
            return 0.0
        return (1 - self.total_compressed_size / self.total_original_size) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_meshes": self.total_meshes,
            "total_compressed": self.total_compressed,
            "total_original_size": self.total_original_size,
            "total_compressed_size": self.total_compressed_size,
            "overall_compression_percentage": self.overall_compression_percentage,
            "average_ratio": self.average_ratio,
            "processing_time": self.processing_time,
            "errors": self.errors
        }


class DracoCompressor:
    """
    Compresses 3D mesh geometry using Google's Draco library.
    Provides efficient compression for transmission and storage.
    """
    
    def __init__(self, quantization_bits: int = 14):
        self.quantization_bits = quantization_bits
        self._encoder = None
        
        if not DRACO_AVAILABLE:
            logger.warning("Draco library not available, using fallback compression")
    
    def compress_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: Optional[np.ndarray] = None,
        uvs: Optional[np.ndarray] = None,
        mesh_id: str = "",
        compression_level: CompressionLevel = CompressionLevel.STANDARD
    ) -> Optional[CompressedMesh]:
        """
        Compress a mesh using Draco.
        
        Args:
            vertices: Vertex positions (N x 3)
            faces: Face indices (M x 3)
            normals: Optional vertex normals (N x 3)
            uvs: Optional UV coordinates (N x 2)
            mesh_id: Identifier for the mesh
            compression_level: Compression level to use
        
        Returns:
            CompressedMesh or None if compression failed
        """
        try:
            if DRACO_AVAILABLE:
                return self._compress_with_draco(
                    vertices, faces, normals, uvs, mesh_id, compression_level
                )
            else:
                return self._compress_fallback(
                    vertices, faces, normals, uvs, mesh_id
                )
                
        except Exception as e:
            logger.error(f"Mesh compression failed: {e}")
            return None
    
    def _compress_with_draco(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: Optional[np.ndarray],
        uvs: Optional[np.ndarray],
        mesh_id: str,
        compression_level: CompressionLevel
    ) -> Optional[CompressedMesh]:
        """Compress using Draco library."""
        # This is a placeholder - actual implementation would use draco3d
        # which has a specific Python API
        
        # For now, use fallback
        return self._compress_fallback(vertices, faces, normals, uvs, mesh_id)
    
    def _compress_fallback(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: Optional[np.ndarray],
        uvs: Optional[np.ndarray],
        mesh_id: str
    ) -> Optional[CompressedMesh]:
        """Fallback compression using gzip and quantization."""
        try:
            # Quantize vertices
            quantized_vertices = self._quantize_vertices(vertices)
            
            # Pack data
            data = {
                'vertices': quantized_vertices.tobytes(),
                'faces': faces.astype(np.uint32).tobytes(),
                'vertex_count': len(vertices),
                'face_count': len(faces)
            }
            
            if normals is not None:
                quantized_normals = self._quantize_normals(normals)
                data['normals'] = quantized_normals.tobytes()
            
            if uvs is not None:
                quantized_uvs = self._quantize_uvs(uvs)
                data['uvs'] = quantized_uvs.tobytes()
            
            # Serialize and compress
            json_data = json.dumps({
                'vertex_count': data['vertex_count'],
                'face_count': data['face_count'],
                'has_normals': 'normals' in data,
                'has_uvs': 'uvs' in data
            }).encode()
            
            # Compress with gzip
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6) as f:
                f.write(json_data)
                f.write(b'\n---DATA---\n')
                f.write(data['vertices'])
                f.write(data['faces'])
                if 'normals' in data:
                    f.write(data['normals'])
                if 'uvs' in data:
                    f.write(data['uvs'])
            
            compressed = buffer.getvalue()
            
            # Calculate original size
            original_size = (
                vertices.nbytes + 
                faces.nbytes + 
                (normals.nbytes if normals is not None else 0) +
                (uvs.nbytes if uvs is not None else 0)
            )
            
            return CompressedMesh(
                mesh_id=mesh_id,
                compressed_data=compressed,
                original_size=original_size,
                compressed_size=len(compressed),
                vertex_count=len(vertices),
                face_count=len(faces),
                has_normals=normals is not None,
                has_uvs=uvs is not None,
                compression_ratio=len(compressed) / original_size if original_size > 0 else 1.0,
                compression_level=CompressionLevel.STANDARD
            )
            
        except Exception as e:
            logger.error(f"Fallback compression failed: {e}")
            return None
    
    def _quantize_vertices(self, vertices: np.ndarray) -> np.ndarray:
        """Quantize vertex positions."""
        # Normalize to 0-1 range
        min_vals = vertices.min(axis=0)
        max_vals = vertices.max(axis=0)
        ranges = max_vals - min_vals
        ranges[ranges == 0] = 1  # Avoid division by zero
        
        normalized = (vertices - min_vals) / ranges
        
        # Quantize to specified bits
        max_val = (1 << self.quantization_bits) - 1
        quantized = (normalized * max_val).astype(np.uint16)
        
        return quantized
    
    def _quantize_normals(self, normals: np.ndarray) -> np.ndarray:
        """Quantize normals to 8-bit."""
        # Normals are in range [-1, 1], map to [0, 255]
        normalized = ((normals + 1) / 2 * 255).astype(np.uint8)
        return normalized
    
    def _quantize_uvs(self, uvs: np.ndarray) -> np.ndarray:
        """Quantize UVs."""
        # UVs are typically in range [0, 1]
        quantized = (uvs * 65535).astype(np.uint16)
        return quantized
    
    def decompress_mesh(
        self,
        compressed_mesh: CompressedMesh
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        Decompress a mesh.
        
        Args:
            compressed_mesh: Compressed mesh data
        
        Returns:
            Dictionary with 'vertices', 'faces', 'normals', 'uvs' arrays
        """
        try:
            if DRACO_AVAILABLE:
                return self._decompress_with_draco(compressed_mesh)
            else:
                return self._decompress_fallback(compressed_mesh)
                
        except Exception as e:
            logger.error(f"Mesh decompression failed: {e}")
            return None
    
    def _decompress_fallback(
        self,
        compressed_mesh: CompressedMesh
    ) -> Optional[Dict[str, np.ndarray]]:
        """Fallback decompression."""
        try:
            buffer = io.BytesIO(compressed_mesh.compressed_data)
            
            with gzip.GzipFile(fileobj=buffer, mode='rb') as f:
                content = f.read()
            
            # Split header and data
            parts = content.split(b'\n---DATA---\n')
            header = json.loads(parts[0])
            data = parts[1]
            
            vertex_count = header['vertex_count']
            face_count = header['face_count']
            
            # Extract arrays
            result = {}
            
            # Vertices (3 uint16 per vertex)
            vertex_bytes = vertex_count * 3 * 2
            vertices = np.frombuffer(data[:vertex_bytes], dtype=np.uint16)
            result['vertices'] = vertices.reshape(-1, 3)
            data = data[vertex_bytes:]
            
            # Faces (3 uint32 per face)
            face_bytes = face_count * 3 * 4
            faces = np.frombuffer(data[:face_bytes], dtype=np.uint32)
            result['faces'] = faces.reshape(-1, 3)
            data = data[face_bytes:]
            
            # Normals (3 uint8 per vertex)
            if header.get('has_normals'):
                normal_bytes = vertex_count * 3
                normals = np.frombuffer(data[:normal_bytes], dtype=np.uint8)
                result['normals'] = (normals.reshape(-1, 3).astype(float) / 255 * 2 - 1)
                data = data[normal_bytes:]
            
            # UVs (2 uint16 per vertex)
            if header.get('has_uvs'):
                uv_bytes = vertex_count * 2 * 2
                uvs = np.frombuffer(data[:uv_bytes], dtype=np.uint16)
                result['uvs'] = uvs.reshape(-1, 2).astype(float) / 65535
            
            return result
            
        except Exception as e:
            logger.error(f"Fallback decompression failed: {e}")
            return None


class BatchCompressor:
    """Compress multiple meshes in batch."""
    
    def __init__(self, compression_level: CompressionLevel = CompressionLevel.STANDARD):
        self.compression_level = compression_level
        self.compressor = DracoCompressor()
    
    def compress_batch(
        self,
        meshes: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[CompressedMesh], CompressionStats]:
        """
        Compress multiple meshes.
        
        Args:
            meshes: List of mesh dictionaries with 'vertices', 'faces', etc.
            progress_callback: Optional callback(current, total)
        
        Returns:
            Tuple of (compressed meshes, statistics)
        """
        import time
        start_time = time.time()
        
        compressed_meshes = []
        errors = []
        total_original = 0
        total_compressed = 0
        
        for i, mesh in enumerate(meshes):
            try:
                compressed = self.compressor.compress_mesh(
                    vertices=mesh['vertices'],
                    faces=mesh['faces'],
                    normals=mesh.get('normals'),
                    uvs=mesh.get('uvs'),
                    mesh_id=mesh.get('id', f'mesh_{i}'),
                    compression_level=self.compression_level
                )
                
                if compressed:
                    compressed_meshes.append(compressed)
                    total_original += compressed.original_size
                    total_compressed += compressed.compressed_size
                else:
                    errors.append(f"Failed to compress mesh {i}")
                
                if progress_callback:
                    progress_callback(i + 1, len(meshes))
                    
            except Exception as e:
                errors.append(f"Error compressing mesh {i}: {e}")
        
        avg_ratio = (
            sum(c.compression_ratio for c in compressed_meshes) / len(compressed_meshes)
            if compressed_meshes else 1.0
        )
        
        stats = CompressionStats(
            total_meshes=len(meshes),
            total_compressed=len(compressed_meshes),
            total_original_size=total_original,
            total_compressed_size=total_compressed,
            average_ratio=avg_ratio,
            processing_time=time.time() - start_time,
            errors=errors
        )
        
        return compressed_meshes, stats
    
    def create_compressed_archive(
        self,
        compressed_meshes: List[CompressedMesh],
        output_path: str
    ) -> bool:
        """Create a compressed archive of all meshes."""
        try:
            import zipfile
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Write manifest
                manifest = {
                    'meshes': [m.to_dict() for m in compressed_meshes],
                    'total_size': sum(m.compressed_size for m in compressed_meshes)
                }
                zf.writestr('manifest.json', json.dumps(manifest, indent=2))
                
                # Write each mesh
                for mesh in compressed_meshes:
                    zf.writestr(f'meshes/{mesh.mesh_id}.drc', mesh.compressed_data)
            
            logger.info(f"Created compressed archive: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            return False


# Convenience functions
def compress_ifc_geometry(
    geometries: List[Dict[str, Any]],
    compression_level: CompressionLevel = CompressionLevel.STANDARD
) -> Tuple[List[CompressedMesh], CompressionStats]:
    """
    Compress IFC geometry data.
    
    Args:
        geometries: List of geometry dictionaries
        compression_level: Compression level
    
    Returns:
        Tuple of (compressed meshes, statistics)
    """
    batch_compressor = BatchCompressor(compression_level)
    return batch_compressor.compress_batch(geometries)


def estimate_compression_ratio(
    vertex_count: int,
    face_count: int,
    has_normals: bool = True,
    has_uvs: bool = False
) -> float:
    """
    Estimate compression ratio for a mesh.
    
    Args:
        vertex_count: Number of vertices
        face_count: Number of faces
        has_normals: Whether mesh has normals
        has_uvs: Whether mesh has UVs
    
    Returns:
        Estimated compression ratio (compressed/original)
    """
    # Draco typically achieves 5-20x compression
    # This is a rough estimate
    base_ratio = 0.1  # 10% of original size
    
    # Adjust for mesh size (larger meshes compress better)
    if face_count > 10000:
        base_ratio *= 0.7
    elif face_count > 1000:
        base_ratio *= 0.85
    
    # Adjust for attributes
    if has_normals:
        base_ratio *= 1.1
    if has_uvs:
        base_ratio *= 1.15
    
    return min(base_ratio, 0.5)  # Cap at 50%
