"""
BIM API Endpoints - IFC File Processing
Handles IFC file upload, geometry extraction, quantity takeoff
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings

# Conditional import for IFC processing - installed via conda
IFC_AVAILABLE = False
QuantityTakeoffEngine = None
IFCPropertyExtractor = None
generate_ifc_takeoff = None

try:
    import ifcopenshell
    from app.pipelines.ifc_takeoff import QuantityTakeoffEngine, generate_ifc_takeoff
    from app.pipelines.ifc_properties import IFCPropertyExtractor
    IFC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"IFC processing not available: {e}")

try:
    from app.api.deps import get_current_user, User
except ImportError:
    from app.core.deps import get_current_user
    User = dict

router = APIRouter(prefix="/bim", tags=["bim"])

# File storage setup - use config with env fallback
UPLOAD_DIR = Path(settings.BIM_UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Check if IFC processing is enabled via config
IFC_PROCESSING_ENABLED = settings.IFC_PROCESSING_ENABLED and IFC_AVAILABLE

# In-memory storage for demo (replace with DB in production)
_uploaded_files: Dict[str, Dict] = {}


class BIMUploadResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    message: str


class BIMElementResponse(BaseModel):
    element_id: str
    element_type: str
    properties: Dict[str, Any]


class BIMTakeoffResponse(BaseModel):
    file_id: str
    quantities: Dict[str, Any]
    total_elements: int


def _check_ifc_available():
    """Check if IFC processing is available."""
    if not IFC_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="IFC processing not available. ifcopenshell-python not installed or disabled in config."
        )


@router.post("/upload", response_model=BIMUploadResponse)
async def upload_ifc_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload an IFC file for processing"""
    if not file.filename.endswith('.ifc'):
        raise HTTPException(status_code=400, detail="Only .ifc files allowed")
    
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        _uploaded_files[file_id] = {
            "id": file_id,
            "filename": file.filename,
            "path": str(file_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "uploaded",
            "user_id": str(current_user.id) if hasattr(current_user, 'id') else 'anonymous'
        }
        
        return BIMUploadResponse(
            file_id=file_id,
            filename=file.filename,
            status="uploaded",
            message="File uploaded successfully. Process with /takeoff endpoint."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{file_id}/status")
async def get_file_status(file_id: str, current_user = Depends(get_current_user)):
    """Get processing status of uploaded file"""
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    return _uploaded_files[file_id]


@router.delete("/files/{file_id}")
async def delete_ifc_file(file_id: str, current_user = Depends(get_current_user)):
    """Delete uploaded IFC file"""
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = _uploaded_files[file_id]
    try:
        Path(file_info["path"]).unlink(missing_ok=True)
        del _uploaded_files[file_id]
        return {"message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.post("/files/{file_id}/takeoff", response_model=BIMTakeoffResponse)
async def generate_takeoff(
    file_id: str,
    element_types: Optional[List[str]] = None,
    current_user = Depends(get_current_user)
):
    """Generate quantity takeoff from IFC file"""
    _check_ifc_available()
    
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = _uploaded_files[file_id]
    file_path = file_info["path"]
    
    try:
        engine = QuantityTakeoffEngine(file_path)
        takeoffs = engine.generate_takeoff(element_types=element_types)
        summary = engine.generate_summary(takeoffs)
        engine.close()
        
        # Update file status
        _uploaded_files[file_id]["status"] = "processed"
        _uploaded_files[file_id]["takeoff_summary"] = summary.to_dict()
        
        return BIMTakeoffResponse(
            file_id=file_id,
            quantities=summary.to_dict(),
            total_elements=len(takeoffs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Takeoff failed: {str(e)}")


@router.get("/files/{file_id}/takeoff")
async def get_takeoff(file_id: str, current_user = Depends(get_current_user)):
    """Get quantity takeoff results"""
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = _uploaded_files[file_id]
    if "takeoff_summary" not in file_info:
        raise HTTPException(status_code=400, detail="Takeoff not generated yet. Use POST first.")
    
    return {
        "file_id": file_id,
        "quantities": file_info["takeoff_summary"],
        "status": file_info.get("status", "unknown")
    }


@router.get("/files/{file_id}/elements")
async def list_ifc_elements(
    file_id: str,
    element_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user = Depends(get_current_user)
):
    """List elements from IFC file"""
    _check_ifc_available()
    
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = _uploaded_files[file_id]["path"]
    
    try:
        extractor = IFCPropertyExtractor(file_path)
        extractor.open_file()
        
        # Get elements
        if element_type:
            elements = extractor.ifc_file.by_type(element_type)
        else:
            elements = extractor.ifc_file.by_type('IfcElement')
        
        total = len(elements)
        elements = elements[offset:offset + limit]
        
        result = []
        for elem in elements:
            props = extractor.extract_element_properties(elem)
            result.append({
                "element_id": str(elem.id()),
                "global_id": elem.GlobalId,
                "element_type": elem.is_a(),
                "name": getattr(elem, 'Name', ''),
                "properties": props.to_dict() if hasattr(props, 'to_dict') else {}
            })
        
        extractor.close()
        
        return {
            "elements": result,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Element extraction failed: {str(e)}")


@router.get("/files/{file_id}/properties")
async def get_all_properties(file_id: str, current_user = Depends(get_current_user)):
    """Get all properties from IFC file"""
    _check_ifc_available()
    
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = _uploaded_files[file_id]["path"]
    
    try:
        extractor = IFCPropertyExtractor(file_path)
        properties = extractor.extract_all_properties()
        extractor.close()
        
        return {
            "file_id": file_id,
            "property_count": len(properties),
            "properties": properties[:100]  # Limit for response size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property extraction failed: {str(e)}")


@router.get("/files/{file_id}/rooms")
async def list_rooms(file_id: str, current_user = Depends(get_current_user)):
    """List all rooms/spaces in IFC file"""
    _check_ifc_available()
    
    if file_id not in _uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = _uploaded_files[file_id]["path"]
    
    try:
        extractor = IFCPropertyExtractor(file_path)
        extractor.open_file()
        
        spaces = extractor.ifc_file.by_type('IfcSpace')
        rooms = []
        for space in spaces:
            rooms.append({
                "id": str(space.id()),
                "global_id": space.GlobalId,
                "name": getattr(space, 'Name', ''),
                "long_name": getattr(space, 'LongName', '')
            })
        
        extractor.close()
        return {"rooms": rooms, "count": len(rooms)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Room extraction failed: {str(e)}")


# Stub endpoints that need more implementation
@router.get("/files/{file_id}/geometry")
async def get_ifc_geometry(file_id: str, format: str = "glb", lod: int = 1):
    raise HTTPException(status_code=501, detail="Geometry export not yet implemented")


@router.post("/clash-detection")
async def run_clash_detection(file_id_1: str, file_id_2: str):
    raise HTTPException(status_code=501, detail="Clash detection not yet implemented")


@router.post("/files/{file_id}/compress")
async def compress_ifc(file_id: str, method: str = "draco"):
    raise HTTPException(status_code=501, detail="Compression not yet implemented")


__all__ = ["router"]
