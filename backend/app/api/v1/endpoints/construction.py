"""
Construction Domain API Endpoints
Complete AEC suite exposed via REST API.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.block_registry import BLOCK_REGISTRY
from app.core.logging import get_logger

# Trigger construction block self-registration on import
import app.containers.construction  # noqa: F401

logger = get_logger(__name__)
router = APIRouter(prefix="/construction", tags=["construction"])


# ═══════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════

class ConstructionActionRequest(BaseModel):
    action: str = Field(..., description="Action name to execute")
    input_data: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)


class ContractAnalysisRequest(BaseModel):
    contract_type: str = "general"


class ScheduleAnalysisRequest(BaseModel):
    baseline_file: Optional[str] = None
    analysis_date: Optional[str] = None
    include_details: bool = False


class SpecificationRequest(BaseModel):
    division: Optional[str] = None
    full_details: bool = False


class ChangeOrderRequest(BaseModel):
    description: str
    value: float = 0.0
    affected_activities: List[str] = Field(default_factory=list)
    schedule_file: Optional[str] = None
    contract_file: Optional[str] = None


class RFIRequest(BaseModel):
    description: str
    drawing_reference: Optional[str] = None
    spec_reference: Optional[str] = None
    priority: str = "normal"
    trade: str = "general"
    project_name: str = "Project"


class SafetyAuditRequest(BaseModel):
    audit_type: str = "general"
    location: str = "US"
    checklist_items: List[Dict[str, Any]] = Field(default_factory=list)


class CarbonCalcRequest(BaseModel):
    boq: List[Dict[str, Any]] = Field(default_factory=list)
    materials: List[Dict[str, Any]] = Field(default_factory=list)
    assessment_type: str = "cradle_to_gate"
    building_type: str = "office"


class ProcurementRequest(BaseModel):
    boq: List[Dict[str, Any]] = Field(default_factory=list)
    project_start_date: Optional[str] = None
    schedule_file: Optional[str] = None
    strategy: str = "just_in_time"


class DeviationReportRequest(BaseModel):
    original_drawings: List[str]
    photos: List[str] = Field(default_factory=list)


class WarrantyRequest(BaseModel):
    equipment_list: List[Dict[str, Any]] = Field(default_factory=list)
    substantial_completion_date: Optional[str] = None


class RiskRegisterRequest(BaseModel):
    drawings: List[str] = Field(default_factory=list)
    spec_file: Optional[str] = None
    schedule_file: Optional[str] = None
    contract_file: Optional[str] = None
    site_photos: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _get_block():
    block = BLOCK_REGISTRY.get("construction")
    if not block:
        raise HTTPException(status_code=503, detail="Construction block not loaded")
    return block


async def _save_upload(file: UploadFile) -> str:
    """Persist uploaded file to a temporary path and return the path."""
    suffix = Path(file.filename or "upload").suffix
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return tmp_path


def _safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# Generic Executor
# ═══════════════════════════════════════════════════════════

@router.post("/execute")
async def execute_action(
    req: ConstructionActionRequest,
    user=Depends(get_current_user),
):
    """Execute any construction block action by name."""
    block = _get_block()
    result = await block.execute(req.action, req.input_data, req.params)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result


@router.get("/actions")
async def list_actions(user=Depends(get_current_user)):
    """List available actions in the construction block."""
    block = _get_block()
    actions = list(block.get_actions().keys())
    return {"status": "success", "actions": actions, "version": block.config.version}


# ═══════════════════════════════════════════════════════════
# 1. Document Processing
# ═══════════════════════════════════════════════════════════

@router.post("/document")
async def process_document(
    doc_type: str = Form("auto"),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload and process a construction document (drawing, spec, schedule, contract)."""
    tmp_path = await _save_upload(file)
    try:
        block = _get_block()
        result = await block.process_document(
            {"file_path": tmp_path},
            {"doc_type": doc_type}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Processing failed"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 2. Contract Analysis
# ═══════════════════════════════════════════════════════════

@router.post("/contract")
async def analyze_contract(
    contract_type: str = Form("general"),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    tmp_path = await _save_upload(file)
    try:
        block = _get_block()
        result = await block.process_contract(
            {"file_path": tmp_path},
            {"contract_type": contract_type}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 3. Schedule Analysis (Primavera P6)
# ═══════════════════════════════════════════════════════════

@router.post("/schedule")
async def analyze_schedule(
    baseline: Optional[UploadFile] = File(None),
    include_details: bool = Form(False),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    tmp_path = await _save_upload(file)
    baseline_path = None
    try:
        if baseline:
            baseline_path = await _save_upload(baseline)
        block = _get_block()
        result = await block.parse_primavera_schedule(
            {"file_path": tmp_path, "baseline_file": baseline_path},
            {"include_details": include_details, "analysis_date": datetime.now().isoformat()}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        for p in (tmp_path, baseline_path):
            if p:
                try:
                    os.remove(p)
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════
# 4. Specification Analysis
# ═══════════════════════════════════════════════════════════

@router.post("/specification")
async def analyze_specification(
    division: Optional[str] = Form(None),
    full_details: bool = Form(False),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    tmp_path = await _save_upload(file)
    try:
        block = _get_block()
        result = await block.process_specification_full(
            {"file_path": tmp_path},
            {"division": division, "full_details": full_details}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 5. Change Order Impact
# ═══════════════════════════════════════════════════════════

@router.post("/change-order")
async def change_order_impact(
    req: ChangeOrderRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.change_order_impact(
        {
            "description": req.description,
            "value": req.value,
            "affected_activities": req.affected_activities,
            "schedule_file": req.schedule_file,
            "contract_file": req.contract_file,
        },
        {}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 6. RFI Generator
# ═══════════════════════════════════════════════════════════

@router.post("/rfi")
async def generate_rfi(
    req: RFIRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.rfi_generator(
        {
            "description": req.description,
            "drawing_reference": req.drawing_reference,
            "spec_reference": req.spec_reference,
        },
        {
            "priority": req.priority,
            "trade": req.trade,
            "project_name": req.project_name,
        }
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 7. Safety Compliance Audit
# ═══════════════════════════════════════════════════════════

@router.post("/safety-audit")
async def safety_audit(
    audit_type: str = Form("general"),
    location: str = Form("US"),
    photos: List[UploadFile] = File(default_factory=list),
    user=Depends(get_current_user),
):
    photo_paths = []
    try:
        for photo in photos:
            photo_paths.append(await _save_upload(photo))
        block = _get_block()
        result = await block.safety_compliance_audit(
            {"photos": photo_paths},
            {"type": audit_type, "location": location}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        for p in photo_paths:
            try:
                os.remove(p)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# 8. Carbon Footprint Calculator
# ═══════════════════════════════════════════════════════════

@router.post("/carbon")
async def carbon_calculator(
    req: CarbonCalcRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.carbon_footprint_calculator(
        {"boq": req.boq, "materials": req.materials},
        {"assessment_type": req.assessment_type, "building_type": req.building_type}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 9. Procurement List Generator
# ═══════════════════════════════════════════════════════════

@router.post("/procurement")
async def procurement_plan(
    req: ProcurementRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.procurement_list_generator(
        {"boq": req.boq, "schedule_file": req.schedule_file},
        {"project_start_date": req.project_start_date, "strategy": req.strategy}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 10. As-Built Deviation Report
# ═══════════════════════════════════════════════════════════

@router.post("/deviation-report")
async def deviation_report(
    originals: List[UploadFile] = File(...),
    as_builts: List[UploadFile] = File(...),
    photos: List[UploadFile] = File(default_factory=list),
    user=Depends(get_current_user),
):
    orig_paths = []
    ab_paths = []
    photo_paths = []
    try:
        for f in originals:
            orig_paths.append(await _save_upload(f))
        for f in as_builts:
            ab_paths.append(await _save_upload(f))
        for f in photos:
            photo_paths.append(await _save_upload(f))
        block = _get_block()
        result = await block.as_built_deviation_report(
            {"as_built_files": ab_paths, "original_drawings": orig_paths, "photos": photo_paths},
            {}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        for p in orig_paths + ab_paths + photo_paths:
            try:
                os.remove(p)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# 11. Warranty & Maintenance Schedule
# ═══════════════════════════════════════════════════════════

@router.post("/warranty")
async def warranty_schedule(
    req: WarrantyRequest,
    spec: Optional[UploadFile] = File(None),
    user=Depends(get_current_user),
):
    spec_path = None
    try:
        if spec:
            spec_path = await _save_upload(spec)
        block = _get_block()
        result = await block.warranty_maintenance_schedule(
            {"spec_file": spec_path, "equipment_list": req.equipment_list},
            {"substantial_completion_date": req.substantial_completion_date}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        if spec_path:
            try:
                os.remove(spec_path)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# 12. Risk Register Auto-Populate
# ═══════════════════════════════════════════════════════════

@router.post("/risk-register")
async def risk_register(
    drawings: List[UploadFile] = File(default_factory=list),
    spec: Optional[UploadFile] = File(None),
    schedule: Optional[UploadFile] = File(None),
    contract: Optional[UploadFile] = File(None),
    site_photos: List[UploadFile] = File(default_factory=list),
    user=Depends(get_current_user),
):
    drawing_paths = []
    spec_path = None
    schedule_path = None
    contract_path = None
    photo_paths = []
    try:
        for f in drawings:
            drawing_paths.append(await _save_upload(f))
        if spec:
            spec_path = await _save_upload(spec)
        if schedule:
            schedule_path = await _save_upload(schedule)
        if contract:
            contract_path = await _save_upload(contract)
        for f in site_photos:
            photo_paths.append(await _save_upload(f))
        block = _get_block()
        result = await block.risk_register_auto_populate(
            {
                "drawings": drawing_paths,
                "spec_file": spec_path,
                "schedule_file": schedule_path,
                "contract_file": contract_path,
                "site_photos": photo_paths,
            },
            {}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        for p in drawing_paths + photo_paths:
            try:
                os.remove(p)
            except Exception:
                pass
        for p in (spec_path, schedule_path, contract_path):
            if p:
                try:
                    os.remove(p)
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════
# 13. QA/QC Inspection (Image)
# ═══════════════════════════════════════════════════════════

@router.post("/qa-qc")
async def qa_qc_inspection(
    inspection_type: str = Form("general"),
    image: UploadFile = File(...),
    user=Depends(get_current_user),
):
    tmp_path = await _save_upload(image)
    try:
        block = _get_block()
        result = await block.qa_qc_inspection(
            {"file_path": tmp_path},
            {"type": inspection_type}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 14. Quantity Extraction
# ═══════════════════════════════════════════════════════════

@router.post("/quantities")
async def extract_quantities(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    tmp_path = await _save_upload(file)
    try:
        block = _get_block()
        result = await block.extract_quantities(
            {"file_path": tmp_path},
            {}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 15. Tender Bid Analysis
# ═══════════════════════════════════════════════════════════

class TenderBidRequest(BaseModel):
    bids: List[Dict[str, Any]] = Field(default_factory=list)
    weights: Optional[Dict[str, float]] = None
    project_type: str = "general_construction"


@router.post("/tender-bids")
async def tender_bid_analysis(
    req: TenderBidRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.tender_bid_analysis(
        {"bids": req.bids},
        {"weights": req.weights, "project_type": req.project_type}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 16. Variation Order Manager
# ═══════════════════════════════════════════════════════════

class VariationOrderRequest(BaseModel):
    variation_data: Dict[str, Any] = Field(default_factory=dict)
    existing_vos: List[Dict[str, Any]] = Field(default_factory=list)
    contract_file: Optional[str] = None


@router.post("/variation-order")
async def variation_order_manager(
    req: VariationOrderRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.variation_order_manager(
        {"variation_data": req.variation_data, "existing_vos": req.existing_vos, "contract_file": req.contract_file},
        {}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 17. Forensic Delay Analysis
# ═══════════════════════════════════════════════════════════

class ForensicDelayRequest(BaseModel):
    delay_events: List[Dict[str, Any]] = Field(default_factory=list)
    method: str = "time_impact"


@router.post("/forensic-delay")
async def forensic_delay_analysis(
    baseline: UploadFile = File(...),
    updated: UploadFile = File(...),
    req: str = Form("{}"),
    user=Depends(get_current_user),
):
    import json as _json
    baseline_path = await _save_upload(baseline)
    updated_path = await _save_upload(updated)
    try:
        body = _json.loads(req)
        block = _get_block()
        result = await block.forensic_delay_analysis(
            {
                "baseline_file": baseline_path,
                "updated_file": updated_path,
                "delay_events": body.get("delay_events", []),
            },
            {"method": body.get("method", "time_impact")}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        for p in (baseline_path, updated_path):
            try:
                os.remove(p)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# 18. Cash Flow Forecast
# ═══════════════════════════════════════════════════════════

class CashFlowRequest(BaseModel):
    boq: List[Dict[str, Any]] = Field(default_factory=list)
    contract_value: float = 0.0
    payment_terms: Optional[Dict[str, Any]] = None
    project_start_date: Optional[str] = None


@router.post("/cash-flow")
async def cash_flow_forecast(
    file: UploadFile = File(...),
    req: str = Form("{}"),
    user=Depends(get_current_user),
):
    import json as _json
    tmp_path = await _save_upload(file)
    try:
        body = _json.loads(req)
        block = _get_block()
        result = await block.cash_flow_forecast(
            {"schedule_file": tmp_path, "boq": body.get("boq", []), "contract_value": body.get("contract_value", 0)},
            {"payment_terms": body.get("payment_terms"), "project_start_date": body.get("project_start_date")}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 19. Procurement Optimizer
# ═══════════════════════════════════════════════════════════

class ProcurementOptimizerRequest(BaseModel):
    boq: List[Dict[str, Any]] = Field(default_factory=list)
    suppliers: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: Optional[Dict[str, Any]] = None


@router.post("/procurement-optimizer")
async def procurement_optimizer(
    req: ProcurementOptimizerRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.procurement_optimizer(
        {"boq": req.boq, "suppliers": req.suppliers},
        {"constraints": req.constraints}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 20. ESG Sustainability Report
# ═══════════════════════════════════════════════════════════

class ESGReportRequest(BaseModel):
    boq: List[Dict[str, Any]] = Field(default_factory=list)
    manpower: Dict[str, Any] = Field(default_factory=dict)
    safety_records: List[Dict[str, Any]] = Field(default_factory=list)
    period: str = "annual"


@router.post("/esg-report")
async def esg_sustainability_report(
    req: ESGReportRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.esg_sustainability_report(
        {"boq": req.boq, "manpower": req.manpower, "safety_records": req.safety_records},
        {"period": req.period}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 21. O&M Manual Generator
# ═══════════════════════════════════════════════════════════

class OMManualRequest(BaseModel):
    equipment_list: List[Dict[str, Any]] = Field(default_factory=list)
    commissioning: Dict[str, Any] = Field(default_factory=dict)
    drawings: List[str] = Field(default_factory=list)
    project_name: str = "Project"


@router.post("/om-manual")
async def om_manual_generator(
    req: OMManualRequest,
    spec: Optional[UploadFile] = File(None),
    user=Depends(get_current_user),
):
    spec_path = None
    try:
        if spec:
            spec_path = await _save_upload(spec)
        block = _get_block()
        result = await block.om_manual_generator(
            {
                "equipment_list": req.equipment_list,
                "spec_file": spec_path,
                "drawings": req.drawings,
                "commissioning": req.commissioning,
            },
            {"project_name": req.project_name}
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        if spec_path:
            try:
                os.remove(spec_path)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# 22. Digital Twin Sync
# ═══════════════════════════════════════════════════════════

class DigitalTwinSyncRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)
    platform: str = "generic"
    mode: str = "update"
    project_id: str = "project_001"


@router.post("/digital-twin")
async def digital_twin_sync(
    req: DigitalTwinSyncRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.digital_twin_sync(
        {"data": req.data},
        {"platform": req.platform, "mode": req.mode, "project_id": req.project_id}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ═══════════════════════════════════════════════════════════
# 23. Intelligent Workflow
# ═══════════════════════════════════════════════════════════

class IntelligentWorkflowRequest(BaseModel):
    goal: str = "process document"
    input_data: Dict[str, Any] = Field(default_factory=dict)


@router.post("/workflow")
async def intelligent_workflow(
    req: IntelligentWorkflowRequest,
    user=Depends(get_current_user),
):
    block = _get_block()
    result = await block.intelligent_workflow(
        req.input_data,
        {"goal": req.goal}
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/workflow/upload")
async def intelligent_workflow_upload(
    goal: str = Form("process document"),
    input_data_json: str = Form("{}"),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    block = _get_block()
    try:
        input_data = json.loads(input_data_json) if input_data_json else {}
    except Exception:
        input_data = {}

    temp_path = await _save_upload(file)
    input_data["file_path"] = temp_path

    try:
        result = await block.intelligent_workflow(
            input_data,
            {"goal": goal}
        )
    finally:
        _safe_remove(temp_path)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
