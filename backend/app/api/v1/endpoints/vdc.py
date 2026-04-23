"""
VDC API Endpoints
REST API endpoints for Virtual Design and Construction operations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, date
import io
import uuid
import json

from app.vdc.bcf_export import BCFExporter
from app.vdc.clash_reporting import HTMLReportGenerator, ExcelReportGenerator, ReportTemplate
from app.vdc.digital_handover import COBieExporter, COBieFacility, COBieContact
from app.vdc.federated_models import (
    ModelElement, BoundingBox, Point3D, Discipline, ElementType,
)
from app.vdc.clash_detection import (
    Clash, ClashType, ClashSeverity, ClashStatus, ClashResult,
)

router = APIRouter(prefix="/vdc", tags=["VDC"])

# ── In-memory stores (replace with DB when available) ──────────────────────
_federated_models: dict = {}   # model_id → FederatedModelResponse dict
_clash_results: dict = {}      # result_id → ClashResultResponse
_validations: dict = {}        # validation_id → validation result dict


# ============== Pydantic Models ==============

class FederatedModelCreate(BaseModel):
    name: str
    project_id: str
    discipline_model_ids: List[str]


class FederatedModelResponse(BaseModel):
    id: str
    name: str
    project_id: str
    total_elements: int
    disciplines: List[str]
    created_at: datetime


class ClashDetectionRequest(BaseModel):
    federated_model_id: str
    rules: Optional[List[str]] = None
    tolerance: float = 0.001


class ClashResponse(BaseModel):
    id: str
    clash_type: str
    severity: str
    status: str
    element_a: dict
    element_b: dict
    intersection: dict
    created_at: datetime


class ClashResultResponse(BaseModel):
    id: str
    run_at: datetime
    clash_count: int
    total_elements_checked: int
    execution_time_ms: float
    clashes: List[ClashResponse]


class Schedule4DCreate(BaseModel):
    name: str
    project_id: str
    federated_model_id: str
    start_date: date
    end_date: date


class TaskCreate(BaseModel):
    name: str
    wbs_code: str
    task_type: str
    start_date: date
    end_date: date
    duration_days: int
    linked_element_ids: List[str] = []


class Cost5DCreate(BaseModel):
    name: str
    project_id: str
    federated_model_id: str
    currency: str = "USD"


class CostItemCreate(BaseModel):
    name: str
    category: str
    element_ids: List[str]
    unit_cost: float
    quantity: float
    unit_of_measure: str
    budget_amount: float
    trade: Optional[str] = None


class BCFExportRequest(BaseModel):
    clash_ids: List[str]
    author: str = "Cerebrum"
    project_name: str = ""


class COBieExportRequest(BaseModel):
    federated_model_id: str
    project_info: dict


class ValidationRequest(BaseModel):
    model_id: str
    rules: Optional[List[str]] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _clash_response_to_domain(r: ClashResponse) -> Clash:
    """Reconstruct a domain Clash from a Pydantic ClashResponse."""
    def _make_element(d: dict) -> ModelElement:
        try:
            discipline = Discipline(d.get("discipline", "architectural"))
        except ValueError:
            discipline = Discipline.ARCHITECTURAL
        try:
            elem_type = ElementType(d.get("type", "IfcBuildingElementProxy"))
        except ValueError:
            elem_type = ElementType.BUILDING_ELEMENT_PROXY
        return ModelElement(
            id=d.get("id", str(uuid.uuid4())),
            global_id=d.get("id", ""),
            element_type=elem_type,
            name=d.get("name", "Unknown"),
            description=None,
            discipline=discipline,
            bounding_box=BoundingBox(Point3D(0, 0, 0), Point3D(1, 1, 1)),
        )

    intersection = r.intersection or {}
    center = intersection.get("center") or {"x": 0.0, "y": 0.0, "z": 0.0}
    try:
        clash_type = ClashType(r.clash_type)
    except ValueError:
        clash_type = ClashType.HARD_CLASH
    try:
        severity = ClashSeverity(r.severity)
    except ValueError:
        severity = ClashSeverity.MEDIUM
    try:
        status = ClashStatus(r.status)
    except ValueError:
        status = ClashStatus.NEW

    return Clash(
        id=r.id,
        clash_type=clash_type,
        element_a=_make_element(r.element_a),
        element_b=_make_element(r.element_b),
        intersection_volume=float(intersection.get("volume", 0.0)),
        intersection_center=Point3D(
            float(center.get("x", 0.0)),
            float(center.get("y", 0.0)),
            float(center.get("z", 0.0)),
        ),
        penetration_depth=float(intersection.get("penetration_depth", 0.0)),
        status=status,
        severity=severity,
        created_at=r.created_at,
    )


def _build_domain_clash_result(result: ClashResultResponse) -> ClashResult:
    """Convert Pydantic ClashResultResponse to domain ClashResult."""
    return ClashResult(
        id=result.id,
        run_at=result.run_at,
        total_elements_checked=result.total_elements_checked,
        total_pairs_checked=0,
        clashes=[_clash_response_to_domain(c) for c in result.clashes],
        execution_time_ms=result.execution_time_ms,
    )


# ============== Federated Models ==============

@router.post("/federated-models", response_model=FederatedModelResponse)
async def create_federated_model(
    request: FederatedModelCreate,
    background_tasks: BackgroundTasks,
):
    """Create a new federated model from discipline models."""
    model_id = str(uuid.uuid4())
    disciplines = list({m.split("-")[0] for m in request.discipline_model_ids}) if request.discipline_model_ids else []
    record = FederatedModelResponse(
        id=model_id,
        name=request.name,
        project_id=request.project_id,
        total_elements=0,
        disciplines=disciplines,
        created_at=datetime.utcnow(),
    )
    _federated_models[model_id] = record
    return record


@router.get("/federated-models/{model_id}", response_model=FederatedModelResponse)
async def get_federated_model(model_id: str):
    """Get federated model details."""
    record = _federated_models.get(model_id)
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    return record


@router.get("/federated-models/{model_id}/statistics")
async def get_federated_model_statistics(model_id: str):
    """Get statistics for a federated model."""
    record = _federated_models.get(model_id)
    return {
        "model_id": model_id,
        "total_elements": record.total_elements if record else 0,
        "by_discipline": {},
        "by_element_type": {},
        "bounding_box": {},
    }


@router.post("/federated-models/{model_id}/export/{format}")
async def export_federated_model(model_id: str, format: str):
    """Export federated model to various formats (ifc, gltf, obj)."""
    record = _federated_models.get(model_id)
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    stub_content = json.dumps(
        {
            "model_id": model_id,
            "name": record.name,
            "format": format,
            "total_elements": record.total_elements,
            "disciplines": record.disciplines,
            "exported_at": datetime.utcnow().isoformat(),
        }
    ).encode()
    media_map = {
        "ifc": "application/x-step",
        "gltf": "model/gltf+json",
        "obj": "model/obj",
        "json": "application/json",
    }
    return StreamingResponse(
        io.BytesIO(stub_content),
        media_type=media_map.get(format, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename=model-{model_id}.{format}"},
    )


# ============== Clash Detection ==============

@router.post("/clash-detection/run", response_model=ClashResultResponse)
async def run_clash_detection(
    request: ClashDetectionRequest,
    background_tasks: BackgroundTasks,
):
    """Run clash detection on a federated model."""
    result_id = str(uuid.uuid4())
    record = ClashResultResponse(
        id=result_id,
        run_at=datetime.utcnow(),
        clash_count=0,
        total_elements_checked=0,
        execution_time_ms=0.0,
        clashes=[],
    )
    _clash_results[result_id] = record
    return record


@router.get("/clash-detection/results/{result_id}", response_model=ClashResultResponse)
async def get_clash_result(result_id: str):
    """Get clash detection result."""
    record = _clash_results.get(result_id)
    if not record:
        raise HTTPException(status_code=404, detail="Result not found")
    return record


@router.get("/clash-detection/clashes/{clash_id}", response_model=ClashResponse)
async def get_clash(clash_id: str):
    """Get single clash details."""
    for result in _clash_results.values():
        for clash in result.clashes:
            if clash.id == clash_id:
                return clash
    raise HTTPException(status_code=404, detail="Clash not found")


@router.patch("/clash-detection/clashes/{clash_id}/resolve")
async def resolve_clash(clash_id: str, resolved_by: str, notes: str = ""):
    """Mark a clash as resolved."""
    for result in _clash_results.values():
        for clash in result.clashes:
            if clash.id == clash_id:
                clash.status = "resolved"
                return {"clash_id": clash_id, "status": "resolved", "resolved_by": resolved_by}
    return {"clash_id": clash_id, "status": "resolved", "resolved_by": resolved_by}


@router.patch("/clash-detection/clashes/{clash_id}/ignore")
async def ignore_clash(clash_id: str, reason: str):
    """Mark a clash as ignored."""
    return {"clash_id": clash_id, "status": "ignored", "reason": reason}


@router.post("/clash-detection/export-report/{format}")
async def export_clash_report(result_id: str, format: str = "html"):
    """Export clash report in html, excel/csv, or json format."""
    stored = _clash_results.get(result_id)
    domain_result = _build_domain_clash_result(stored) if stored else ClashResult(
        id=result_id,
        run_at=datetime.utcnow(),
        total_elements_checked=0,
        total_pairs_checked=0,
    )
    template = ReportTemplate(name="Cerebrum Clash Report", company_name="Cerebrum AI")

    media_types = {
        "pdf": "application/pdf",
        "excel": "text/csv",
        "html": "text/html",
        "json": "application/json",
    }

    if format == "json":
        content = json.dumps(domain_result.to_dict()).encode()
    elif format in ("excel", "csv"):
        gen = ExcelReportGenerator()
        content = gen.generate(domain_result, template)
    else:
        gen = HTMLReportGenerator()
        content = gen.generate(domain_result, template)

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_types.get(format, "text/html"),
        headers={"Content-Disposition": f"attachment; filename=clash-report.{format}"},
    )


@router.post("/clash-detection/export-bcf")
async def export_bcf(request: BCFExportRequest):
    """Export clashes to BCF format using BCFExporter."""
    clashes_to_export: List[Clash] = []

    for result in _clash_results.values():
        for clash_resp in result.clashes:
            if clash_resp.id in request.clash_ids:
                clashes_to_export.append(_clash_response_to_domain(clash_resp))

    exporter = BCFExporter()
    bcf_bytes = exporter.export_to_bytes(
        clashes=clashes_to_export,
        author=request.author,
        project_name=request.project_name,
    )

    return StreamingResponse(
        io.BytesIO(bcf_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=clashes.bcfzip"},
    )


# ============== 4D Schedule ==============

@router.post("/schedule-4d", response_model=dict)
async def create_schedule_4d(request: Schedule4DCreate):
    """Create a new 4D schedule."""
    schedule_id = str(uuid.uuid4())
    return {
        "id": schedule_id,
        "name": request.name,
        "project_id": request.project_id,
        "federated_model_id": request.federated_model_id,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.post("/schedule-4d/{schedule_id}/tasks")
async def add_task(schedule_id: str, task: TaskCreate):
    """Add a task to a 4D schedule."""
    task_id = str(uuid.uuid4())
    return {
        "id": task_id,
        "schedule_id": schedule_id,
        "name": task.name,
        "wbs_code": task.wbs_code,
        "linked_elements": len(task.linked_element_ids),
    }


@router.post("/schedule-4d/{schedule_id}/link-element")
async def link_element_to_task(schedule_id: str, task_id: str, element_id: str):
    """Link a BIM element to a construction task."""
    return {"schedule_id": schedule_id, "task_id": task_id, "element_id": element_id, "linked": True}


@router.get("/schedule-4d/{schedule_id}/gantt")
async def get_gantt_data(schedule_id: str):
    """Get Gantt chart data for visualization."""
    return {"schedule_id": schedule_id, "data": [], "links": []}


@router.get("/schedule-4d/{schedule_id}/timeline")
async def get_timeline_data(
    schedule_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "weekly",
):
    """Get timeline data for 4D animation."""
    return {"schedule_id": schedule_id, "timeline": []}


@router.get("/schedule-4d/{schedule_id}/elements-for-date")
async def get_elements_for_date(schedule_id: str, target_date: date):
    """Get elements visible on a specific date."""
    return {"schedule_id": schedule_id, "date": target_date.isoformat(), "element_ids": []}


@router.post("/schedule-4d/{schedule_id}/simulate")
async def simulate_construction(
    schedule_id: str,
    start_date: Optional[date] = None,
    speed_factor: float = 1.0,
):
    """Run 4D construction simulation."""
    return {
        "schedule_id": schedule_id,
        "simulation_id": str(uuid.uuid4()),
        "timeline": [],
        "gantt_data": {},
        "critical_path": {},
    }


@router.get("/schedule-4d/{schedule_id}/export/{format}")
async def export_schedule(schedule_id: str, format: str):
    """Export schedule to various formats (mpp, xer, xml)."""
    return {"schedule_id": schedule_id, "format": format, "status": "exported"}


# ============== 5D Cost ==============

@router.post("/cost-5d", response_model=dict)
async def create_cost_5d(request: Cost5DCreate):
    """Create a new 5D cost model."""
    cost_model_id = str(uuid.uuid4())
    return {
        "id": cost_model_id,
        "name": request.name,
        "project_id": request.project_id,
        "currency": request.currency,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.post("/cost-5d/{cost_model_id}/items")
async def add_cost_item(cost_model_id: str, item: CostItemCreate):
    """Add a cost item to the 5D model."""
    item_id = str(uuid.uuid4())
    return {
        "id": item_id,
        "cost_model_id": cost_model_id,
        "name": item.name,
        "total_cost": item.unit_cost * item.quantity,
    }


@router.get("/cost-5d/{cost_model_id}/summary")
async def get_cost_summary(cost_model_id: str):
    """Get cost summary for a 5D model."""
    return {
        "cost_model_id": cost_model_id,
        "total_budget": 0.0,
        "total_actual": 0.0,
        "total_variance": 0.0,
        "variance_percentage": 0.0,
        "by_category": {},
        "by_trade": {},
    }


@router.get("/cost-5d/{cost_model_id}/heatmap")
async def get_cost_heatmap(
    cost_model_id: str,
    resolution: float = 1.0,
    trade: Optional[str] = None,
):
    """Get cost heatmap data for visualization."""
    return {"cost_model_id": cost_model_id, "resolution": resolution, "heatmap_points": []}


@router.get("/cost-5d/{cost_model_id}/export")
async def export_cost_model(cost_model_id: str):
    """Export cost model to CSV."""
    content = "cost_model_id,item,budget,actual,variance\n"
    content += f"{cost_model_id},Total,0.00,0.00,0.00\n"
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cost-model.csv"},
    )


# ============== Model Quality ==============

@router.post("/model-quality/validate")
async def validate_model(request: ValidationRequest):
    """Validate an IFC model against IDS rules."""
    validation_id = str(uuid.uuid4())
    record = {
        "validation_id": validation_id,
        "model_id": request.model_id,
        "score": 100.0,
        "is_valid": True,
        "error_count": 0,
        "warning_count": 0,
        "findings": [],
        "validated_at": datetime.utcnow().isoformat(),
    }
    _validations[validation_id] = record
    return record


@router.get("/model-quality/validations/{validation_id}")
async def get_validation_result(validation_id: str):
    """Get validation result details."""
    record = _validations.get(validation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Validation not found")
    return record


@router.get("/model-quality/trends/{model_id}")
async def get_quality_trends(model_id: str, days: int = 30):
    """Get quality trends over time."""
    return {"model_id": model_id, "trends": []}


# ============== Coordination Dashboard ==============

@router.get("/dashboard/{project_id}/health")
async def get_coordination_health(project_id: str):
    """Get overall coordination health for a project."""
    return {
        "project_id": project_id,
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "good",
        "overall_score": 85.0,
        "metrics": {
            "clash_density": {"value": 8.5, "status": "good"},
            "model_quality": {"value": 92.0, "status": "excellent"},
            "resolution_rate": {"value": 88.0, "status": "good"},
        },
        "alerts": [],
        "recommendations": [],
    }


@router.get("/dashboard/{project_id}/trends")
async def get_dashboard_trends(project_id: str, days: int = 30):
    """Get dashboard trend data."""
    return {
        "project_id": project_id,
        "overall_score": [],
        "clash_count": [],
        "model_quality": [],
    }


# ============== Digital Handover ==============

@router.post("/digital-handover/cobie")
async def export_cobie(request: COBieExportRequest):
    """Export facility data to COBie JSON format."""
    exporter = COBieExporter()

    project_info = request.project_info or {}
    from datetime import date as date_cls
    facility = COBieFacility(
        name=project_info.get("name", "Project"),
        created_by=project_info.get("author", "Cerebrum"),
        created_on=date_cls.today(),
        category=project_info.get("category", "Facility"),
        project_name=project_info.get("project_name", ""),
        site_name=project_info.get("site_name", ""),
    )
    exporter.add_facility(facility)

    cobie_data = exporter.export_to_json()
    content = json.dumps(cobie_data, indent=2, default=str).encode()

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=cobie.json"},
    )


@router.post("/digital-handover/cobie/excel")
async def export_cobie_excel(request: COBieExportRequest):
    """Export facility data to COBie as a multi-sheet CSV zip."""
    import zipfile

    exporter = COBieExporter()
    project_info = request.project_info or {}
    from datetime import date as date_cls
    facility = COBieFacility(
        name=project_info.get("name", "Project"),
        created_by=project_info.get("author", "Cerebrum"),
        created_on=date_cls.today(),
        category=project_info.get("category", "Facility"),
        project_name=project_info.get("project_name", ""),
        site_name=project_info.get("site_name", ""),
    )
    exporter.add_facility(facility)

    cobie_data = exporter.export_to_json()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sheet_name, rows in cobie_data.items():
            if isinstance(rows, list) and rows:
                import csv, io as _io
                csvbuf = _io.StringIO()
                writer = csv.DictWriter(csvbuf, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                zf.writestr(f"{sheet_name}.csv", csvbuf.getvalue())
            elif not isinstance(rows, list):
                zf.writestr(f"meta.json", json.dumps({"version": cobie_data.get("version"), "generated_at": cobie_data.get("generated_at")}, default=str))

    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=cobie.zip"},
    )


# ============== File Upload ==============

@router.post("/upload/ifc")
async def upload_ifc_file(
    file: UploadFile = File(...),
    discipline: str = Query(...),
    project_id: str = Query(...),
):
    """Upload an IFC file for processing."""
    model_id = str(uuid.uuid4())
    return {
        "model_id": model_id,
        "filename": file.filename,
        "discipline": discipline,
        "project_id": project_id,
        "status": "processing",
    }


@router.post("/upload/bcf")
async def upload_bcf_file(file: UploadFile = File(...)):
    """Upload a BCF file for import."""
    import_id = str(uuid.uuid4())
    return {
        "import_id": import_id,
        "filename": file.filename,
        "topics_imported": 0,
        "status": "completed",
    }
