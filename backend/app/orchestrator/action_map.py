"""
Action Map for Smart Orchestrator

Defines 39 Construction Container actions with their triggers, keywords,
patterns, and schema requirements for intent routing.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Callable
from enum import Enum


class ActionCategory(Enum):
    """Categories for construction actions."""
    DOCUMENT = "document"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    PLANNING = "planning"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    BIM = "bim"
    WORKFLOW = "workflow"


@dataclass
class ActionDefinition:
    """Definition of a construction action with routing metadata."""
    name: str
    category: ActionCategory
    description: str
    keywords: List[str]
    patterns: List[str]
    required_input: List[str]
    optional_input: List[str]
    schema_triggers: List[str]  # File types that trigger this action
    priority: int = 1  # Higher = checked first
    synonym_matches: List[str] = None
    
    def __post_init__(self):
        if self.synonym_matches is None:
            self.synonym_matches = []


# ═══════════════════════════════════════════════════════════
# 39 CONSTRUCTION CONTAINER ACTION DEFINITIONS
# ═══════════════════════════════════════════════════════════

ACTION_MAP: Dict[str, ActionDefinition] = {
    # 1. CORE DOCUMENT PROCESSING
    "process_document": ActionDefinition(
        name="process_document",
        category=ActionCategory.DOCUMENT,
        description="Master document processor with classification",
        keywords=["process", "analyze", "read", "extract"],
        patterns=[
            r"process\s+(?:the\s+)?(?:document|file|drawing)",
            r"analyze\s+(?:the\s+)?(?:pdf|document|drawing)",
            r"extract\s+(?:data|info|text)\s+from",
        ],
        required_input=["file_path"],
        optional_input=["doc_type", "url"],
        schema_triggers=[".pdf", ".dwg", ".dxf", ".tif", ".png"],
        priority=10,
        synonym_matches=["document_processor", "file_analyzer", "pdf_reader"],
    ),
    
    "process_drawing": ActionDefinition(
        name="process_drawing",
        category=ActionCategory.DOCUMENT,
        description="Process technical drawings with full extraction",
        keywords=["drawing", "blueprint", "plan", "elevation", "section"],
        patterns=[
            r"process\s+(?:the\s+)?drawing",
            r"extract\s+(?:measurements|dimensions|quantities)\s+from\s+drawing",
            r"read\s+(?:architectural|structural|mep)\s+drawing",
        ],
        required_input=["file_path"],
        optional_input=["scale", "discipline"],
        schema_triggers=[".pdf", ".dwg", ".dxf"],
        priority=9,
        synonym_matches=["drawing_processor", "blueprint_reader"],
    ),
    
    "process_contract": ActionDefinition(
        name="process_contract",
        category=ActionCategory.DOCUMENT,
        description="Analyze contract documents and clauses",
        keywords=["contract", "agreement", "legal", "terms", "conditions"],
        patterns=[
            r"analyze\s+(?:the\s+)?contract",
            r"review\s+(?:contract\s+)?terms",
            r"extract\s+clauses",
            r"contract\s+risk\s+assessment",
        ],
        required_input=["file_path"],
        optional_input=["contract_type"],
        schema_triggers=[".pdf"],
        priority=9,
        synonym_matches=["contract_analyzer", "legal_review"],
    ),
    
    "process_specification_full": ActionDefinition(
        name="process_specification_full",
        category=ActionCategory.DOCUMENT,
        description="Parse CSI MasterFormat specifications",
        keywords=["specification", "spec", "masterformat", "csi", "section"],
        patterns=[
            r"process\s+(?:the\s+)?spec(?:ification)?s?",
            r"extract\s+submittals",
            r"check\s+spec(?:ification)?s?",
            r"parse\s+(?:spec|specification)",
        ],
        required_input=["file_path"],
        optional_input=["division_filter"],
        schema_triggers=[".pdf", ".doc", ".docx"],
        priority=9,
        synonym_matches=["spec_analyzer", "specification_parser"],
    ),
    
    # 2. QUANTITY & COST ANALYSIS
    "extract_quantities": ActionDefinition(
        name="extract_quantities",
        category=ActionCategory.ANALYSIS,
        description="Extract quantities from drawings and documents",
        keywords=["quantity", "quantities", "qto", "takeoff", "bill", "boq", "measurement"],
        patterns=[
            r"extract\s+(?:quantities|qto|takeoff)",
            r"calculate\s+(?:quantities|volumes|areas)",
            r"(?:do|perform)\s+(?:full\s+)?qto",
            r"bill\s+of\s+quantities",
            r"(?:get|extract)\s+measurements",
        ],
        required_input=["file_path"],
        optional_input=["discipline", "unit_system"],
        schema_triggers=[".pdf", ".dwg", ".xlsx"],
        priority=10,
        synonym_matches=["quantity_takeoff", "qto", "measurement_extraction", "bill_of_quantities"],
    ),
    
    "change_order_impact": ActionDefinition(
        name="change_order_impact",
        category=ActionCategory.ANALYSIS,
        description="Analyze change order cost and schedule impact",
        keywords=["change order", "variation", "co", "modification", "impact"],
        patterns=[
            r"analyze\s+(?:change\s+order|variation)",
            r"change\s+order\s+impact",
            r"(?:calculate|assess)\s+(?:co|change\s+order)\s+(?:cost|schedule)",
            r"variation\s+order\s+impact",
        ],
        required_input=["description"],
        optional_input=["value", "schedule_file", "contract_file", "affected_activities"],
        schema_triggers=[".xer", ".xml", ".pdf"],
        priority=8,
        synonym_matches=["co_analysis", "variation_impact", "change_impact"],
    ),
    
    "value_engineering": ActionDefinition(
        name="value_engineering",
        category=ActionCategory.ANALYSIS,
        description="Identify cost-saving alternatives",
        keywords=["value engineering", "ve", "cost saving", "optimization", "alternative"],
        patterns=[
            r"(?:do|perform)\s+value\s+engineering",
            r"find\s+(?:cost\s+)?savings?",
            r"optimize\s+(?:costs?|design)",
            r"value\s+engineer\s+(?:the\s+)?(?:design|boq)",
        ],
        required_input=["boq"],
        optional_input=["carbon_priority", "target_reduction"],
        schema_triggers=[".xlsx", ".csv"],
        priority=7,
        synonym_matches=["ve_analysis", "cost_optimization", "design_optimization"],
    ),
    
    "tender_bid_analysis": ActionDefinition(
        name="tender_bid_analysis",
        category=ActionCategory.ANALYSIS,
        description="Compare multiple tender bids",
        keywords=["tender", "bid", "comparison", "proposal", "quotation"],
        patterns=[
            r"compare\s+(?:tender|bid)s?",
            r"analyze\s+(?:bids?|tenders?)",
            r"bid\s+comparison",
            r"tender\s+evaluation",
        ],
        required_input=["bids"],
        optional_input=["weights", "criteria"],
        schema_triggers=[".xlsx", ".csv", ".pdf"],
        priority=8,
        synonym_matches=["bid_comparison", "tender_evaluation", "proposal_analysis"],
    ),
    
    # 3. SCHEDULING & PLANNING
    "parse_primavera_schedule": ActionDefinition(
        name="parse_primavera_schedule",
        category=ActionCategory.PLANNING,
        description="Parse Primavera P6 XER/XML schedules",
        keywords=["primavera", "p6", "schedule", "xer", "xml", "msp"],
        patterns=[
            r"parse\s+(?:primavera|p6|schedule)",
            r"analyze\s+(?:the\s+)?schedule",
            r"process\s+(?:xer|\.xer)\s+file",
            r"schedule\s+analysis",
            r"critical\s+path\s+analysis",
        ],
        required_input=["file_path"],
        optional_input=["baseline_file", "analysis_date"],
        schema_triggers=[".xer", ".xml"],
        priority=9,
        synonym_matches=["schedule_parser", "primavera_analysis", "cpm_analysis"],
    ),
    
    "forensic_delay_analysis": ActionDefinition(
        name="forensic_delay_analysis",
        category=ActionCategory.PLANNING,
        description="Forensic delay and disruption analysis",
        keywords=["delay", "forensic", "eot", "extension", "disruption", "time impact"],
        patterns=[
            r"(?:perform|do)\s+(?:forensic\s+)?delay\s+analysis",
            r"analyze\s+(?:the\s+)?delays?",
            r"extension\s+of\s+time\s+(?:analysis|claim)",
            r"eot\s+(?:analysis|claim)",
            r"time\s+impact\s+analysis",
        ],
        required_input=["schedule_file"],
        optional_input=["baseline_file", "delay_events", "analysis_window"],
        schema_triggers=[".xer", ".xml"],
        priority=8,
        synonym_matches=["delay_analysis", "eot_analysis", "time_impact"],
    ),
    
    "resource_histogram": ActionDefinition(
        name="resource_histogram",
        category=ActionCategory.PLANNING,
        description="Generate resource loading histograms",
        keywords=["resource", "histogram", "loading", "manpower", "crew"],
        patterns=[
            r"(?:generate|create)\s+resource\s+histogram",
            r"resource\s+loading\s+analysis",
            r"manpower\s+(?:forecast|histogram)",
            r"crew\s+(?:loading|requirements)",
        ],
        required_input=["schedule_file"],
        optional_input=["resource_type", "time_period"],
        schema_triggers=[".xer", ".xml"],
        priority=7,
        synonym_matches=["resource_loading", "manpower_forecast", "crew_analysis"],
    ),
    
    "procurement_list_generator": ActionDefinition(
        name="procurement_list_generator",
        category=ActionCategory.PLANNING,
        description="Generate procurement schedule from BOQ",
        keywords=["procurement", "purchase", "materials", "ordering", "lead time"],
        patterns=[
            r"generate\s+procurement\s+(?:list|schedule)",
            r"(?:create|make)\s+purchase\s+plan",
            r"material\s+procurement\s+schedule",
            r"long\s+lead\s+item\s+(?:identification|list)",
        ],
        required_input=["boq"],
        optional_input=["project_start_date", "schedule_file", "strategy"],
        schema_triggers=[".xlsx", ".csv", ".xer"],
        priority=8,
        synonym_matches=["procurement_schedule", "purchase_plan", "material_plan"],
    ),
    
    "procurement_optimizer": ActionDefinition(
        name="procurement_optimizer",
        category=ActionCategory.PLANNING,
        description="Optimize material ordering and packaging",
        keywords=["optimize", "procurement", "packaging", "batch", "order"],
        patterns=[
            r"optimize\s+procurement",
            r"optimize\s+(?:materials?|ordering)",
            r"(?:batch|package)\s+procurement",
            r"procurement\s+optimization",
        ],
        required_input=["boq"],
        optional_input=["strategy", "cash_flow_constraint"],
        schema_triggers=[".xlsx", ".csv"],
        priority=7,
        synonym_matches=["material_optimization", "order_optimization"],
    ),
    
    # 4. FINANCIAL MANAGEMENT
    "payment_certificate": ActionDefinition(
        name="payment_certificate",
        category=ActionCategory.FINANCIAL,
        description="Generate interim payment certificates",
        keywords=["payment", "certificate", "ipc", "invoice", "billing", "progress"],
        patterns=[
            r"generate\s+(?:payment\s+)?certificate",
            r"(?:create|make)\s+ipc",
            r"interim\s+payment\s+certificate",
            r"progress\s+(?:billing|payment)",
            r"payment\s+application",
        ],
        required_input=["boq"],
        optional_input=["schedule_file", "previous_payments", "retention"],
        schema_triggers=[".xlsx", ".csv", ".xer"],
        priority=8,
        synonym_matches=["ipc", "payment_application", "progress_billing"],
    ),
    
    "cash_flow_forecast": ActionDefinition(
        name="cash_flow_forecast",
        category=ActionCategory.FINANCIAL,
        description="Forecast project cash flow",
        keywords=["cash flow", "forecast", "projection", "financial", "s-curve"],
        patterns=[
            r"(?:generate|create)\s+cash\s+flow\s+(?:forecast|projection)",
            r"(?:s-curve|s curve)\s+(?:analysis|forecast)",
            r"financial\s+projection",
            r"cash\s+flow\s+analysis",
        ],
        required_input=["schedule_file"],
        optional_input=["payment_terms", "retention", "overheads"],
        schema_triggers=[".xer", ".xml", ".xlsx"],
        priority=8,
        synonym_matches=["cashflow_forecast", "financial_projection", "s_curve"],
    ),
    
    "claims_builder": ActionDefinition(
        name="claims_builder",
        category=ActionCategory.FINANCIAL,
        description="Build delay and disruption claims",
        keywords=["claim", "disruption", "prolongation", "loss", "expense"],
        patterns=[
            r"(?:build|create|prepare)\s+(?:a\s+)?claim",
            r"claim\s+(?:analysis|preparation)",
            r"delay\s+claim",
            r"disruption\s+claim",
            r"loss\s+and\s+expense",
        ],
        required_input=["schedule_file"],
        optional_input=["baseline_file", "delay_events", "cost_records"],
        schema_triggers=[".xer", ".xml"],
        priority=8,
        synonym_matches=["claim_preparation", "delay_claim", "disruption_analysis"],
    ),
    
    "variation_order_manager": ActionDefinition(
        name="variation_order_manager",
        category=ActionCategory.FINANCIAL,
        description="Manage variation orders and their impact",
        keywords=["variation", "vo", "variation order", "change", "modification"],
        patterns=[
            r"manage\s+(?:variation|vo)s?",
            r"variation\s+order\s+(?:management|register)",
            r"track\s+variations?",
            r"variation\s+impact\s+(?:analysis|assessment)",
        ],
        required_input=["variations"],
        optional_input=["contract_value", "schedule_file"],
        schema_triggers=[".xlsx", ".csv"],
        priority=8,
        synonym_matches=["vo_manager", "variation_tracker", "change_order_manager"],
    ),
    
    # 5. RFI & COMMUNICATION
    "rfi_generator": ActionDefinition(
        name="rfi_generator",
        category=ActionCategory.WORKFLOW,
        description="Generate RFIs from ambiguities",
        keywords=["rfi", "request for information", "clarification", "question", "ambiguity"],
        patterns=[
            r"(?:generate|create|draft)\s+(?:an\s+)?rfi",
            r"request\s+for\s+information",
            r"(?:write|prepare)\s+rfi",
            r"clarification\s+request",
        ],
        required_input=["description"],
        optional_input=["drawing_ref", "spec_ref", "priority", "trade"],
        schema_triggers=[],
        priority=9,
        synonym_matches=["rfi_draft", "clarification_request", "information_request"],
    ),
    
    "submittal_log_generator": ActionDefinition(
        name="submittal_log_generator",
        category=ActionCategory.WORKFLOW,
        description="Generate submittal tracking logs",
        keywords=["submittal", "submittals", "shop drawing", "log", "tracking"],
        patterns=[
            r"(?:generate|create)\s+submittal\s+(?:log|register)",
            r"submittal\s+tracking",
            r"(?:extract|get)\s+submittals",
            r"shop\s+drawing\s+log",
        ],
        required_input=["spec_file"],
        optional_input=["existing_log", "phase"],
        schema_triggers=[".pdf", ".doc", ".docx"],
        priority=8,
        synonym_matches=["submittal_register", "submittal_tracking", "shop_drawing_log"],
    ),
    
    # 6. COMPLIANCE & SAFETY
    "safety_compliance_audit": ActionDefinition(
        name="safety_compliance_audit",
        category=ActionCategory.COMPLIANCE,
        description="Audit site safety compliance",
        keywords=["safety", "audit", "compliance", "hse", "osha", "inspection"],
        patterns=[
            r"(?:perform|do|conduct)\s+(?:safety\s+)?audit",
            r"safety\s+compliance\s+(?:check|audit)",
            r"hse\s+(?:audit|inspection)",
            r"(?:check|verify)\s+safety\s+compliance",
        ],
        required_input=[],
        optional_input=["type", "location", "photos", "checklist_items"],
        schema_triggers=[".jpg", ".png", ".pdf"],
        priority=8,
        synonym_matches=["safety_audit", "hse_inspection", "compliance_check"],
    ),
    
    "qa_qc_inspection": ActionDefinition(
        name="qa_qc_inspection",
        category=ActionCategory.COMPLIANCE,
        description="Quality assurance inspection from photos",
        keywords=["quality", "qa", "qc", "inspection", "defect", "defects"],
        patterns=[
            r"(?:perform|do)\s+(?:qa|qc)\s+inspection",
            r"quality\s+(?:check|inspection)",
            r"inspect\s+(?:for\s+)?(?:defects|quality)",
            r"(?:check|assess)\s+quality",
        ],
        required_input=["file_path"],
        optional_input=["type"],
        schema_triggers=[".jpg", ".png"],
        priority=8,
        synonym_matches=["quality_inspection", "defect_detection", "qa_check"],
    ),
    
    "commissioning_checklist": ActionDefinition(
        name="commissioning_checklist",
        category=ActionCategory.COMPLIANCE,
        description="Generate commissioning checklists",
        keywords=["commissioning", "handover", "testing", "checklist", "completion"],
        patterns=[
            r"(?:generate|create)\s+commissioning\s+(?:checklist|plan)",
            r"(?:handover|completion)\s+checklist",
            r"testing\s+(?:checklist|requirements)",
            r"commissioning\s+(?:schedule|plan)",
        ],
        required_input=[],
        optional_input=["spec_file", "equipment_list", "systems"],
        schema_triggers=[".pdf", ".doc", ".docx"],
        priority=7,
        synonym_matches=["commissioning_plan", "handover_checklist", "testing_plan"],
    ),
    
    "warranty_maintenance_schedule": ActionDefinition(
        name="warranty_maintenance_schedule",
        category=ActionCategory.COMPLIANCE,
        description="Generate warranty and maintenance schedules",
        keywords=["warranty", "maintenance", "o&m", "operation", "manual"],
        patterns=[
            r"(?:generate|create)\s+(?:warranty|maintenance)\s+schedule",
            r"o[&+]m\s+(?:schedule|plan)",
            r"(?:preventive|planned)\s+maintenance",
            r"warranty\s+tracking",
        ],
        required_input=[],
        optional_input=["spec_file", "equipment_list", "substantial_completion"],
        schema_triggers=[".pdf", ".xlsx"],
        priority=7,
        synonym_matches=["warranty_schedule", "maintenance_plan", "pm_schedule"],
    ),
    
    # 7. CARBON & SUSTAINABILITY
    "carbon_footprint_calculator": ActionDefinition(
        name="carbon_footprint_calculator",
        category=ActionCategory.COMPLIANCE,
        description="Calculate embodied carbon footprint",
        keywords=["carbon", "footprint", "embodied", "co2", "sustainability", "green"],
        patterns=[
            r"calculate\s+(?:carbon|co2)\s+(?:footprint|emissions)",
            r"(?:embodied|embodied\s+carbon)\s+(?:calculation|analysis)",
            r"carbon\s+assessment",
            r"(?:green|sustainability)\s+(?:check|assessment)",
        ],
        required_input=[],
        optional_input=["boq", "materials", "assessment_type"],
        schema_triggers=[".xlsx", ".csv"],
        priority=7,
        synonym_matches=["carbon_calculator", "co2_footprint", "embodied_carbon"],
    ),
    
    "esg_sustainability_report": ActionDefinition(
        name="esg_sustainability_report",
        category=ActionCategory.COMPLIANCE,
        description="Generate ESG and sustainability reports",
        keywords=["esg", "sustainability", "report", "environmental", "social", "governance"],
        patterns=[
            r"(?:generate|create)\s+(?:esg|sustainability)\s+report",
            r"esg\s+(?:analysis|assessment|reporting)",
            r"sustainability\s+(?:report|metrics)",
        ],
        required_input=[],
        optional_input=["boq", "project_data", "reporting_period"],
        schema_triggers=[".xlsx", ".csv"],
        priority=6,
        synonym_matches=["esg_report", "sustainability_metrics", "green_report"],
    ),
    
    # 8. RISK & BIM
    "risk_register_auto_populate": ActionDefinition(
        name="risk_register_auto_populate",
        category=ActionCategory.ANALYSIS,
        description="Auto-populate risk register from documents",
        keywords=["risk", "risk register", "risk assessment", "hazards"],
        patterns=[
            r"(?:generate|create|populate)\s+risk\s+register",
            r"(?:auto\s+)?risk\s+(?:identification|assessment)",
            r"risk\s+analysis",
            r"identify\s+(?:project\s+)?risks?",
        ],
        required_input=[],
        optional_input=["drawings", "spec_file", "schedule_file", "contract_file", "site_photos"],
        schema_triggers=[".pdf", ".dwg", ".xer"],
        priority=8,
        synonym_matches=["risk_analysis", "risk_identification", "hazard_register"],
    ),
    
    "bim_clash_detection": ActionDefinition(
        name="bim_clash_detection",
        category=ActionCategory.BIM,
        description="Detect clashes in IFC models",
        keywords=["bim", "clash", "clash detection", "ifc", "coordination", "collision"],
        patterns=[
            r"(?:perform|do|run)\s+(?:bim\s+)?clash\s+detection",
            r"detect\s+(?:model\s+)?clashes?",
            r"(?:bim|model)\s+coordination",
            r"clash\s+(?:check|test|analysis)",
        ],
        required_input=[],
        optional_input=["ifc_file", "discipline_models", "tolerance"],
        schema_triggers=[".ifc"],
        priority=9,
        synonym_matches=["clash_detection", "bim_coordination", "model_clash"],
    ),
    
    "digital_twin_sync": ActionDefinition(
        name="digital_twin_sync",
        category=ActionCategory.BIM,
        description="Sync physical and digital models",
        keywords=["digital twin", "twin", "as-built", "sync", "update", "reality"],
        patterns=[
            r"(?:update|sync)\s+(?:the\s+)?digital\s+twin",
            r"digital\s+twin\s+(?:sync|update)",
            r"(?:as[-\s]built|asbuilt)\s+model\s+(?:update|sync)",
            r"model\s+vs\s+reality",
        ],
        required_input=[],
        optional_input=["bim_model", "sensor_data", "progress_photos"],
        schema_triggers=[".ifc", ".json"],
        priority=7,
        synonym_matches=["twin_sync", "asbuilt_update", "reality_capture"],
    ),
    
    # 9. REPORTING
    "as_built_deviation_report": ActionDefinition(
        name="as_built_deviation_report",
        category=ActionCategory.REPORTING,
        description="Compare as-built vs design drawings",
        keywords=["as-built", "asbuilt", "deviation", "comparison", "redline"],
        patterns=[
            r"(?:generate|create)\s+(?:as[-\s]built|asbuilt)\s+(?:report|comparison)",
            r"compare\s+(?:as[-\s]built|asbuilt)\s+(?:to|with|vs)\s+design",
            r"deviation\s+(?:report|analysis|check)",
            r"(?:redline|red[-\s]line)\s+comparison",
        ],
        required_input=["as_built_files", "original_drawings"],
        optional_input=["photos"],
        schema_triggers=[".pdf", ".dwg"],
        priority=8,
        synonym_matches=["asbuilt_report", "deviation_analysis", "redline_check"],
    ),
    
    "daily_site_report": ActionDefinition(
        name="daily_site_report",
        category=ActionCategory.REPORTING,
        description="Generate daily site reports from inputs",
        keywords=["daily report", "site report", "dsr", "daily log", "progress"],
        patterns=[
            r"(?:generate|create)\s+daily\s+(?:site\s+)?report",
            r"dsr\s+(?:generation|creation)",
            r"daily\s+(?:site\s+)?log",
            r"site\s+daily\s+report",
        ],
        required_input=[],
        optional_input=["voice_files", "photos", "location", "supervisor"],
        schema_triggers=[".jpg", ".png", ".mp3", ".wav"],
        priority=7,
        synonym_matches=["dsr", "daily_log", "site_report"],
    ),
    
    "om_manual_generator": ActionDefinition(
        name="om_manual_generator",
        category=ActionCategory.REPORTING,
        description="Generate O&M manuals from specs",
        keywords=["o&m", "om", "manual", "operation", "maintenance", "handover"],
        patterns=[
            r"(?:generate|create)\s+(?:o[&+]m|om)\s+manual",
            r"operation\s+and\s+maintenance\s+manual",
            r"(?:handover|hand[-\s]over)\s+manual",
            r"(?:closeout|close[-\s]out)\s+documentation",
        ],
        required_input=[],
        optional_input=["spec_file", "equipment_list", "submittals"],
        schema_triggers=[".pdf", ".doc", ".docx"],
        priority=7,
        synonym_matches=["om_manual", "handover_docs", "closeout_manual"],
    ),
    
    # 10. INTELLIGENT WORKFLOW
    "intelligent_workflow": ActionDefinition(
        name="intelligent_workflow",
        category=ActionCategory.WORKFLOW,
        description="Chain multiple actions for complex goals",
        keywords=["workflow", "chain", "full qto", "complete analysis", "do full"],
        patterns=[
            r"(?:do|perform)\s+(?:a\s+)?full\s+(?:qto|analysis)",
            r"(?:complete|full)\s+(?:project|document)\s+analysis",
            r"(?:run|execute)\s+workflow",
            r"(?:chain|sequence)\s+(?:actions|steps)",
            r"(?:intelligent|smart)\s+workflow",
        ],
        required_input=["user_goal"],
        optional_input=["file_path", "context"],
        schema_triggers=[".pdf", ".dwg", ".xer", ".xlsx"],
        priority=10,
        synonym_matches=["smart_workflow", "action_chain", "full_analysis"],
    ),
    
    "generate_construction_report": ActionDefinition(
        name="generate_construction_report",
        category=ActionCategory.REPORTING,
        description="Generate comprehensive construction reports",
        keywords=["report", "construction report", "summary", "analysis report"],
        patterns=[
            r"(?:generate|create)\s+(?:construction\s+)?report",
            r"(?:full|comprehensive)\s+report",
            r"(?:project|construction)\s+summary",
        ],
        required_input=[],
        optional_input=["documents", "analysis_type"],
        schema_triggers=[".pdf", ".xlsx"],
        priority=8,
        synonym_matches=["construction_summary", "project_report"],
    ),
    
    "track_progress": ActionDefinition(
        name="track_progress",
        category=ActionCategory.REPORTING,
        description="Track construction progress",
        keywords=["progress", "tracking", "percent complete", "status"],
        patterns=[
            r"(?:track|monitor)\s+progress",
            r"progress\s+(?:tracking|status|update)",
            r"(?:get|check)\s+(?:the\s+)?progress",
            r"(?:percent|percentage)\s+complete",
        ],
        required_input=[],
        optional_input=["schedule_file", "photos", "reports"],
        schema_triggers=[".xer", ".xml", ".jpg"],
        priority=7,
        synonym_matches=["progress_tracking", "status_update"],
    ),
}

# ═══════════════════════════════════════════════════════════
# ACTION SYNONYMS MAPPING
# ═══════════════════════════════════════════════════════════

ACTION_SYNONYMS: Dict[str, str] = {
    # Quantity & BOQ
    "quantity_takeoff": "extract_quantities",
    "qto": "extract_quantities",
    "takeoff": "extract_quantities",
    "bill_of_quantities": "extract_quantities",
    "boq": "extract_quantities",
    "measurement_extraction": "extract_quantities",
    
    # Documents
    "document_processor": "process_document",
    "file_analyzer": "process_document",
    "pdf_reader": "process_document",
    "drawing_processor": "process_drawing",
    "blueprint_reader": "process_drawing",
    "contract_analyzer": "process_contract",
    "legal_review": "process_contract",
    "spec_analyzer": "process_specification_full",
    "specification_parser": "process_specification_full",
    
    # Scheduling
    "schedule_parser": "parse_primavera_schedule",
    "primavera_analysis": "parse_primavera_schedule",
    "cpm_analysis": "parse_primavera_schedule",
    
    # Change Orders
    "co_analysis": "change_order_impact",
    "variation_impact": "change_order_impact",
    "change_impact": "change_order_impact",
    
    # RFI
    "rfi_draft": "rfi_generator",
    "clarification_request": "rfi_generator",
    "information_request": "rfi_generator",
    "generate_rfi": "rfi_generator",
    
    # Safety & QA
    "safety_audit": "safety_compliance_audit",
    "hse_inspection": "safety_compliance_audit",
    "compliance_check": "safety_compliance_audit",
    "quality_inspection": "qa_qc_inspection",
    "defect_detection": "qa_qc_inspection",
    "qa_check": "qa_qc_inspection",
    
    # Carbon
    "carbon_calculator": "carbon_footprint_calculator",
    "co2_footprint": "carbon_footprint_calculator",
    "embodied_carbon": "carbon_footprint_calculator",
    "esg_report": "esg_sustainability_report",
    "sustainability_metrics": "esg_sustainability_report",
    "green_report": "esg_sustainability_report",
    
    # Risk & BIM
    "risk_analysis": "risk_register_auto_populate",
    "risk_identification": "risk_register_auto_populate",
    "hazard_register": "risk_register_auto_populate",
    "clash_detection": "bim_clash_detection",
    "bim_coordination": "bim_clash_detection",
    "model_clash": "bim_clash_detection",
    "twin_sync": "digital_twin_sync",
    "asbuilt_update": "digital_twin_sync",
    "reality_capture": "digital_twin_sync",
    
    # Financial
    "ipc": "payment_certificate",
    "payment_application": "payment_certificate",
    "progress_billing": "payment_certificate",
    "cashflow_forecast": "cash_flow_forecast",
    "financial_projection": "cash_flow_forecast",
    "s_curve": "cash_flow_forecast",
    "claim_preparation": "claims_builder",
    "delay_claim": "claims_builder",
    "disruption_analysis": "claims_builder",
    "vo_manager": "variation_order_manager",
    "variation_tracker": "variation_order_manager",
    "change_order_manager": "variation_order_manager",
    
    # Planning
    "delay_analysis": "forensic_delay_analysis",
    "eot_analysis": "forensic_delay_analysis",
    "time_impact": "forensic_delay_analysis",
    "resource_loading": "resource_histogram",
    "manpower_forecast": "resource_histogram",
    "crew_analysis": "resource_histogram",
    "procurement_schedule": "procurement_list_generator",
    "purchase_plan": "procurement_list_generator",
    "material_plan": "procurement_list_generator",
    "material_optimization": "procurement_optimizer",
    "order_optimization": "procurement_optimizer",
    
    # VE & Tender
    "ve_analysis": "value_engineering",
    "cost_optimization": "value_engineering",
    "design_optimization": "value_engineering",
    "bid_comparison": "tender_bid_analysis",
    "tender_evaluation": "tender_bid_analysis",
    "proposal_analysis": "tender_bid_analysis",
    
    # Compliance
    "commissioning_plan": "commissioning_checklist",
    "handover_checklist": "commissioning_checklist",
    "testing_plan": "commissioning_checklist",
    "warranty_schedule": "warranty_maintenance_schedule",
    "maintenance_plan": "warranty_maintenance_schedule",
    "pm_schedule": "warranty_maintenance_schedule",
    
    # Reporting
    "asbuilt_report": "as_built_deviation_report",
    "deviation_analysis": "as_built_deviation_report",
    "redline_check": "as_built_deviation_report",
    "dsr": "daily_site_report",
    "daily_log": "daily_site_report",
    "site_report": "daily_site_report",
    "om_manual": "om_manual_generator",
    "handover_docs": "om_manual_generator",
    "closeout_manual": "om_manual_generator",
    "submittal_register": "submittal_log_generator",
    "submittal_tracking": "submittal_log_generator",
    "shop_drawing_log": "submittal_log_generator",
    "construction_summary": "generate_construction_report",
    "project_report": "generate_construction_report",
    "progress_tracking": "track_progress",
    "status_update": "track_progress",
    
    # Workflow
    "smart_workflow": "intelligent_workflow",
    "action_chain": "intelligent_workflow",
    "full_analysis": "intelligent_workflow",
}
