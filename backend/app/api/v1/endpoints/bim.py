"""
BIM API Endpoints
RESTful API for IFC/BIM operations including geometry, properties, and analysis.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User
from app.core.logging import get_logger
from app.pipelines.ifc_geometry import (
    extract_ifc_geometry, ExtractionResult, GeometryFormat
)
from app.pipelines.ifc_properties import (
    extract_ifc_properties, ElementProperties
)
from app.pipelines.ifc_spatial import (
    build_ifc_spatial_index, RTreeSpatialIndex, BoundingBox
)
from app.pipelines.ifc_takeoff import (
    generate_ifc_takeoff, ElementTakeoff
)
from app.pipelines.ifc_compression import compress_ifc_geometry
from app.pipelines.ifc_lod import generate_ifc_lods, LODLevel

logger = get_logger(__name__)
router = APIRouter(prefix="/bim", tags=["BIM"])

# Pydantic Models
class IFCUploadResponse(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    message: str


class GeometryExtractionRequest(BaseModel):
    file_id: str
    element_types: Optional[List[str]] = None
    output_format: str = "three_js"
    include_normals: bool = True
    include_uvs: bool = False


class GeometryResponse(BaseModel):
    file_id: str
    element_count: int
    total_vertices: int
    total_faces: int
    processing_time: float
    download_url: str


class PropertyExtractionRequest(BaseModel):
    file_id: str
    element_types: Optional[List[str]] = None
    include_quantities: bool = True


class SpatialQueryRequest(BaseModel):
    file_id: str
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


class SpatialQueryResponse(BaseModel):
    objects: List[Dict[str, Any]]
    count: int
    query_time_ms: float


class TakeoffRequest(BaseModel):
    file_id: str
    element_types: Optional[List[str]] = None
    include_calculated: bool = True
    output_format: str = "json"


class TakeoffResponse(BaseModel):
    file_id: str
    total_elements: int
    summary: Dict[str, Any]
    download_url: str


class ClashDetectionRequest(BaseModel):
    file_id: str
    tolerance: float = 0.001


class ClashDetectionResponse(BaseModel):
    file_id: str
    clash_count: int
    clashes: List[Dict[str, Any]]


class LODGenerationRequest(BaseModel):
    file_id: str
    element_types: Optional[List[str]] = None
    target_lods: List[int] = Field(default=[100, 200, 300, 400])


class LODGenerationResponse(BaseModel):
    file_id: str
    lod_levels: List[int]
    total_representations: int
    download_url: str


class CompressionRequest(BaseModel):
    file_id: str
    compression_level: str = "standard"


class CompressionResponse(BaseModel):
    file_id: str
    compression_ratio: float
    original_size: int
    compressed_size: int
    download_url: str


# File storage (would use S3/cloud storage in production)
UPLOAD_DIR = "/tmp/ifc_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_file_path(file_id: str) -> str:
    """Get full path for uploaded file."""
    return os.path.join(UPLOAD_DIR, f"{file_id}.ifc")


# Upload Endpoints
@router.post("/upload", response_model=IFCUploadResponse)
async def upload_ifc(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> IFCUploadResponse:
    """Upload an IFC file."""
    try:
        # Validate file extension
        if not file.filename.endswith('.ifc'):
            raise HTTPException(status_code=400, detail="File must be an IFC file")
        
        # Generate file ID
        file_id = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        file_path = get_file_path(file_id)
        
        # Save file
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Uploaded IFC file: {file.filename} ({len(content)} bytes)")
        
        return IFCUploadResponse(
            file_id=file_id,
            file_name=file.filename,
            file_size=len(content),
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Geometry Endpoints
@router.post("/geometry/extract", response_model=GeometryResponse)
async def extract_geometry(
    request: GeometryExtractionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> GeometryResponse:
    """Extract geometry from IFC file."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Extract geometry
        result = await extract_ifc_geometry(
            file_path,
            element_types=request.element_types
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail="Geometry extraction failed")
        
        # Export to requested format
        output_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_geometry.json")
        
        # Convert to output format
        geometry_data = {
            "file_id": request.file_id,
            "exported_at": datetime.utcnow().isoformat(),
            "elements": [g.to_dict() for g in result.geometries],
            "metadata": {
                "element_count": result.element_count,
                "total_vertices": result.total_vertices,
                "total_faces": result.total_faces,
                "processing_time": result.processing_time
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(geometry_data, f)
        
        return GeometryResponse(
            file_id=request.file_id,
            element_count=result.element_count,
            total_vertices=result.total_vertices,
            total_faces=result.total_faces,
            processing_time=result.processing_time,
            download_url=f"/api/v1/bim/download/{request.file_id}_geometry.json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geometry extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geometry/{file_id}")
async def get_geometry(
    file_id: str,
    element_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get extracted geometry data."""
    try:
        geometry_path = os.path.join(UPLOAD_DIR, f"{file_id}_geometry.json")
        
        if not os.path.exists(geometry_path):
            raise HTTPException(status_code=404, detail="Geometry not found")
        
        with open(geometry_path, 'r') as f:
            data = json.load(f)
        
        # Filter by element type if specified
        if element_type:
            data['elements'] = [
                e for e in data['elements']
                if e['element_type'] == element_type
            ]
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get geometry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Property Endpoints
@router.post("/properties/extract")
async def extract_properties(
    request: PropertyExtractionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Extract properties from IFC file."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Extract properties
        properties = await extract_ifc_properties(
            file_path,
            element_types=request.element_types
        )
        
        # Save to file
        output_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_properties.json")
        
        data = {
            "file_id": request.file_id,
            "exported_at": datetime.utcnow().isoformat(),
            "elements": [p.to_dict() for p in properties],
            "summary": {
                "total_elements": len(properties),
                "property_set_names": list(set(
                    ps.name for p in properties for ps in p.property_sets
                ))
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        return {
            "file_id": request.file_id,
            "total_elements": len(properties),
            "download_url": f"/api/v1/bim/download/{request.file_id}_properties.json"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Property extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Spatial Query Endpoints
@router.post("/spatial/query", response_model=SpatialQueryResponse)
async def spatial_query(
    request: SpatialQueryRequest,
    current_user: User = Depends(get_current_user)
) -> SpatialQueryResponse:
    """Query elements within spatial bounds."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Build or load spatial index
        index_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_spatial.idx")
        
        if os.path.exists(index_path):
            spatial_index = RTreeSpatialIndex.load(index_path)
        else:
            spatial_index = await build_ifc_spatial_index(file_path)
            spatial_index.save(index_path)
        
        # Execute query
        bbox = BoundingBox(
            min_x=request.min_x,
            min_y=request.min_y,
            min_z=request.min_z,
            max_x=request.max_x,
            max_y=request.max_y,
            max_z=request.max_z
        )
        
        import time
        start_time = time.time()
        
        results = spatial_index.intersects(bbox, objects_only=True)
        
        query_time = (time.time() - start_time) * 1000
        
        return SpatialQueryResponse(
            objects=[r.to_dict() for r in results if r],
            count=len(results),
            query_time_ms=query_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Spatial query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spatial/clash-detection", response_model=ClashDetectionResponse)
async def clash_detection(
    request: ClashDetectionRequest,
    current_user: User = Depends(get_current_user)
) -> ClashDetectionResponse:
    """Detect clashes between elements."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Build spatial index
        spatial_index = await build_ifc_spatial_index(file_path)
        
        # Find clashes
        clashes = spatial_index.find_clashes(tolerance=request.tolerance)
        
        clash_data = [
            {
                "element1": {
                    "global_id": c[0].global_id,
                    "name": c[0].name,
                    "type": c[0].element_type
                },
                "element2": {
                    "global_id": c[1].global_id,
                    "name": c[1].name,
                    "type": c[1].element_type
                },
                "overlap_volume": c[2]
            }
            for c in clashes
        ]
        
        return ClashDetectionResponse(
            file_id=request.file_id,
            clash_count=len(clashes),
            clashes=clash_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clash detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Takeoff Endpoints
@router.post("/takeoff/generate", response_model=TakeoffResponse)
async def generate_takeoff(
    request: TakeoffRequest,
    current_user: User = Depends(get_current_user)
) -> TakeoffResponse:
    """Generate quantity takeoff from IFC file."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Generate takeoff
        takeoffs = await generate_ifc_takeoff(
            file_path,
            element_types=request.element_types,
            include_calculated=request.include_calculated
        )
        
        # Save to file
        output_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_takeoff.json")
        
        from app.pipelines.ifc_takeoff import TakeoffSummary
        
        # Generate summary
        engine = __import__('app.pipelines.ifc_takeoff', fromlist=['QuantityTakeoffEngine']).QuantityTakeoffEngine(file_path)
        summary = engine.generate_summary(takeoffs)
        engine.close()
        
        data = {
            "file_id": request.file_id,
            "exported_at": datetime.utcnow().isoformat(),
            "elements": [t.to_dict() for t in takeoffs],
            "summary": summary.to_dict()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        return TakeoffResponse(
            file_id=request.file_id,
            total_elements=len(takeoffs),
            summary=summary.to_dict(),
            download_url=f"/api/v1/bim/download/{request.file_id}_takeoff.json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Takeoff generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# LOD Generation Endpoints
@router.post("/lod/generate", response_model=LODGenerationResponse)
async def generate_lods(
    request: LODGenerationRequest,
    current_user: User = Depends(get_current_user)
) -> LODGenerationResponse:
    """Generate LOD representations for IFC file."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Convert LOD levels
        target_lods = [LODLevel(l) for l in request.target_lods]
        
        # Generate LODs
        lods = await generate_ifc_lods(
            file_path,
            element_types=request.element_types,
            target_lods=target_lods
        )
        
        # Save to file
        output_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_lods.json")
        
        data = {
            "file_id": request.file_id,
            "generated_at": datetime.utcnow().isoformat(),
            "elements": [l.to_dict() for l in lods],
            "total_representations": sum(
                len(l.representations) for l in lods
            )
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        return LODGenerationResponse(
            file_id=request.file_id,
            lod_levels=request.target_lods,
            total_representations=data["total_representations"],
            download_url=f"/api/v1/bim/download/{request.file_id}_lods.json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LOD generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Compression Endpoints
@router.post("/compress", response_model=CompressionResponse)
async def compress_geometry(
    request: CompressionRequest,
    current_user: User = Depends(get_current_user)
) -> CompressionResponse:
    """Compress IFC geometry."""
    try:
        file_path = get_file_path(request.file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # First extract geometry
        result = await extract_ifc_geometry(file_path)
        
        if not result.success:
            raise HTTPException(status_code=500, detail="Geometry extraction failed")
        
        # Prepare geometry for compression
        geometries = [
            {
                'id': g.element_id,
                'vertices': g.vertices,
                'faces': g.faces,
                'normals': g.normals if len(g.normals) > 0 else None,
                'uvs': g.uvs if len(g.uvs) > 0 else None
            }
            for g in result.geometries
        ]
        
        # Compress
        from app.pipelines.ifc_compression import CompressionLevel
        
        compression_level = CompressionLevel[request.compression_level.upper()]
        compressed_meshes, stats = compress_ifc_geometry(
            geometries,
            compression_level
        )
        
        # Save compressed data
        output_path = os.path.join(UPLOAD_DIR, f"{request.file_id}_compressed.zip")
        
        from app.pipelines.ifc_compression import BatchCompressor
        compressor = BatchCompressor()
        compressor.create_compressed_archive(compressed_meshes, output_path)
        
        return CompressionResponse(
            file_id=request.file_id,
            compression_ratio=stats.average_ratio,
            original_size=stats.total_original_size,
            compressed_size=stats.total_compressed_size,
            download_url=f"/api/v1/bim/download/{request.file_id}_compressed.zip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Download Endpoints
@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Download a generated file."""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# File Management Endpoints
@router.get("/files")
async def list_files(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List uploaded IFC files."""
    try:
        files = []
        
        for filename in os.listdir(UPLOAD_DIR):
            if filename.endswith('.ifc'):
                file_path = os.path.join(UPLOAD_DIR, filename)
                stat = os.stat(file_path)
                
                # Check if belongs to current user
                if filename.startswith(str(current_user.id)):
                    files.append({
                        "file_id": filename.replace('.ifc', ''),
                        "file_name": filename,
                        "file_size": stat.st_size,
                        "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return sorted(files, key=lambda x: x['uploaded_at'], reverse=True)
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete an uploaded file and its derivatives."""
    try:
        # Check ownership
        if not file_id.startswith(str(current_user.id)):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Delete main file
        file_path = get_file_path(file_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete derivatives
        for suffix in ['_geometry.json', '_properties.json', '_takeoff.json', 
                       '_lods.json', '_spatial.idx', '_compressed.zip']:
            derivative_path = os.path.join(UPLOAD_DIR, f"{file_id}{suffix}")
            if os.path.exists(derivative_path):
                os.remove(derivative_path)
        
        return {"success": True, "message": "File deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Metadata Endpoints
@router.get("/metadata/{file_id}")
async def get_metadata(
    file_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get IFC file metadata."""
    try:
        file_path = get_file_path(file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Extract metadata
        from app.pipelines.ifc_geometry import IFCGeometryExtractor
        
        extractor = IFCGeometryExtractor(file_path)
        extractor.open_file()
        metadata = extractor.get_file_metadata()
        extractor.close()
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
