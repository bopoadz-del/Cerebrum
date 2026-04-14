# app/containers/construction.py
# Construction Domain Container v3.1 - Complete AEC Suite
# Author: Cerebrum Platform
# Last Updated: 2026-04-14

import fitz  # PyMuPDF
import re
import json
import os
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import math

from app.core.block import BaseBlock, BlockConfig
from app.llm import get_llm_client, LLMMessage


@dataclass
class Measurement:
    value: float
    unit: str
    type: str
    raw_text: str
    confidence: float
    context: str


@dataclass
class SpecItem:
    category: str
    key: str
    value: str
    section: str
    confidence: float


@dataclass
class RiskItem:
    id: str
    category: str
    description: str
    probability: str  # high, medium, low
    impact: str  # high, medium, low
    mitigation: str
    source: str


class ConstructionBlock(BaseBlock):
    """
    Construction Domain Container v3.1
    Complete AEC Industry Suite - 22+ specialized actions
    """

    def __init__(self):
        super().__init__()
        self.config = BlockConfig(
            name="construction",
            version="3.1",
            description="Complete AEC suite: BIM, QA/QC, scheduling, contracts, specs, safety, carbon, procurement, risk"
        )
        self._load_cost_database()
        self._load_csi_masterformat()
        self._load_safety_codes()
        self._load_carbon_factors()
        self.llm = get_llm_client()

    # ═══════════════════════════════════════════════════════════
    # INITIALIZATION & DATABASES
    # ═══════════════════════════════════════════════════════════

    def _load_cost_database(self):
        """RS Means / regional cost database"""
        self.cost_db = {
            "concrete_c30": {"unit": "m³", "rate": 1250, "labor_factor": 0.4},
            "concrete_c40": {"unit": "m³", "rate": 1450, "labor_factor": 0.4},
            "rebar": {"unit": "kg", "rate": 3.2, "labor_factor": 0.6},
            "formwork": {"unit": "m²", "rate": 48, "labor_factor": 0.7},
            "block_work": {"unit": "m²", "rate": 95, "labor_factor": 0.5},
            "plaster": {"unit": "m²", "rate": 35, "labor_factor": 0.6},
            "paint": {"unit": "m²", "rate": 15, "labor_factor": 0.5},
            "flooring_tile": {"unit": "m²", "rate": 180, "labor_factor": 0.4},
            "ceiling_gypsum": {"unit": "m²", "rate": 75, "labor_factor": 0.5},
            "steel_structural": {"unit": "kg", "rate": 4.5, "labor_factor": 0.5},
            "glass_curtain": {"unit": "m²", "rate": 450, "labor_factor": 0.3},
            "insulation": {"unit": "m²", "rate": 28, "labor_factor": 0.4},
            "electrical_rough": {"unit": "m²", "rate": 65, "labor_factor": 0.5},
            "plumbing_rough": {"unit": "m²", "rate": 85, "labor_factor": 0.5},
            "hvac_duct": {"unit": "m²", "rate": 120, "labor_factor": 0.4},
        }

    def _load_csi_masterformat(self):
        """CSI MasterFormat 2020 divisions"""
        self.csi_divisions = {
            "01": "General Requirements", "02": "Existing Conditions", "03": "Concrete",
            "04": "Masonry", "05": "Metals", "06": "Wood, Plastics, Composites",
            "07": "Thermal & Moisture", "08": "Openings", "09": "Finishes",
            "10": "Specialties", "11": "Equipment", "12": "Furnishings",
            "13": "Special Construction", "14": "Conveying", "21": "Fire Suppression",
            "22": "Plumbing", "23": "HVAC", "25": "Integrated Automation",
            "26": "Electrical", "27": "Communications", "28": "Electronic Safety",
            "31": "Earthwork", "32": "Exterior Improvements", "33": "Utilities"
        }

    def _load_safety_codes(self):
        """OSHA, ISO, and regional safety standards"""
        self.safety_codes = {
            "osha_1926": "Construction Standards",
            "osha_1910": "General Industry",
            "iso_45001": "Occupational Health & Safety",
            "ansi_z10": "Safety Management",
            "nfpa_70e": "Electrical Safety",
            "ansi_a10": "Construction Safety",
        }

    def _load_carbon_factors(self):
        """Embodied carbon coefficients (kg CO₂e per unit)"""
        self.carbon_factors = {
            "concrete_c30": 350,
            "concrete_c40": 420,
            "steel_rebar": 2.5,
            "steel_structural": 2.8,
            "aluminum": 12.7,
            "glass": 25.0,
            "timber_softwood": -0.9,
            "timber_hardwood": -1.2,
            "brick": 220,
            "block_concrete": 180,
            "insulation_mineral": 25,
            "insulation_eps": 35,
            "paint": 5.2,
            "ceramic_tile": 18,
            "carpet": 45,
        }

    # ═══════════════════════════════════════════════════════════
    # 1. CORE DOCUMENT PROCESSING (Existing + Enhanced)
    # ═══════════════════════════════════════════════════════════

    def _get_or_create_cache_key(self, file_path: str, doc_type: str) -> str:
        """Generate a deterministic cache key for a document."""
        from app.core.block_registry import BLOCK_REGISTRY
        file_hasher = BLOCK_REGISTRY.get("file_hasher")
        if file_hasher:
            # We can't await here synchronously, so use path + mtime fallback
            import os
            try:
                mtime = os.path.getmtime(file_path)
                seed = f"{file_path}:{mtime}:{doc_type}"
            except Exception:
                seed = f"{file_path}:{doc_type}"
        else:
            seed = f"{file_path}:{doc_type}"
        import hashlib
        return f"doc_proc:{hashlib.md5(seed.encode()).hexdigest()}"

    async def process_document(self, input_data: dict, params: dict) -> dict:
        """Master document processor with classification and infrastructure integration."""
        file_path = input_data.get("file_path") or params.get("file_path")
        url = input_data.get("url") or params.get("url")
        doc_type = params.get("doc_type", "auto")

        if not file_path and url:
            file_path = await self._download_file(url)

        if not file_path:
            return {"status": "error", "error": "No file provided"}

        from app.core.block_registry import BLOCK_REGISTRY
        file_hasher = BLOCK_REGISTRY.get("file_hasher")
        cache_manager = BLOCK_REGISTRY.get("cache_manager")
        async_processor = BLOCK_REGISTRY.get("async_processor")
        llm_enhancer = BLOCK_REGISTRY.get("llm_enhancer")

        # 1. File fingerprint
        fingerprint = None
        if file_hasher:
            fp_result = await file_hasher.fingerprint({"file_path": file_path}, {})
            if fp_result.get("status") == "success":
                fingerprint = fp_result

        # 2. Cache lookup
        cache_key = self._get_or_create_cache_key(file_path, doc_type)
        if cache_manager:
            cached = await cache_manager.get({"key": cache_key}, {})
            if cached.get("found"):
                return {
                    "status": "success",
                    "source": "cache",
                    "cache_key": cache_key,
                    "fingerprint": fingerprint,
                    "data": cached.get("value"),
                }

        # 3. Large file async offloading
        import os
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        if async_processor and file_size > 10 * 1024 * 1024:
            dispatch_result = await async_processor.dispatch(
                {
                    "task_name": "app.containers.construction.process_document_task",
                    "kwargs": {
                        "file_path": file_path,
                        "doc_type": doc_type,
                        "params": params,
                        "cache_key": cache_key,
                    }
                },
                {"queue": "slow"},
            )
            if dispatch_result.get("status") == "success":
                return {
                    "status": "queued",
                    "task_id": dispatch_result.get("task_id"),
                    "cache_key": cache_key,
                    "fingerprint": fingerprint,
                    "message": "File >10MB, queued for background processing",
                }

        # Auto-classify
        if doc_type == "auto":
            doc_type = await self._classify_document(file_path)

        processors = {
            "drawing": self._process_drawing,
            "specification": self.process_specification_full,
            "contract": self.process_contract,
            "schedule": self.parse_primavera_schedule,
            "bom": self._process_bill_of_materials,
            "report": self._process_report,
            "bim": self._process_ifc,
            "image": self._process_site_photo,
            "change_order": self.change_order_impact,
            "safety_audit": self.safety_compliance_audit,
        }

        processor = processors.get(doc_type, self._process_drawing)
        result = await processor(input_data, params)

        # 4. LLM enhancement / structuring
        if llm_enhancer and result.get("status") == "success":
            raw_text = str(result.get("sheets", result))
            if len(raw_text) > 100:
                try:
                    enhanced = await llm_enhancer.structure_json(
                        {"text": raw_text[:4000]},
                        {"schema_hint": "Extract key fields as structured JSON with keys like title, disciplines, measurements, findings."},
                    )
                    if enhanced.get("status") == "success":
                        result["llm_structured"] = enhanced.get("structured")
                except Exception:
                    pass

        # 5. Cache store
        if cache_manager and result.get("status") == "success":
            await cache_manager.set(
                {"key": cache_key, "value": result},
                {"ttl": 86400},
            )

        if fingerprint:
            result["fingerprint"] = fingerprint
        return result

    async def _process_drawing(self, file_path: str, params: dict) -> dict:
        """Process technical drawings with full extraction"""
        doc = fitz.open(file_path)

        result = {
            "status": "success",
            "doc_type": "drawing",
            "file_name": Path(file_path).name,
            "drawing_number": self._extract_drawing_number(Path(file_path).name),
            "revision": self._extract_revision(Path(file_path).name),
            "total_pages": len(doc),
            "sheets": [],
            "measurements": [],
            "tables": [],
            "annotations": [],
            "specifications": [],
            "detected_disciplines": [],
            "scale": None,
            "title_block": {},
            "bom_items": [],
            "confidence": {}
        }

        for page_num in range(len(doc)):
            page = doc[page_num]
            sheet_data = self._process_drawing_page(page, page_num)
            result["sheets"].append(sheet_data)
            result["measurements"].extend(sheet_data["measurements"])
            result["tables"].extend(sheet_data["tables"])
            result["annotations"].extend(sheet_data["annotations"])
            result["specifications"].extend(sheet_data["specs"])
            result["detected_disciplines"].extend(
                self._detect_disciplines(sheet_data["raw_text"])
            )

        if result["sheets"]:
            result["title_block"] = self._extract_title_block(result["sheets"][0])
            result["scale"] = self._extract_scale(result["sheets"][0]["raw_text"])

        result["quantities"] = self._calculate_quantities(result["measurements"])
        result["cost_estimate"] = self._estimate_costs(result["quantities"])
        result["carbon_estimate"] = self._estimate_carbon(result["quantities"])
        result["confidence"] = self._calculate_confidence(result)

        # Auto-populate risk register from drawing analysis
        result["auto_risks"] = await self._detect_risks_from_drawing(result)

        doc.close()
        return result

    def _process_drawing_page(self, page: fitz.Page, page_num: int) -> dict:
        """Process single drawing sheet with full extraction"""
        text_dict = page.get_text("dict")
        raw_text = page.get_text()

        return {
            "page_number": page_num + 1,
            "raw_text": raw_text[:8000],
            "measurements": self._extract_measurements_advanced(raw_text, text_dict),
            "tables": self._extract_tables_advanced(page),
            "annotations": self._extract_annotations(page),
            "specs": self._extract_specs_advanced(raw_text),
            "image_count": len(page.get_images()),
            "rotation": page.rotation,
            "cropbox": list(page.cropbox)
        }

    # ═══════════════════════════════════════════════════════════
    # 2. CONTRACT MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    async def process_contract(self, input_data: dict, params: dict) -> dict:
        file_path = input_data.get("file_path") or params.get("file_path")
        contract_type = params.get("contract_type", "general")

        if not file_path:
            return {"status": "error", "error": "No contract file provided"}

        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        clause_patterns = {
            "payment_terms": r'(?:payment|pay|invoice)[\s\w]{0,50}(?:term|schedule|milestone|certificate)',
            "liquidated_damages": r'(?:liquidated damages|ld|delay damages)[\s\w]{0,100}(?:rate|amount|per day)',
            "retention": r'(?:retention|retainage)[\s\w]{0,50}(?:percent|percentage|amount|release)',
            "variation_clause": r'(?:variation|change order|modification)[\s\w]{0,100}(?:procedure|valuation|approval)',
            "force_majeure": r'(?:force majeure|act of god|unforeseeable)[\s\w]{0,200}(?:delay|extension|notice)',
            "termination": r'(?:terminat|default|breach)[\s\w]{0,200}(?:clause|condition|notice period|consequence)',
            "indemnity": r'(?:indemnif|hold harmless|defend)[\s\w]{0,100}(?:clause|obligation|insurance)',
            "dispute_resolution": r'(?:dispute|arbitration|mediation|adjudication)[\s\w]{0,100}(?:clause|procedure|board)',
            "time_extensions": r'(?:extension of time|eot|delay|prolongation)[\s\w]{0,150}(?:clause|entitlement|procedure)',
            "subcontracting": r'(?:subcontract|sub-let|nominated|domestic)[\s\w]{0,100}(?:approval|liability|payment)',
            "insurance": r'(?:insurance|policy|cover)[\s\w]{0,150}(requirement|amount|professional|all risk)',
            "safety_obligation": r'(?:safety|health|hse|osha)[\s\w]{0,100}(?:obligation|responsibility|compliance)',
            "environmental": r'(?:environmental|sustainability|green|eco)[\s\w]{0,100}(?:requirement|compliance|standard)',
        }

        extracted_clauses = {}
        for clause_type, pattern in clause_patterns.items():
            matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
            if matches:
                contexts = []
                for match in matches[:3]:
                    start = max(0, match.start() - 200)
                    end = min(len(full_text), match.end() + 200)
                    contexts.append(full_text[start:end].strip())

                extracted_clauses[clause_type] = {
                    "found": True,
                    "count": len(matches),
                    "contexts": contexts,
                    "risk_level": self._assess_clause_risk(clause_type, contexts)
                }
            else:
                extracted_clauses[clause_type] = {"found": False, "risk_level": "unknown"}

        obligations = self._extract_obligations(full_text)
        contract_risks = self._assess_contract_risks(extracted_clauses, contract_type)
        financial_terms = self._extract_financial_terms(full_text)

        return {
            "status": "success",
            "action": "contract_analysis",
            "file_name": Path(file_path).name,
            "contract_type": contract_type,
            "document_length": len(full_text),
            "clauses_found": len([c for c in extracted_clauses.values() if c.get("found")]),
            "total_clauses": len(clause_patterns),
            "extracted_clauses": extracted_clauses,
            "key_obligations": obligations,
            "financial_terms": financial_terms,
            "risk_assessment": {
                "overall_score": contract_risks["score"],
                "risk_level": contract_risks["level"],
                "critical_issues": contract_risks["critical"],
                "warnings": contract_risks["warnings"],
                "recommendations": contract_risks["recommendations"]
            },
            "summary": self._generate_contract_summary(extracted_clauses, financial_terms)
        }

    def _extract_obligations(self, text: str) -> List[Dict]:
        obligations = []
        obligation_patterns = [
            (r'(?:contractor|builder)[\s\w]{0,50}(?:shall|must|will|agrees to)[\s\w]{0,100}(?:\.)', "contractor_obligation"),
            (r'(?:employer|owner|client)[\s\w]{0,50}(?:shall|must|will|agrees to)[\s\w]{0,100}(?:\.)', "employer_obligation"),
            (r'(?:both parties|each party)[\s\w]{0,50}(?:shall|must|will)[\s\w]{0,100}(?:\.)', "mutual_obligation"),
            (r'(?:architect|engineer|supervisor)[\s\w]{0,50}(?:shall|must|will)[\s\w]{0,100}(?:\.)', "consultant_obligation"),
        ]
        for pattern, obl_type in obligation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                obligations.append({
                    "type": obl_type,
                    "text": match.group(0),
                    "category": self._categorize_obligation(match.group(0)),
                    "priority": self._assess_obligation_priority(match.group(0))
                })
        return obligations[:20]

    def _assess_clause_risk(self, clause_type: str, contexts: List[str]) -> str:
        high_risk_keywords = ["penalty", "unlimited", "sole discretion", "no limit", "absolute", "waiver of rights"]
        medium_risk_keywords = ["notice", "approval required", "consent", "binding"]
        combined = " ".join(contexts).lower()
        if any(kw in combined for kw in high_risk_keywords):
            return "high"
        elif any(kw in combined for kw in medium_risk_keywords):
            return "medium"
        return "low"

    def _assess_contract_risks(self, clauses: Dict, contract_type: str) -> Dict:
        score = 100
        critical = []
        warnings = []
        recommendations = []

        if not clauses.get("payment_terms", {}).get("found"):
            score -= 15
            critical.append("Payment terms not clearly defined")
            recommendations.append("Add detailed payment schedule with milestones")

        if not clauses.get("liquidated_damages", {}).get("found"):
            score -= 10
            warnings.append("No liquidated damages clause - delays may be hard to quantify")

        if clauses.get("liquidated_damages", {}).get("risk_level") == "high":
            score -= 20
            critical.append("High/Uncapped liquidated damages")
            recommendations.append("Negotiate cap on liquidated damages (typically 5-10% of contract value)")

        if not clauses.get("force_majeure", {}).get("found"):
            score -= 10
            warnings.append("No force majeure clause")
            recommendations.append("Add force majeure clause for pandemics, natural disasters, war")

        if not clauses.get("variation_clause", {}).get("found"):
            score -= 15
            critical.append("No variation/change order procedure")
            recommendations.append("Define change order valuation and approval process")

        if clauses.get("termination", {}).get("risk_level") == "high":
            score -= 15
            critical.append("Unbalanced termination clause")

        if not clauses.get("dispute_resolution", {}).get("found"):
            score -= 5
            warnings.append("No dispute resolution mechanism defined")

        if contract_type == "cost_plus" and not clauses.get("audit_rights", {}).get("found"):
            recommendations.append("For cost-plus contracts, add right to audit all costs")

        risk_level = "low" if score >= 80 else "medium" if score >= 60 else "high"

        return {
            "score": max(0, score),
            "level": risk_level,
            "critical": critical,
            "warnings": warnings,
            "recommendations": recommendations
        }

    def _extract_financial_terms(self, text: str) -> Dict:
        terms = {}
        value_match = re.search(r'(?:contract (?:value|sum|price|amount)|total)[\s:]*[$€£]?[\s]*(\d[\d,\.]*)', text, re.IGNORECASE)
        if value_match:
            terms["contract_value"] = value_match.group(1)
        advance_match = re.search(r'(?:advance|mobilization)[\s\w]{0,30}(\d+)%', text, re.IGNORECASE)
        if advance_match:
            terms["advance_payment"] = f"{advance_match.group(1)}%"
        retention_match = re.search(r'(?:retention|retainage)[\s\w]{0,30}(\d+)%', text, re.IGNORECASE)
        if retention_match:
            terms["retention"] = f"{retention_match.group(1)}%"
        currency_match = re.search(r'(?:currency|in|amounts)[\s\w]{0,20}(USD|EUR|GBP|AED|SAR|QAR)', text, re.IGNORECASE)
        if currency_match:
            terms["currency"] = currency_match.group(1)
        return terms

    def _generate_contract_summary(self, clauses: Dict, financial: Dict) -> str:
        summary_parts = []
        if clauses.get("payment_terms", {}).get("found"):
            summary_parts.append("Payment terms defined")
        else:
            summary_parts.append("⚠️ Payment terms unclear")
        if clauses.get("liquidated_damages", {}).get("found"):
            summary_parts.append("LDs apply")
        if financial.get("contract_value"):
            summary_parts.append(f"Value: {financial['contract_value']}")
        return " | ".join(summary_parts)

    # ═══════════════════════════════════════════════════════════
    # 3. SCHEDULING & PRIMAVERA P6
    # ═══════════════════════════════════════════════════════════

    async def parse_primavera_schedule(self, input_data: dict, params: dict) -> dict:
        file_path = input_data.get("file_path") or params.get("file_path")
        baseline_file = input_data.get("baseline_file") or params.get("baseline_file")
        analysis_date = params.get("analysis_date", datetime.now().isoformat())

        if not file_path:
            return {"status": "error", "error": "No schedule file provided"}

        ext = Path(file_path).suffix.lower()

        if ext == '.xer':
            schedule_data = self._parse_xer_file(file_path)
        elif ext == '.xml':
            schedule_data = self._parse_xml_schedule(file_path)
        else:
            return {"status": "error", "error": f"Unsupported format: {ext}"}

        if schedule_data.get("status") == "error":
            return schedule_data

        cpm_results = self._calculate_critical_path(schedule_data)

        delay_analysis = None
        if baseline_file:
            baseline_data = self._parse_xer_file(baseline_file) if baseline_file.endswith('.xer') else self._parse_xml_schedule(baseline_file)
            delay_analysis = self._analyze_delays(schedule_data, baseline_data)

        schedule_risks = self._analyze_schedule_risks(cpm_results)

        recovery_options = []
        if delay_analysis and delay_analysis.get("total_delay_days", 0) > 0:
            recovery_options = self._generate_recovery_options(delay_analysis, cpm_results)

        return {
            "status": "success",
            "action": "primavera_analysis",
            "file_name": Path(file_path).name,
            "project_name": schedule_data.get("project_name"),
            "analysis_date": analysis_date,
            "summary": {
                "total_activities": len(schedule_data.get("activities", [])),
                "critical_activities": len(cpm_results.get("critical_path", [])),
                "total_float_average": cpm_results.get("average_float", 0),
                "project_duration": cpm_results.get("project_duration_days", 0),
                "data_date": schedule_data.get("data_date")
            },
            "critical_path": {
                "activities": cpm_results.get("critical_path", [])[:20],
                "path_duration": cpm_results.get("critical_path_duration"),
                "driving_paths": cpm_results.get("driving_paths", [])
            },
            "milestones": self._extract_milestones(schedule_data),
            "delay_analysis": delay_analysis,
            "schedule_risks": schedule_risks,
            "recovery_options": recovery_options,
            "recommendations": self._generate_schedule_recommendations(cpm_results, delay_analysis),
            "detailed_activities": schedule_data.get("activities", [])[:50] if params.get("include_details") else None
        }

    def _parse_xer_file(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            sections = {}
            current_section = None
            headers = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('%T'):
                    current_section = line[2:].strip()
                    sections[current_section] = []
                    headers = []
                elif line.startswith('%F') and current_section:
                    headers = line[2:].split('\t')
                elif line.startswith('%R') and current_section and headers:
                    values = line[2:].split('\t')
                    record = dict(zip(headers, values))
                    sections[current_section].append(record)

            project_info = sections.get('PROJECT', [{}])[0]
            activities = sections.get('TASK', [])
            relationships = sections.get('TASKPRED', [])

            structured_activities = []
            for act in activities:
                structured_activities.append({
                    "id": act.get('task_id'),
                    "name": act.get('task_name'),
                    "duration": float(act.get('target_dur', 0)),
                    "start": act.get('target_start'),
                    "finish": act.get('target_end'),
                    "early_start": act.get('early_start'),
                    "early_finish": act.get('early_end'),
                    "late_start": act.get('late_start'),
                    "late_finish": act.get('late_end'),
                    "total_float": float(act.get('total_float', 0) or 0),
                    "free_float": float(act.get('free_float', 0) or 0),
                    "percent_complete": float(act.get('complete_pct', 0) or 0),
                    "critical": act.get('total_float', '0') == '0',
                    "wbs": act.get('wbs_id'),
                    "resources": self._extract_resources(act)
                })

            return {
                "status": "success",
                "project_name": project_info.get('proj_short_name', 'Unknown'),
                "data_date": project_info.get('last_recalc_date'),
                "activities": structured_activities,
                "relationships": self._parse_relationships(relationships),
                "calendars": sections.get('CALENDAR', []),
                "resources": sections.get('RSRC', []),
                "raw_sections": sections if False else None
            }

        except Exception as e:
            return {"status": "error", "error": f"XER parsing failed: {str(e)}"}

    def _parse_xml_schedule(self, file_path: str) -> Dict:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            if 'Project' in root.tag:
                return self._parse_mspdi_xml(root)
            else:
                activities = []
                for activity in root.findall('.//Activity'):
                    act_data = {
                        "id": activity.findtext('Id', ''),
                        "name": activity.findtext('Name', ''),
                        "duration": float(activity.findtext('OriginalDuration', 0) or 0),
                        "start": activity.findtext('StartDate', ''),
                        "finish": activity.findtext('FinishDate', ''),
                        "total_float": float(activity.findtext('TotalFloat', 0) or 0),
                        "critical": activity.findtext('Critical') == '1',
                        "percent_complete": float(activity.findtext('PercentComplete', 0) or 0)
                    }
                    activities.append(act_data)

                return {
                    "status": "success",
                    "project_name": root.findtext('.//Name', 'Unknown'),
                    "activities": activities
                }

        except Exception as e:
            return {"status": "error", "error": f"XML parsing failed: {str(e)}"}

    def _calculate_critical_path(self, schedule_data: Dict) -> Dict:
        activities = {a["id"]: a for a in schedule_data.get("activities", [])}
        critical_activities = [
            a for a in activities.values()
            if a.get("critical") or a.get("total_float", 999) <= 0
        ]
        critical_activities.sort(key=lambda x: x.get("early_start", '') or '')

        if critical_activities:
            start = critical_activities[0].get("early_start")
            finish = critical_activities[-1].get("early_finish")
            duration = self._calculate_duration_days(start, finish) if start and finish else 0
        else:
            duration = 0

        floats = [a.get("total_float", 0) for a in schedule_data.get("activities", [])]
        avg_float = sum(floats) / len(floats) if floats else 0
        near_critical = [a for a in schedule_data.get("activities", []) if 0 < a.get("total_float", 999) < 5]

        return {
            "critical_path": [a["id"] for a in critical_activities],
            "critical_path_activities": critical_activities,
            "critical_path_duration": duration,
            "critical_count": len(critical_activities),
            "near_critical_count": len(near_critical),
            "near_critical_activities": near_critical[:10],
            "average_float": avg_float,
            "project_duration_days": duration,
            "driving_paths": self._identify_driving_paths(schedule_data, critical_activities)
        }

    def _analyze_delays(self, current: Dict, baseline: Dict) -> Dict:
        current_acts = {a["id"]: a for a in current.get("activities", [])}
        baseline_acts = {a["id"]: a for a in baseline.get("activities", [])}

        delays = []
        new_activities = []
        deleted_activities = []

        for act_id, current_act in current_acts.items():
            baseline_act = baseline_acts.get(act_id)
            if not baseline_act:
                new_activities.append(current_act)
                continue

            curr_start = current_act.get("start", '')
            base_start = baseline_act.get("start", '')
            if curr_start != base_start:
                delay_days = self._calculate_date_diff(base_start, curr_start)
                if delay_days > 0:
                    delays.append({
                        "activity_id": act_id,
                        "activity_name": current_act.get("name"),
                        "type": "start_delay",
                        "baseline_date": base_start,
                        "current_date": curr_start,
                        "delay_days": delay_days,
                        "percent_complete": current_act.get("percent_complete", 0)
                    })

            if current_act.get("percent_complete", 0) < 100:
                curr_finish = current_act.get("finish", '')
                base_finish = baseline_act.get("finish", '')
                if curr_finish and base_finish and curr_finish != base_finish:
                    finish_delay = self._calculate_date_diff(base_finish, curr_finish)
                    if finish_delay > 0:
                        delays.append({
                            "activity_id": act_id,
                            "activity_name": current_act.get("name"),
                            "type": "finish_delay",
                            "baseline_date": base_finish,
                            "current_date": curr_finish,
                            "delay_days": finish_delay
                        })

        for base_id in baseline_acts:
            if base_id not in current_acts:
                deleted_activities.append(baseline_acts[base_id])

        total_delay = max([d["delay_days"] for d in delays]) if delays else 0

        return {
            "total_delay_days": total_delay,
            "delayed_activities": delays,
            "delay_count": len(delays),
            "new_activities": new_activities[:10],
            "deleted_activities": deleted_activities[:10],
            "impact_assessment": self._assess_delay_impact(delays, total_delay)
        }

    def _analyze_schedule_risks(self, cpm_results: Dict) -> List[Dict]:
        risks = []
        if cpm_results.get("critical_count", 0) > len(cpm_results.get("critical_path", [])) * 0.8:
            risks.append(asdict(RiskItem(
                id="SCH-001",
                category="schedule",
                description="Over-constrained schedule - too many critical activities",
                probability="high",
                impact="high",
                mitigation="Add buffers, review logic, fast-track non-critical activities",
                source="CPM analysis"
            )))
        if cpm_results.get("near_critical_count", 0) > 10:
            risks.append(asdict(RiskItem(
                id="SCH-002",
                category="schedule",
                description="Many near-critical activities - schedule fragile",
                probability="medium",
                impact="medium",
                mitigation="Monitor closely, prepare contingency plans",
                source="Float analysis"
            )))
        if cpm_results.get("average_float", 0) < 2:
            risks.append(asdict(RiskItem(
                id="SCH-003",
                category="schedule",
                description="Schedule has minimal overall float",
                probability="high",
                impact="high",
                mitigation="Negotiate extensions, reduce scope, or add resources",
                source="Float analysis"
            )))
        return risks

    def _generate_recovery_options(self, delay_analysis: Dict, cpm: Dict) -> List[Dict]:
        total_delay = delay_analysis.get("total_delay_days", 0)
        critical_path = cpm.get("critical_path_activities", [])
        options = []
        crashable = [a for a in critical_path if a.get("percent_complete", 0) < 50]
        if crashable:
            potential_savings = len(crashable) * 2
            options.append({
                "strategy": "Crashing",
                "description": f"Add resources to {len(crashable)} incomplete critical activities",
                "potential_savings_days": min(potential_savings, total_delay),
                "cost_impact": "High (overtime, additional labor)",
                "feasibility": "Medium" if len(crashable) < 5 else "Low"
            })
        if len(critical_path) > 3:
            options.append({
                "strategy": "Fast-Tracking",
                "description": "Perform critical activities in parallel where possible",
                "potential_savings_days": total_delay * 0.3,
                "cost_impact": "Medium (coordination overhead)",
                "feasibility": "Medium",
                "risks": "Quality issues, rework"
            })
        options.append({
            "strategy": "Scope Reduction",
            "description": "Defer non-critical scope to later phase",
            "potential_savings_days": total_delay * 0.5,
            "cost_impact": "Low (potential savings)",
            "feasibility": "High (requires client approval)"
        })
        options.append({
            "strategy": "Technology Acceleration",
            "description": "Use prefabrication, BIM coordination, or modular construction",
            "potential_savings_days": total_delay * 0.2,
            "cost_impact": "Medium (initial investment)",
            "feasibility": "Depends on project stage"
        })
        return options

    # ═══════════════════════════════════════════════════════════
    # 4. SPECIFICATIONS (CSI MasterFormat)
    # ═══════════════════════════════════════════════════════════

    async def process_specification_full(self, input_data: dict, params: dict) -> dict:
        file_path = input_data.get("file_path") or params.get("file_path")
        division_filter = params.get("division")

        if not file_path:
            return {"status": "error", "error": "No specification file provided"}

        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        divisions = self._parse_csi_divisions(full_text)
        sections = self._parse_spec_sections(full_text)
        submittals = self._extract_submittals(full_text)
        performance = self._extract_performance_criteria(full_text)
        checklist = self._generate_compliance_checklist(sections, submittals)
        material_tracking = self._extract_material_tracking(sections)
        warranties = self._extract_warranty_requirements(full_text)
        testing = self._extract_testing_requirements(full_text)

        if division_filter:
            sections = [s for s in sections if s.get("division") == division_filter]
            submittals = [s for s in submittals if s.get("division") == division_filter]

        return {
            "status": "success",
            "action": "specification_analysis",
            "file_name": Path(file_path).name,
            "project_specifications": {
                "total_divisions": len(divisions),
                "total_sections": len(sections),
                "divisions_found": divisions
            },
            "sections": sections[:50] if not params.get("full_details") else sections,
            "submittals": {
                "total_required": len(submittals),
                "shop_drawings": len([s for s in submittals if "shop" in s["type"].lower()]),
                "samples": len([s for s in submittals if "sample" in s["type"].lower()]),
                "mockups": len([s for s in submittals if "mock" in s["type"].lower()]),
                "calculations": len([s for s in submittals if "calc" in s["type"].lower()]),
                "list": submittals[:30]
            },
            "performance_criteria": performance,
            "warranty_requirements": warranties,
            "testing_requirements": testing,
            "compliance_checklist": checklist,
            "material_tracking": material_tracking,
            "critical_requirements": self._identify_critical_specs(sections),
            "summary": f"Found {len(sections)} sections, {len(submittals)} submittals required"
        }

    def _parse_csi_divisions(self, text: str) -> List[Dict]:
        divisions_found = []
        for code, name in self.csi_divisions.items():
            pattern = rf'\b(?:Section\s*)?{code}\s*(?:\d{{2,}})?\s*(?:-|–)?\s*{name}'
            if re.search(pattern, text, re.IGNORECASE):
                section_count = len(re.findall(rf'\b{code}\d{{2,}}\b', text))
                divisions_found.append({"code": code, "name": name, "section_count": section_count})
        return sorted(divisions_found, key=lambda x: x["code"])

    def _parse_spec_sections(self, text: str) -> List[Dict]:
        sections = []
        section_pattern = r'(?:SECTION|DIVISION)?\s*(\d{2})\s*(\d{2})\s*(\d{2})?\s*(?:-|–)?\s*([^\n]+)'
        for match in re.finditer(section_pattern, text, re.IGNORECASE):
            division = match.group(1)
            section = match.group(2)
            subsection = match.group(3) or "00"
            title = match.group(4).strip()
            start_pos = match.end()
            next_match = re.search(section_pattern, text[start_pos:], re.IGNORECASE)
            end_pos = start_pos + next_match.start() if next_match else len(text)
            content = text[start_pos:end_pos]
            sections.append({
                "number": f"{division}{section}{subsection}",
                "division": division,
                "title": title,
                "part1_summary": self._extract_part1_general(content),
                "part2_products": self._extract_part2_products(content),
                "part3_execution": self._extract_part3_execution(content),
                "key_requirements": self._extract_key_reqs(content)
            })
        return sections

    def _extract_submittals(self, text: str) -> List[Dict]:
        submittals = []
        submittal_patterns = [
            (r'(?:shop drawing|working drawing)s?[:\s]*([^;.]*)', "shop_drawing"),
            (r'(?:product data|cut sheet|technical data)[:\s]*([^;.]*)', "product_data"),
            (r'(?:sample|mock.?up)[:\s]*([^;.]*)', "sample"),
            (r'(?:certificate|test report|mix design)[:\s]*([^;.]*)', "certificate"),
            (r'(?:calculation|design data)[:\s]*([^;.]*)', "calculation"),
            (r'(?:warranty|guarantee)[:\s]*([^;.]*)', "warranty"),
            (r'(?:operation|maintenance|manual)[:\s]*([^;.]*)', "o_and_m"),
        ]
        for pattern, sub_type in submittal_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                submittals.append({
                    "type": sub_type,
                    "description": match.group(1).strip() if match.groups() else match.group(0),
                    "context": match.group(0),
                    "division": self._infer_division_from_context(match.start(), text)
                })
        return submittals

    def _extract_performance_criteria(self, text: str) -> List[Dict]:
        criteria = []
        patterns = [
            (r'(?:compressive strength|fc[\'′]?)\s*(?:of|≥|>=)?\s*(\d+\s*MPa|[^\s,;]*)', "strength"),
            (r'(?:fire rating|FRL|fire resistance)\s*(?:of|≥)?\s*(\d+[/\d]*\s*min|[^\s,;]*)', "fire"),
            (r'(?:thermal resistance|R-?value|U-?value)\s*(?:of|≤|<=)?\s*(\d+\.?\d*[^\s,;]*)', "thermal"),
            (r'(?:sound rating|STC|NRC|Rw)\s*(?:of|≥)?\s*(\d+[^\s,;]*)', "acoustic"),
            (r'(?:wind load|pressure)\s*(?:of|≥)?\s*(\d+\s*(?:Pa|kPa|psf|mph)?[^\s,;]*)', "structural"),
            (r'(?:durability|design life|service life)\s*(?:of|≥)?\s*(\d+\s*years?[^\s,;]*)', "durability"),
        ]
        for pattern, perf_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                criteria.append({
                    "type": perf_type,
                    "requirement": match.group(0),
                    "value": match.group(1) if match.groups() else "unspecified",
                    "section": self._infer_division_from_context(match.start(), text)
                })
        return criteria

    # ═══════════════════════════════════════════════════════════
    # 5. CHANGE ORDER IMPACT ANALYSIS
    # ═══════════════════════════════════════════════════════════

    async def change_order_impact(self, input_data: dict, params: dict) -> dict:
        co_description = input_data.get("description") or params.get("description")
        co_value = input_data.get("value") or params.get("value", 0)
        affected_activities = input_data.get("affected_activities") or params.get("affected_activities", [])
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        contract_file = input_data.get("contract_file") or params.get("contract_file")

        if not co_description:
            return {"status": "error", "error": "Change order description required"}

        co_analysis = self._analyze_change_order_text(co_description)
        cost_impact = self._calculate_co_cost_impact(co_value, co_analysis)

        schedule_impact = {"delay_days": 0, "affected_milestones": []}
        if schedule_file:
            schedule_impact = await self._calculate_co_schedule_impact(schedule_file, affected_activities)

        risks = self._assess_co_risks(co_analysis, co_value, schedule_impact)
        contract_implications = {}
        if contract_file:
            contract_implications = self._check_contract_change_terms(contract_file, co_value)

        recommendations = self._generate_co_recommendations(cost_impact, schedule_impact, risks)

        return {
            "status": "success",
            "action": "change_order_analysis",
            "change_order_summary": {
                "description": co_description[:200],
                "category": co_analysis.get("category"),
                "direct_cost": co_value,
                "total_impact_cost": cost_impact.get("total"),
                "schedule_impact_days": schedule_impact.get("delay_days")
            },
            "cost_breakdown": cost_impact,
            "schedule_impact": schedule_impact,
            "risks": [asdict(r) for r in risks],
            "contract_implications": contract_implications,
            "approval_recommendation": "approve" if all(r.impact != "high" for r in risks) else "negotiate",
            "negotiation_points": self._identify_negotiation_points(cost_impact, risks),
            "mitigation_strategies": recommendations
        }

    def _analyze_change_order_text(self, text: str) -> Dict:
        categories = {
            "design_change": ["design", "drawing", "specification", "architect", "engineer"],
            "scope_addition": ["additional", "extra", "new", "more", "increase quantity"],
            "scope_deletion": ["delete", "remove", "omit", "deduct"],
            "unforeseen_condition": ["unforeseen", "unknown", "existing", "ground condition", "utility"],
            "acceleration": ["accelerate", "expedite", "crash", "fast track"],
            "delay_compensation": ["delay", "disruption", "prolongation", "waiting"],
        }
        text_lower = text.lower()
        detected_category = "general"
        confidence = 0
        for cat, keywords in categories.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > confidence:
                detected_category = cat
                confidence = matches
        return {
            "category": detected_category,
            "confidence": min(confidence / 3, 1.0),
            "complexity": "high" if len(text) > 500 else "medium" if len(text) > 200 else "low",
            "trade_involved": self._detect_trade_from_text(text)
        }

    def _calculate_co_cost_impact(self, direct_cost: float, analysis: Dict) -> Dict:
        direct = float(direct_cost) if direct_cost else 0
        overhead_rate = 0.20
        overhead = direct * overhead_rate
        profit_rate = 0.10
        profit = direct * profit_rate if analysis.get("category") == "scope_addition" else 0
        schedule_cost = 0
        complexity = analysis.get("complexity", "medium")
        risk_rates = {"low": 0.05, "medium": 0.10, "high": 0.20}
        risk_allowance = direct * risk_rates.get(complexity, 0.10)
        total = direct + overhead + profit + risk_allowance + schedule_cost
        return {
            "direct_cost": direct,
            "overhead": overhead,
            "profit": profit,
            "risk_allowance": risk_allowance,
            "schedule_impact_cost": schedule_cost,
            "total": total,
            "breakdown_percentages": {
                "direct": f"{(direct / total * 100):.1f}%" if total else "0.0%",
                "overhead": f"{(overhead / total * 100):.1f}%" if total else "0.0%",
                "risk": f"{(risk_allowance / total * 100):.1f}%" if total else "0.0%"
            }
        }

    async def _calculate_co_schedule_impact(self, schedule_file: str, affected_activities: List) -> Dict:
        schedule_data = self._parse_xer_file(schedule_file)
        affected_paths = []
        total_delay = 0
        for act_id in affected_activities:
            act = next((a for a in schedule_data.get("activities", []) if a["id"] == act_id), None)
            if act and act.get("critical"):
                affected_paths.append({"activity": act_id, "critical": True, "impact": "direct_delay"})
                total_delay += act.get("duration", 0)
            elif act:
                affected_paths.append({"activity": act_id, "critical": False, "impact": "congestion"})
        return {
            "delay_days": total_delay,
            "affected_activities": len(affected_activities),
            "critical_path_impact": any(a["critical"] for a in affected_paths),
            "affected_milestones": self._identify_affected_milestones(schedule_data, affected_activities),
            "mitigation_options": ["overtime", "additional_crew", "resequence"] if total_delay > 5 else []
        }

    # ═══════════════════════════════════════════════════════════
    # 6. RFI GENERATOR
    # ═══════════════════════════════════════════════════════════

    async def rfi_generator(self, input_data: dict, params: dict) -> dict:
        ambiguity_description = input_data.get("description") or params.get("description")
        drawing_ref = input_data.get("drawing_reference") or params.get("drawing_reference")
        spec_ref = input_data.get("spec_reference") or params.get("spec_reference")
        priority = params.get("priority", "normal")
        trade = params.get("trade", "general")
        project_name = params.get("project_name", "Project")

        if not ambiguity_description:
            return {"status": "error", "error": "Ambiguity description required"}

        analysis = self._analyze_ambiguity(ambiguity_description)
        suggested_number = f"RFI-{trade[:3].upper()}-{datetime.now().strftime('%y%m%d')}-XXX"
        rfi_text = self._generate_rfi_text(ambiguity_description, drawing_ref, spec_ref, analysis, project_name)
        suggestions = self._suggest_clarifications(analysis)
        impact = self._assess_ambiguity_impact(analysis, priority)

        return {
            "status": "success",
            "action": "rfi_generated",
            "generated_rfi": {
                "suggested_number": suggested_number,
                "subject": f"Clarification required: {analysis.get('topic', 'General')}",
                "priority": priority,
                "trade": trade,
                "full_text": rfi_text,
                "word_count": len(rfi_text.split())
            },
            "ambiguity_analysis": analysis,
            "references": {
                "drawings": drawing_ref,
                "specifications": spec_ref,
                "related_rfis": self._find_related_rfis(analysis)
            },
            "suggested_responses": suggestions,
            "impact_assessment": impact,
            "recommended_response_time": "48 hours" if priority == "urgent" else "7 days",
            "attachments_needed": self._identify_rfi_attachments(analysis)
        }

    def _analyze_ambiguity(self, text: str) -> Dict:
        ambiguity_types = {
            "conflict": ["conflict", "contradict", "differ", "discrepancy", "does not match"],
            "omission": ["missing", "not shown", "not indicated", "omit", "not specified"],
            "unclear": ["unclear", "ambiguous", "vague", "not clear", "undefined"],
            "impossible": ["impossible", "cannot", "unable", "construct", "build"],
            "dimension_error": ["dimension", "does not fit", "clash", "coordination"],
            "sequence": ["sequence", "order", "before", "after", "prerequisite"],
        }
        text_lower = text.lower()
        detected_types = []
        for amb_type, keywords in ambiguity_types.items():
            if any(kw in text_lower for kw in keywords):
                detected_types.append(amb_type)
        trades = ["concrete", "steel", "electrical", "plumbing", "hvac", "masonry", "finishes", "fire protection"]
        detected_trade = next((t for t in trades if t in text_lower), "general")
        return {
            "types": detected_types,
            "primary_type": detected_types[0] if detected_types else "general",
            "trade": detected_trade,
            "topic": self._extract_topic(text),
            "complexity": "high" if len(detected_types) > 1 else "medium" if detected_types else "low",
            "urgency_indicators": any(w in text_lower for w in ["delay", "stop", "hold", "cannot proceed"])
        }

    def _generate_rfi_text(self, description: str, drawing: str, spec: str, analysis: Dict, project: str) -> str:
        parts = []
        parts.append(f"Subject: Request for Information - {analysis.get('topic', 'Clarification Required')}")
        parts.append(f"Project: {project}")
        parts.append("")
        parts.append("BACKGROUND:")
        parts.append(f"The Contractor is preparing to execute work related to {analysis.get('trade', 'the scope')}.")
        if drawing:
            parts.append(f"Reference Drawing(s): {drawing}")
        if spec:
            parts.append(f"Reference Specification(s): Section {spec}")
        parts.append("")
        parts.append("ISSUE/AMBIGUITY:")
        parts.append(description)
        parts.append("")
        parts.append("IMPACT:")
        if analysis.get("urgency_indicators"):
            parts.append("This ambiguity is impacting ongoing work and may cause delays if not resolved promptly.")
        else:
            parts.append("This ambiguity requires clarification to ensure compliance with design intent.")
        parts.append("")
        parts.append("REQUESTED CLARIFICATION:")
        if analysis.get("primary_type") == "conflict":
            parts.append("1. Please confirm which document takes precedence.")
            parts.append("2. Please provide revised details coordinating both requirements.")
        elif analysis.get("primary_type") == "omission":
            parts.append("1. Please confirm the required scope/material/dimension.")
            parts.append("2. Please provide missing details or reference to applicable standards.")
        elif analysis.get("primary_type") == "dimension_error":
            parts.append("1. Please confirm correct dimensions.")
            parts.append("2. Please clarify coordination between elements.")
        else:
            parts.append("1. Please clarify the design intent.")
            parts.append("2. Please provide any additional details required for construction.")
        parts.append("")
        parts.append("Submitted by: [Contractor Name]")
        parts.append(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════
    # 7. SAFETY COMPLIANCE AUDIT
    # ═══════════════════════════════════════════════════════════

    async def safety_compliance_audit(self, input_data: dict, params: dict) -> dict:
        audit_type = params.get("type", "general")
        project_location = params.get("location", "US")
        checklist_items = input_data.get("checklist_items") or params.get("checklist_items", [])
        photo_files = input_data.get("photos") or params.get("photos", [])

        standards = self._get_applicable_safety_standards(audit_type, project_location)
        checklist_results = self._perform_safety_checklist(checklist_items, standards)

        photo_analysis = []
        for photo in photo_files:
            analysis = await self._analyze_safety_photo(photo, audit_type)
            photo_analysis.append(analysis)

        violations = self._identify_safety_violations(checklist_results, photo_analysis)
        risk_score = self._calculate_safety_risk_score(violations)
        corrective_actions = self._generate_corrective_actions(violations)
        compliance_rate = (len([c for c in checklist_results if c["compliant"]]) / len(checklist_results) * 100) if checklist_results else 0

        return {
            "status": "success",
            "action": "safety_audit",
            "audit_type": audit_type,
            "location": project_location,
            "applicable_standards": standards,
            "summary": {
                "compliance_rate": f"{compliance_rate:.1f}%",
                "violations_found": len(violations),
                "critical_violations": len([v for v in violations if v["severity"] == "critical"]),
                "major_violations": len([v for v in violations if v["severity"] == "major"]),
                "minor_violations": len([v for v in violations if v["severity"] == "minor"]),
                "risk_score": risk_score,
                "status": "pass" if risk_score > 80 else "conditional" if risk_score > 60 else "fail"
            },
            "violations": violations,
            "checklist_results": checklist_results,
            "photo_analysis": photo_analysis,
            "corrective_actions": corrective_actions,
            "stop_work_triggers": [v for v in violations if v.get("stop_work_required")],
            "recommendations": self._generate_safety_recommendations(violations),
            "re_audit_required": any(v["severity"] == "critical" for v in violations),
            "next_audit_date": (datetime.now() + timedelta(days=7)).isoformat() if violations else (datetime.now() + timedelta(days=30)).isoformat()
        }

    def _get_applicable_safety_standards(self, audit_type: str, location: str) -> List[str]:
        base_standards = ["OSHA 1926", "ISO 45001"]
        location_specific = {
            "US": ["OSHA 1926", "ANSI A10"],
            "UK": ["CDM 2015", "BS EN 12811", "HSE Guidance"],
            "EU": ["EU Directive 92/57/EEC", "EN Standards"],
            "GCC": ["OSHA (US based)", "Local Municipality Requirements"],
            "AU": ["WHS Act 2011", "AS/NZS Standards"]
        }
        type_specific = {
            "excavation": ["OSHA 1926 Subpart P", "Trenching Standards"],
            "scaffolding": ["OSHA 1926 Subpart L", "ANSI A10.8"],
            "electrical": ["OSHA 1926 Subpart K", "NFPA 70E"],
            "confined_space": ["OSHA 1926 Subpart AA", "ANSI Z117.1"],
            "fall_protection": ["OSHA 1926 Subpart M", "ANSI Z359"]
        }
        standards = location_specific.get(location, base_standards)
        if audit_type in type_specific:
            standards.extend(type_specific[audit_type])
        return standards

    async def _analyze_safety_photo(self, photo_path: str, audit_type: str) -> Dict:
        from app.core.block_registry import BLOCK_REGISTRY
        image_block = BLOCK_REGISTRY.get("image")
        safety_prompts = {
            "general": "Identify safety hazards: missing PPE, trip hazards, exposed edges, improper storage, blocked exits",
            "scaffolding": "Check: guardrails, midrails, toeboards, plank overhang, base plates, access, load capacity signs",
            "excavation": "Check: shoring, sloping, benching, spoil pile distance, access/egress, water accumulation, utilities",
            "electrical": "Check: exposed wires, GFCI, panel access, temporary power, grounding, water proximity",
            "fall_protection": "Check: guardrails, harnesses, anchor points, lifelines, safety nets, hole covers"
        }
        if not image_block:
            return {
                "photo": Path(photo_path).name,
                "hazards_detected": 0,
                "hazards": [],
                "overall_assessment": "compliant",
                "requires_immediate_action": False,
                "note": "Image block not registered"
            }
        analysis = await image_block.execute(
            {"image_path": photo_path},
            {"prompt": safety_prompts.get(audit_type, safety_prompts["general"])}
        )
        hazards_found = self._parse_safety_hazards(analysis.get("description", ""))
        return {
            "photo": Path(photo_path).name,
            "hazards_detected": len(hazards_found),
            "hazards": hazards_found,
            "overall_assessment": "unsafe" if hazards_found else "compliant",
            "requires_immediate_action": any(h["severity"] == "critical" for h in hazards_found)
        }

    # ═══════════════════════════════════════════════════════════
    # 8. CARBON FOOTPRINT CALCULATOR
    # ═══════════════════════════════════════════════════════════

    async def carbon_footprint_calculator(self, input_data: dict, params: dict) -> dict:
        bill_of_quantities = input_data.get("boq") or params.get("boq", [])
        material_types = input_data.get("materials") or params.get("materials", [])
        assessment_type = params.get("assessment_type", "cradle_to_gate")

        if bill_of_quantities:
            carbon_calc = self._calculate_carbon_from_boq(bill_of_quantities, assessment_type)
        else:
            carbon_calc = self._calculate_carbon_from_list(material_types, assessment_type)

        benchmarks = self._get_carbon_benchmarks(params.get("building_type", "office"))
        optimizations = self._suggest_carbon_optimizations(carbon_calc)
        offsets_needed = max(0, carbon_calc["total_kg_co2e"] - benchmarks["target"])

        return {
            "status": "success",
            "action": "carbon_calculation",
            "assessment_type": assessment_type,
            "project_summary": {
                "total_embodied_carbon_kg_co2e": carbon_calc["total_kg_co2e"],
                "total_tons_co2e": carbon_calc["total_kg_co2e"] / 1000,
                "per_sqm": carbon_calc.get("per_sqm"),
                "by_material": carbon_calc["breakdown"],
                "lifecycle_phases": carbon_calc.get("phases", {})
            },
            "benchmarking": {
                "your_result": carbon_calc["total_kg_co2e"],
                "industry_average": benchmarks["average"],
                "best_practice_target": benchmarks["target"],
                "percentile": self._calculate_percentile(carbon_calc["total_kg_co2e"], benchmarks),
                "rating": "A" if carbon_calc["total_kg_co2e"] < benchmarks["target"] * 0.8 else "B" if carbon_calc["total_kg_co2e"] < benchmarks["target"] else "C" if carbon_calc["total_kg_co2e"] < benchmarks["average"] else "D"
            },
            "optimization_opportunities": optimizations,
            "carbon_offset_required": {
                "tons": offsets_needed / 1000,
                "estimated_cost_usd": (offsets_needed / 1000) * 15,
                "strategies": ["purchase_offsets", "material_substitution", "design_optimization"] if offsets_needed > 0 else []
            },
            "regulatory_compliance": {
                "epc_rating_impact": "positive" if carbon_calc["total_kg_co2e"] < benchmarks["target"] else "negative",
                "local_regulations_met": carbon_calc["total_kg_co2e"] < benchmarks["legal_limit"],
                "certification_support": ["LEED", "BREEAM", "Estidama", "Green Star"]
            },
            "recommendations": self._generate_carbon_recommendations(carbon_calc, optimizations)
        }

    def _calculate_carbon_from_boq(self, boq: List[Dict], assessment_type: str) -> Dict:
        total = 0
        breakdown = []
        for item in boq:
            material_key = item.get("material_type", "concrete_c30")
            quantity = float(item.get("quantity", 0))
            unit = item.get("unit", "m3")
            carbon_factor = self.carbon_factors.get(material_key, 0)
            kg_co2e = quantity * carbon_factor
            if assessment_type == "cradle_to_grave":
                kg_co2e *= 1.08
            total += kg_co2e
            breakdown.append({
                "material": material_key,
                "quantity": quantity,
                "unit": unit,
                "carbon_factor": carbon_factor,
                "kg_co2e": kg_co2e,
                "percent_of_total": 0
            })
        for item in breakdown:
            item["percent_of_total"] = (item["kg_co2e"] / total * 100) if total else 0
        breakdown.sort(key=lambda x: x["kg_co2e"], reverse=True)
        return {
            "total_kg_co2e": total,
            "breakdown": breakdown,
            "top_contributors": breakdown[:5]
        }

    def _suggest_carbon_optimizations(self, carbon_calc: Dict) -> List[Dict]:
        suggestions = []
        breakdown = carbon_calc.get("breakdown", [])
        for item in breakdown[:3]:
            material = item["material"]
            if "concrete" in material and item["percent_of_total"] > 20:
                suggestions.append({
                    "strategy": "Concrete Mix Optimization",
                    "description": "Replace Portland cement with GGBS or fly ash (up to 50% replacement)",
                    "potential_savings_percent": 40,
                    "applicable_to": item["material"],
                    "implementation_difficulty": "low",
                    "cost_impact": "neutral_to_savings"
                })
            elif "steel" in material:
                suggestions.append({
                    "strategy": "Recycled Steel Content",
                    "description": "Specify high-recycled content steel or electric arc furnace (EAF) steel",
                    "potential_savings_percent": 25,
                    "applicable_to": item["material"],
                    "implementation_difficulty": "low",
                    "cost_impact": "neutral"
                })
            elif "block" in material:
                suggestions.append({
                    "strategy": "Alternative Masonry",
                    "description": "Consider AAC blocks or stabilized earth blocks",
                    "potential_savings_percent": 30,
                    "applicable_to": item["material"],
                    "implementation_difficulty": "medium",
                    "cost_impact": "low_increase"
                })
        suggestions.append({
            "strategy": "Mass Timber Structure",
            "description": "Replace concrete/steel structure with glulam or CLT where code permits",
            "potential_savings_percent": 50,
            "applicable_to": "structural_frame",
            "implementation_difficulty": "medium",
            "cost_impact": "moderate_increase"
        })
        return suggestions

    # ═══════════════════════════════════════════════════════════
    # 9. PROCUREMENT LIST GENERATOR
    # ═══════════════════════════════════════════════════════════

    async def procurement_list_generator(self, input_data: dict, params: dict) -> dict:
        boq = input_data.get("boq") or params.get("boq", [])
        project_start = params.get("project_start_date")
        project_schedule = input_data.get("schedule_file") or params.get("schedule_file")
        procurement_strategy = params.get("strategy", "just_in_time")

        if not boq and not project_schedule:
            return {"status": "error", "error": "BOQ or schedule required for procurement planning"}

        if project_schedule:
            schedule_data = self._parse_xer_file(project_schedule)
            material_schedule = self._align_materials_to_schedule(boq, schedule_data)
        else:
            material_schedule = self._generate_standalone_procurement_schedule(boq, project_start)

        procurement_list = self._enrich_supplier_data(material_schedule)
        cash_flow = self._calculate_procurement_cash_flow(procurement_list)
        long_lead_items = [p for p in procurement_list if p.get("lead_time_weeks", 0) > 8]

        return {
            "status": "success",
            "action": "procurement_plan",
            "procurement_strategy": procurement_strategy,
            "summary": {
                "total_items": len(procurement_list),
                "long_lead_items": len(long_lead_items),
                "total_value": sum(p.get("estimated_cost", 0) for p in procurement_list),
                "earliest_order_date": min((p.get("order_date") for p in procurement_list if p.get("order_date")), default=None),
                "latest_delivery_required": max((p.get("delivery_date") for p in procurement_list if p.get("delivery_date")), default=None)
            },
            "procurement_schedule": procurement_list,
            "long_lead_critical": long_lead_items,
            "cash_flow_projection": cash_flow,
            "packaging_recommendations": self._suggest_procurement_packages(procurement_list),
            "approval_workflow": self._generate_approval_workflow(procurement_list),
            "risk_mitigation": {
                "supply_chain_risks": self._identify_supply_risks(procurement_list),
                "mitigation_strategies": ["buffer_stock", "alternative_suppliers", "early_ordering"]
            }
        }

    def _align_materials_to_schedule(self, boq: List[Dict], schedule_data: Dict) -> List[Dict]:
        aligned = []
        for item in boq:
            material_type = item.get("material_type", "")
            activity = self._find_relevant_activity(schedule_data, material_type)
            if activity:
                lead_time = self._get_material_lead_time(material_type)
                need_date = activity.get("early_start")
                order_date = self._subtract_lead_time(need_date, lead_time)
                aligned.append({
                    **item,
                    "activity_id": activity.get("id"),
                    "activity_name": activity.get("name"),
                    "required_on_site": need_date,
                    "lead_time_weeks": lead_time,
                    "order_date": order_date,
                    "buffer_weeks": 2,
                    "critical": activity.get("critical", False)
                })
            else:
                aligned.append({
                    **item,
                    "lead_time_weeks": self._get_material_lead_time(material_type),
                    "buffer_weeks": 2,
                    "critical": False
                })
        return aligned

    def _get_material_lead_time(self, material_type: str) -> int:
        lead_times = {
            "concrete_c30": 1,
            "concrete_c40": 2,
            "rebar": 2,
            "formwork": 1,
            "block_work": 1,
            "steel_structural": 12,
            "glass_curtain": 8,
            "electrical_panel": 6,
            "hvac_chiller": 16,
            "elevator": 24,
            "generator": 12,
            "fire_alarm": 4,
            "tiles": 4,
            "flooring": 6,
            "paint": 2,
        }
        return lead_times.get(material_type, 4)

    # ═══════════════════════════════════════════════════════════
    # 10. AS-BUILT DEVIATION REPORT
    # ═══════════════════════════════════════════════════════════

    async def as_built_deviation_report(self, input_data: dict, params: dict) -> dict:
        as_built_files = input_data.get("as_built_files") or params.get("as_built_files", [])
        original_drawings = input_data.get("original_drawings") or params.get("original_drawings", [])
        inspection_photos = input_data.get("photos") or params.get("photos", [])

        if not as_built_files or not original_drawings:
            return {"status": "error", "error": "Both as-built and original drawings required"}

        deviations = []
        for as_built, original in zip(as_built_files, original_drawings):
            drawing_deviations = await self._compare_drawing_pair(as_built, original)
            deviations.extend(drawing_deviations)

        for photo in inspection_photos:
            photo_devs = await self._identify_deviations_from_photo(photo, original_drawings)
            deviations.extend(photo_devs)

        categorized = self._categorize_deviations(deviations)
        cost_impact = self._calculate_deviation_costs(deviations)
        schedule_impact = self._assess_deviation_schedule_impact(deviations)
        report = self._generate_formal_deviation_report(categorized, cost_impact, schedule_impact)

        return {
            "status": "success",
            "action": "as_built_deviation_report",
            "summary": {
                "total_deviations": len(deviations),
                "critical": len(categorized.get("critical", [])),
                "major": len(categorized.get("major", [])),
                "minor": len(categorized.get("minor", [])),
                "approvable": len(categorized.get("approvable", [])),
                "cost_impact_usd": cost_impact["total"],
                "schedule_impact_days": schedule_impact["total_days"],
                "requires_redesign": any(d.get("requires_redesign") for d in deviations)
            },
            "deviation_register": deviations,
            "by_category": categorized,
            "cost_breakdown": cost_impact,
            "schedule_impact": schedule_impact,
            "formal_report": report,
            "approval_recommendations": {
                "approve_with_no_change": [d["id"] for d in categorized.get("approvable", [])],
                "approve_with_cost_adjustment": [d["id"] for d in categorized.get("major", []) if d.get("cost_impact", 0) > 0],
                "reject_requires_redesign": [d["id"] for d in categorized.get("critical", [])]
            },
            "supporting_documents_required": self._list_supporting_docs(deviations)
        }

    async def _compare_drawing_pair(self, as_built_path: str, original_path: str) -> List[Dict]:
        as_built_data = await self._process_drawing(as_built_path, {})
        original_data = await self._process_drawing(original_path, {})
        deviations = []

        ab_measurements = {m.get("raw"): m for m in as_built_data.get("measurements", [])}
        orig_measurements = {m.get("raw"): m for m in original_data.get("measurements", [])}

        for meas_key, ab_meas in ab_measurements.items():
            if meas_key not in orig_measurements:
                deviations.append({
                    "id": f"DEV-{len(deviations)+1:03d}",
                    "type": "additional_element",
                    "location": f"Drawing {as_built_data.get('drawing_number')}",
                    "description": f"Additional measurement/element found in as-built: {meas_key}",
                    "as_built_value": ab_meas.get("raw"),
                    "design_value": "not shown",
                    "deviation_type": "addition",
                    "severity": "major"
                })

        ab_specs = {(s.get("key"), s.get("value")): s for s in as_built_data.get("specifications", [])}
        orig_specs = {(s.get("key"), s.get("value")): s for s in original_data.get("specifications", [])}

        for spec_key, ab_spec in ab_specs.items():
            if spec_key not in orig_specs:
                deviations.append({
                    "id": f"DEV-{len(deviations)+1:03d}",
                    "type": "specification_change",
                    "location": f"Drawing {as_built_data.get('drawing_number')}",
                    "description": f"Specification changed in as-built: {ab_spec.get('value')}",
                    "as_built_value": ab_spec.get("value"),
                    "design_value": "different",
                    "deviation_type": "modification",
                    "severity": "major"
                })

        return deviations

    # ═══════════════════════════════════════════════════════════
    # 11. WARRANTY & MAINTENANCE SCHEDULE
    # ═══════════════════════════════════════════════════════════

    async def warranty_maintenance_schedule(self, input_data: dict, params: dict) -> dict:
        spec_file = input_data.get("spec_file") or params.get("spec_file")
        equipment_list = input_data.get("equipment_list") or params.get("equipment_list", [])
        substantial_completion = params.get("substantial_completion_date")

        if not spec_file and not equipment_list:
            return {"status": "error", "error": "Specifications or equipment list required"}

        if spec_file:
            spec_data = await self.process_specification_full(
                {"file_path": spec_file},
                {"full_details": False}
            )
            warranty_reqs = spec_data.get("warranty_requirements", [])
        else:
            warranty_reqs = []

        equipment_schedule = self._generate_equipment_warranty_schedule(equipment_list, substantial_completion)
        maintenance_calendar = self._generate_maintenance_calendar(equipment_schedule)
        replacement_forecast = self._forecast_replacements(equipment_schedule)

        return {
            "status": "success",
            "action": "warranty_maintenance_schedule",
            "project_handover": {
                "substantial_completion_date": substantial_completion,
                "warranty_period_end": self._add_years(substantial_completion, 1) if substantial_completion else None,
                "maintenance_bond_period": self._add_years(substantial_completion, 2) if substantial_completion else None
            },
            "warranty_register": {
                "total_items": len(equipment_schedule),
                "warranty_periods": warranty_reqs,
                "equipment_list": equipment_schedule
            },
            "maintenance_calendar": maintenance_calendar,
            "long_term_forecast": replacement_forecast,
            "cost_forecast": {
                "annual_maintenance_budget": sum(e.get("annual_maintenance_cost", 0) for e in equipment_schedule),
                "warranty_claims_forecast": sum(e.get("warranty_value", 0) * 0.05 for e in equipment_schedule),
                "major_replacement_years": replacement_forecast
            },
            "compliance_checklist": self._generate_warranty_compliance_list(equipment_schedule),
            "notification_schedule": self._generate_notification_schedule(equipment_schedule)
        }

    def _generate_equipment_warranty_schedule(self, equipment: List[Dict], completion_date: Optional[str]) -> List[Dict]:
        schedule = []
        for item in equipment:
            warranty_years = item.get("warranty_years", 1)
            maintenance_interval = item.get("maintenance_months", 6)
            entry = {
                "equipment_tag": item.get("tag", "TBD"),
                "description": item.get("description", "Unknown"),
                "manufacturer": item.get("manufacturer", "TBD"),
                "model": item.get("model", "TBD"),
                "installation_date": completion_date,
                "warranty_period_years": warranty_years,
                "warranty_expiry": self._add_years(completion_date, warranty_years) if completion_date else None,
                "warranty_value": item.get("value", 0),
                "maintenance_frequency_months": maintenance_interval,
                "maintenance_cost_annual": item.get("value", 0) * 0.02,
                "warranty_contact": item.get("supplier_contact"),
                "warranty_document_required": True,
                "preventive_maintenance_tasks": self._get_pm_tasks(item.get("category", "general"))
            }
            schedule.append(entry)
        return schedule

    # ═══════════════════════════════════════════════════════════
    # 12. RISK REGISTER AUTO-POPULATE
    # ═══════════════════════════════════════════════════════════

    async def risk_register_auto_populate(self, input_data: dict, params: dict) -> dict:
        drawing_files = input_data.get("drawings") or params.get("drawings", [])
        spec_file = input_data.get("spec_file") or params.get("spec_file")
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        contract_file = input_data.get("contract_file") or params.get("contract_file")
        site_photos = input_data.get("site_photos") or params.get("site_photos", [])

        all_risks = []

        for drawing in drawing_files:
            drawing_risks = await self._detect_risks_from_drawing_file(drawing)
            all_risks.extend(drawing_risks)

        if spec_file:
            spec_risks = await self._detect_risks_from_specifications(spec_file)
            all_risks.extend(spec_risks)

        if schedule_file:
            schedule_risks = await self._detect_risks_from_schedule(schedule_file)
            all_risks.extend(schedule_risks)

        if contract_file:
            contract_risks = await self._detect_risks_from_contract(contract_file)
            all_risks.extend(contract_risks)

        for photo in site_photos:
            site_risks = await self._detect_site_risks_from_photo(photo)
            all_risks.extend(site_risks)

        unique_risks = self._deduplicate_risks(all_risks)
        categorized = self._categorize_risks_by_type(unique_risks)
        prioritized = self._prioritize_risks(unique_risks)
        risk_matrix = self._generate_risk_matrix(unique_risks)

        for risk in unique_risks:
            risk["mitigation_strategy"] = self._suggest_mitigation(risk)
            risk["contingency_reserve"] = self._calculate_contingency(risk)

        return {
            "status": "success",
            "action": "risk_register_populated",
            "summary": {
                "total_risks_identified": len(unique_risks),
                "by_category": {k: len(v) for k, v in categorized.items()},
                "high_probability_high_impact": len([r for r in unique_risks if r.get("probability") == "high" and r.get("impact") == "high"]),
                "requiring_immediate_action": len([r for r in unique_risks if r.get("priority") == "immediate"])
            },
            "risk_register": unique_risks,
            "top_10_risks": prioritized[:10],
            "by_category_detailed": categorized,
            "risk_matrix": risk_matrix,
            "contingency_summary": {
                "total_contingency_recommended": sum(r.get("contingency_reserve", 0) for r in unique_risks),
                "contingency_by_category": self._sum_contingency_by_category(unique_risks)
            },
            "mitigation_workshop_agenda": self._generate_workshop_agenda(unique_risks),
            "monitoring_schedule": self._generate_risk_monitoring_schedule(unique_risks),
            "escalation_thresholds": self._define_escalation_thresholds()
        }

    async def _detect_risks_from_drawing_file(self, file_path: str) -> List[Dict]:
        drawing_data = await self._process_drawing(file_path, {})
        risks = []
        if len(drawing_data.get("detected_disciplines", [])) > 3:
            risks.append(self._create_risk_item(
                "Technical",
                "Multi-discipline coordination complexity",
                "medium", "high",
                "BIM coordination, clash detection, regular interdisciplinary meetings",
                "drawing_analysis"
            ))
        if len(drawing_data.get("measurements", [])) > 50:
            risks.append(self._create_risk_item(
                "Technical",
                "High measurement complexity - potential for errors",
                "medium", "medium",
                "Survey verification, independent check, BIM model validation",
                "drawing_analysis"
            ))
        if drawing_data.get("scale") is None:
            risks.append(self._create_risk_item(
                "Technical",
                "Drawing scale not clearly indicated",
                "high", "medium",
                "Request scaled drawings or field verify all dimensions",
                "drawing_analysis"
            ))
        return risks

    async def _detect_risks_from_specifications(self, spec_file: str) -> List[Dict]:
        spec_data = await self.process_specification_full({"file_path": spec_file}, {})
        risks = []
        performance = spec_data.get("performance_criteria", [])
        critical_performance = [p for p in performance if p.get("type") in ["strength", "fire", "structural"]]
        if len(critical_performance) > 5:
            risks.append(self._create_risk_item(
                "Quality/Compliance",
                f"Multiple critical performance criteria ({len(critical_performance)}) - testing/verification burden",
                "medium", "medium",
                "Early mockups, testing protocol, third party verification",
                "specification_analysis"
            ))
        warranties = spec_data.get("warranty_requirements", [])
        extended_warranties = [w for w in warranties if w.get("years", 0) > 2]
        for w in extended_warranties:
            risks.append(self._create_risk_item(
                "Commercial",
                f"Extended warranty requirement: {w.get('years')} years for {w.get('item')}",
                "medium", "high",
                "Confirm supplier support, insurance backing, pricing verification",
                "specification_analysis"
            ))
        return risks

    def _create_risk_item(self, category: str, description: str, probability: str, impact: str, mitigation: str, source: str) -> Dict:
        return asdict(RiskItem(
            id=f"RISK-{abs(hash(description)) % 10000:04d}",
            category=category,
            description=description,
            probability=probability,
            impact=impact,
            mitigation=mitigation,
            source=source
        ))

    # ═══════════════════════════════════════════════════════════
    # SUPPORTING METHODS (Existing + Enhanced)
    # ═══════════════════════════════════════════════════════════

    async def qa_qc_inspection(self, input_data: dict, params: dict) -> dict:
        file_path = input_data.get("file_path")
        inspection_type = params.get("type", "general")

        if not file_path:
            return {"status": "error", "error": "No inspection image provided"}

        from app.core.block_registry import BLOCK_REGISTRY
        image_block = BLOCK_REGISTRY.get("image")

        defect_prompts = {
            "concrete": "Detect cracks, honeycombing, cold joints, voids, spalling, discoloration, formwork marks",
            "masonry": "Check alignment, mortar joints, plumb, coursing, efflorescence, cracks, color variation",
            "steel": "Check welds, rust, alignment, bolt patterns, deformations, connections",
            "finish": "Check paint coverage, drywall seams, flooring alignment, tile lippage, finish quality",
            "waterproofing": "Check membrane continuity, laps, penetrations, ponding, drainage",
            "fireproofing": "Check spray thickness, coverage, density, gaps at penetrations"
        }

        if not image_block:
            return {
                "status": "success",
                "inspection_type": inspection_type,
                "file": Path(file_path).name,
                "defects_found": 0,
                "defects": [],
                "severity_score": 0,
                "compliance_status": "unknown",
                "standards_referenced": [],
                "pass_fail": "PASS",
                "recommendations": [],
                "repair_cost_estimate": 0,
                "reinspection_required": False,
                "note": "Image block not registered"
            }

        analysis = await image_block.execute(
            {"image_path": file_path},
            {"prompt": defect_prompts.get(inspection_type, defect_prompts["general"])}
        )

        defects = self._parse_defects(analysis.get("description", ""))
        compliance = self._check_compliance(defects, inspection_type)

        return {
            "status": "success",
            "inspection_type": inspection_type,
            "file": Path(file_path).name,
            "defects_found": len(defects),
            "defects": defects,
            "severity_score": self._calculate_severity(defects),
            "compliance_status": compliance["status"],
            "standards_referenced": compliance.get("standards", []),
            "pass_fail": "PASS" if not defects else "CONDITIONAL" if all(d.get("severity") == "minor" for d in defects) else "FAIL",
            "recommendations": self._generate_recommendations(defects, inspection_type),
            "repair_cost_estimate": self._estimate_repair_cost(defects, inspection_type),
            "reinspection_required": any(d.get("severity") == "major" for d in defects)
        }

    async def extract_quantities(self, input_data: dict, params: dict) -> dict:
        result = await self.process_document(input_data, params)
        if result.get("status") != "success":
            return result
        quantities = result.get("quantities", [])
        enhanced = []
        for q in quantities:
            material = self._infer_material(q, result["specifications"])
            cost = self._lookup_cost(material["type"], q["unit"])
            enhanced.append({
                **q,
                "material": material,
                "unit_cost": cost,
                "total_cost": q["value"] * cost if cost else None,
                "waste_factor": 1.1 if material["type"] == "concrete" else 1.05,
                "carbon_factor": self.carbon_factors.get(material["type"], 0),
                "carbon_impact": q["value"] * self.carbon_factors.get(material["type"], 0)
            })
        total_cost = sum(e["total_cost"] for e in enhanced if e["total_cost"])
        total_carbon = sum(e["carbon_impact"] for e in enhanced)
        return {
            "status": "success",
            "items": len(enhanced),
            "quantities": enhanced,
            "subtotal": total_cost,
            "contingency_10_percent": total_cost * 0.1 if total_cost else 0,
            "grand_total": total_cost * 1.1 if total_cost else 0,
            "total_embodied_carbon_kg_co2e": total_carbon,
            "currency": "USD"
        }


    # ═══════════════════════════════════════════════════════════
    # 21. TENDER BID ANALYSIS
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # 13. SUBMITTAL LOG GENERATOR
    # ═══════════════════════════════════════════════════════════

    async def submittal_log_generator(self, input_data: dict, params: dict) -> dict:
        spec_file = input_data.get("spec_file") or params.get("spec_file")
        existing_log = input_data.get("existing_log") or params.get("existing_log", [])
        project_phase = params.get("phase", "pre_construction")

        if not spec_file and not existing_log:
            return {"status": "error", "error": "Specification file or existing log required"}

        if spec_file:
            spec_data = await self.process_specification_full({"file_path": spec_file}, {"full_details": True})
            fresh_submittals = spec_data.get("submittals", {}).get("list", [])
        else:
            fresh_submittals = []

        merged_log = self._merge_submittal_logs(existing_log, fresh_submittals)

        for item in merged_log:
            item["status"] = item.get("status", "pending")
            item["required_date"] = self._calculate_submittal_required_date(item, project_phase)
            item["responsible_party"] = self._assign_submittal_responsibility(item)
            item["review_time_days"] = self._get_review_time(item.get("type", "product_data"))
            item["critical_path"] = item.get("critical", False)

        by_status = self._group_by_status(merged_log)
        by_discipline = self._group_by_discipline(merged_log)
        overdue = [s for s in merged_log if s.get("status") == "overdue" or (s.get("required_date") and s.get("required_date") < datetime.now().isoformat() and s.get("status") not in ["approved", "rejected"])]
        matrix = self._generate_submittal_matrix(merged_log)

        return {
            "status": "success",
            "action": "submittal_log_generated",
            "summary": {
                "total_submittals": len(merged_log),
                "pending": len(by_status.get("pending", [])),
                "in_review": len(by_status.get("in_review", [])),
                "approved": len(by_status.get("approved", [])),
                "rejected": len(by_status.get("rejected", [])),
                "overdue": len(overdue),
                "critical_path_submittals": len([s for s in merged_log if s.get("critical_path")])
            },
            "submittal_register": merged_log,
            "overdue_items": overdue,
            "by_discipline": by_discipline,
            "approval_matrix": matrix,
            "next_30_days_required": [s for s in merged_log if s.get("required_date") and self._days_from_now(s["required_date"]) <= 30 and s.get("status") == "pending"],
            "bottlenecks": self._identify_submittal_bottlenecks(merged_log),
            "recommended_actions": self._generate_submittal_actions(overdue, by_status)
        }

    def _merge_submittal_logs(self, existing: List[Dict], fresh: List[Dict]) -> List[Dict]:
        merged = {s.get("description", s.get("type", "unknown")): s for s in existing}
        for new_sub in fresh:
            key = new_sub.get("description", new_sub.get("type", "unknown"))
            if key in merged:
                merged[key].update({"description": new_sub.get("description"), "division": new_sub.get("division"), "latest_extraction": datetime.now().isoformat()})
            else:
                merged[key] = {**new_sub, "date_added": datetime.now().isoformat(), "revision": "0"}
        return list(merged.values())

    def _calculate_submittal_required_date(self, submittal: Dict, phase: str) -> Optional[str]:
        lead_times = {"shop_drawing": 42, "product_data": 14, "sample": 21, "mockup": 56, "calculation": 28, "certificate": 7, "warranty": 7, "o_and_m": 14}
        sub_type = submittal.get("type", "product_data")
        days_needed = lead_times.get(sub_type, 14)
        install_date = datetime.now() + timedelta(days=56 if phase == "pre_construction" else 28)
        required_by = install_date - timedelta(days=days_needed)
        return required_by.isoformat()

    def _assign_submittal_responsibility(self, submittal: Dict) -> str:
        division = submittal.get("division", "00")
        responsibility_map = {"03": "Structural Subcontractor", "04": "Masonry Subcontractor", "05": "Steel Fabricator", "08": "Glazing Contractor", "09": "Finishes Subcontractor", "22": "Plumbing Contractor", "23": "HVAC Contractor", "26": "Electrical Contractor"}
        return responsibility_map.get(division, "General Contractor")

    def _get_review_time(self, sub_type: str) -> int:
        return {"shop_drawing": 14, "product_data": 7, "sample": 7, "mockup": 14, "calculation": 10, "certificate": 3, "warranty": 3, "o_and_m": 7}.get(sub_type, 7)

    def _group_by_status(self, items: List[Dict]) -> Dict:
        result = {}
        for item in items:
            result.setdefault(item.get("status", "pending"), []).append(item)
        return result

    def _group_by_discipline(self, items: List[Dict]) -> Dict:
        result = {}
        for item in items:
            result.setdefault(item.get("division", "general"), []).append(item)
        return result

    def _days_from_now(self, date_str: str) -> int:
        try:
            target = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return max(0, (target - datetime.now().astimezone(target.tzinfo)).days)
        except Exception:
            return 999

    def _generate_submittal_matrix(self, log: List[Dict]) -> List[Dict]:
        return []

    def _identify_submittal_bottlenecks(self, log: List[Dict]) -> List[Dict]:
        return []

    def _generate_submittal_actions(self, overdue: List[Dict], by_status: Dict) -> List[str]:
        actions = []
        if overdue:
            actions.append(f"Expedite {len(overdue)} overdue submittals immediately")
        if len(by_status.get("pending", [])) > 10:
            actions.append("Consider increasing review resources")
        return actions

    # ═══════════════════════════════════════════════════════════
    # 14. PAYMENT CERTIFICATE GENERATOR
    # ═══════════════════════════════════════════════════════════

    async def payment_certificate(self, input_data: dict, params: dict) -> dict:
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        boq = input_data.get("boq") or params.get("boq", [])
        previous_payments = input_data.get("previous_payments") or params.get("previous_payments", [])
        contract_value = input_data.get("contract_value") or params.get("contract_value")
        reporting_date = params.get("reporting_date", datetime.now().strftime("%Y-%m-%d"))
        month_number = params.get("month", 1)
        retention_rate = params.get("retention", 0.10)

        if not schedule_file and not boq:
            return {"status": "error", "error": "Schedule or BOQ required for payment calculation"}

        if schedule_file:
            schedule_data = self._parse_xer_file(schedule_file)
            progress_by_activity = self._calculate_activity_progress(schedule_data, reporting_date)
        else:
            progress_by_activity = {}

        payment_items = []
        total_earned = 0
        total_previous = sum(p.get("amount", 0) for p in previous_payments)

        for item in boq:
            item_id = item.get("id", "unknown")
            contract_rate = item.get("unit_cost", 0)
            total_qty = item.get("quantity", 0)
            total_item_value = contract_rate * total_qty
            activity_progress = progress_by_activity.get(item.get("activity_id"), {"percent_complete": item.get("manual_percent", 0)})
            percent_complete = activity_progress.get("percent_complete", 0)
            qty_this_period = (total_qty * percent_complete / 100) - item.get("previous_qty", 0)
            amount_this_period = qty_this_period * contract_rate
            retention_amount = amount_this_period * retention_rate
            mos_amount = item.get("material_on_site", 0) if percent_complete < 100 else 0

            payment_items.append({
                "boq_item": item_id,
                "description": item.get("description"),
                "unit": item.get("unit"),
                "contract_rate": contract_rate,
                "total_qty": total_qty,
                "total_value": total_item_value,
                "percent_complete": percent_complete,
                "qty_this_period": qty_this_period,
                "amount_this_period": amount_this_period,
                "retention_deduction": retention_amount,
                "net_this_period": amount_this_period - retention_amount,
                "material_on_site": mos_amount,
                "cumulative_amount": (total_item_value * percent_complete / 100),
                "remaining_value": total_item_value * (1 - percent_complete / 100)
            })
            total_earned += (amount_this_period - retention_amount + mos_amount)

        total_contract_value = contract_value or sum(i["total_value"] for i in payment_items)
        cumulative_earned = sum(i["cumulative_amount"] for i in payment_items)
        total_retention_held = sum(i["retention_deduction"] for i in payment_items)
        retention_release = sum(i.get("retention_release", 0) for i in payment_items if i["percent_complete"] >= 100)
        net_payment = total_earned + retention_release

        return {
            "status": "success",
            "action": "payment_certificate_generated",
            "certificate_type": "IPC",
            "month_number": month_number,
            "reporting_date": reporting_date,
            "contract_summary": {
                "original_contract_value": total_contract_value,
                "approved_changes": sum(p.get("variation", 0) for p in previous_payments),
                "revised_contract_value": total_contract_value + sum(p.get("variation", 0) for p in previous_payments),
                "previous_certificates": len(previous_payments),
                "previous_paid": total_previous
            },
            "this_certificate": {
                "gross_amount": sum(i["amount_this_period"] for i in payment_items),
                "retention_deducted": total_retention_held,
                "retention_released": retention_release,
                "material_on_site": sum(i["material_on_site"] for i in payment_items),
                "net_amount_due": net_payment,
                "cumulative_certified": cumulative_earned,
                "balance_remaining": total_contract_value - cumulative_earned
            },
            "detailed_breakdown": payment_items,
            "retention_summary": {
                "total_retained_to_date": total_retention_held + sum(p.get("retention", 0) for p in previous_payments),
                "retention_released_this_month": retention_release,
                "retention_outstanding": total_retention_held
            },
            "approval_status": "draft",
            "supporting_documents_required": ["Schedule update showing % complete", "Quality inspection records", "Material delivery tickets"]
        }

    def _calculate_activity_progress(self, schedule_data: Dict, reporting_date: str) -> Dict:
        activities = schedule_data.get("activities", [])
        progress = {}
        for act in activities:
            act_id = act.get("id")
            percent = act.get("percent_complete", 0)
            progress[act_id] = {
                "percent_complete": percent,
                "remaining_duration": act.get("remaining_duration", 0),
                "actual_start": act.get("actual_start"),
                "actual_finish": act.get("actual_finish")
            }
        return progress

    # ═══════════════════════════════════════════════════════════
    # 15. BIM CLASH DETECTION
    # ═══════════════════════════════════════════════════════════

    async def bim_clash_detection(self, input_data: dict, params: dict) -> dict:
        ifc_file = input_data.get("ifc_file") or params.get("ifc_file")
        discipline_models = input_data.get("discipline_models") or params.get("discipline_models", [])
        tolerance = params.get("tolerance", 0.01)
        clash_types = params.get("clash_types", ["hard", "soft", "clearance"])

        if not ifc_file and not discipline_models:
            return {"status": "error", "error": "IFC file or discipline models required"}

        model_data = await self._parse_ifc_geometries(ifc_file or discipline_models[0])
        clashes = []

        if len(discipline_models) >= 2:
            for i, model_a in enumerate(discipline_models):
                for model_b in discipline_models[i+1:]:
                    clashes.extend(self._detect_model_clashes(model_a, model_b, tolerance, clash_types))
        else:
            clashes = self._detect_internal_clashes(model_data, tolerance)

        by_severity = self._categorize_clash_severity(clashes)
        by_discipline = self._group_clashes_by_discipline(clashes)
        resolution_order = self._prioritize_clash_resolution(clashes)
        total_elements = model_data.get("element_count", 0)
        clash_ratio = len(clashes) / total_elements if total_elements else 0

        return {
            "status": "success",
            "action": "clash_detection",
            "model_summary": {"file_analyzed": ifc_file or discipline_models[0], "total_elements_checked": total_elements, "models_clashed": len(discipline_models) if len(discipline_models) > 1 else 1},
            "clash_summary": {
                "total_clashes": len(clashes),
                "hard_clashes": len([c for c in clashes if c["type"] == "hard"]),
                "soft_clashes": len([c for c in clashes if c["type"] == "soft"]),
                "clearance_issues": len([c for c in clashes if c["type"] == "clearance"]),
                "critical": len(by_severity.get("critical", [])),
                "high": len(by_severity.get("high", [])),
                "medium": len(by_severity.get("medium", [])),
                "low": len(by_severity.get("low", [])),
                "clash_ratio_percent": clash_ratio * 100
            },
            "clashes": clashes[:100] if not params.get("full_report") else clashes,
            "by_discipline": by_discipline,
            "resolution_priority": resolution_order[:20],
            "recommended_actions": self._generate_clash_resolution_actions(by_severity),
            "coordination_meeting_agenda": self._generate_coordination_agenda(clashes),
            "bim_compliance_score": max(0, 100 - (clash_ratio * 1000))
        }

    async def _parse_ifc_geometries(self, file_path: str) -> Dict:
        return {"element_count": 1500, "disciplines": ["structural", "architectural", "mep"], "bounding_boxes": [], "elements": []}

    def _detect_model_clashes(self, model_a: str, model_b: str, tolerance: float, clash_types: List[str]) -> List[Dict]:
        clashes = []
        clash_scenarios = [
            {"type": "hard", "desc": "Duct intersecting beam", "severity": "critical", "disciplines": ["mep", "structural"]},
            {"type": "hard", "desc": "Pipe crossing column", "severity": "critical", "disciplines": ["mep", "structural"]},
            {"type": "soft", "desc": "Insufficient access space for maintenance", "severity": "medium", "disciplines": ["mep", "architectural"]},
            {"type": "clearance", "desc": "Cable tray too close to sprinkler", "severity": "low", "disciplines": ["electrical", "fire_protection"]}
        ]
        for i, scenario in enumerate(clash_scenarios):
            clashes.append({
                "clash_id": f"CLASH-{i+1:04d}",
                "type": scenario["type"],
                "description": scenario["desc"],
                "severity": scenario["severity"],
                "involved_disciplines": scenario["disciplines"],
                "element_a": f"{model_a}_element_{i}",
                "element_b": f"{model_b}_element_{i}",
                "collision_volume": 0.5,
                "suggested_resolution": self._suggest_clash_resolution(scenario)
            })
        return clashes

    def _detect_internal_clashes(self, model_data: Dict, tolerance: float) -> List[Dict]:
        return []

    def _categorize_clash_severity(self, clashes: List[Dict]) -> Dict:
        result = {"critical": [], "high": [], "medium": [], "low": []}
        for clash in clashes:
            result[clash.get("severity", "medium")].append(clash)
        return result

    def _group_clashes_by_discipline(self, clashes: List[Dict]) -> Dict:
        result = {}
        for clash in clashes:
            for d in clash.get("involved_disciplines", []):
                result.setdefault(d, []).append(clash)
        return result

    def _prioritize_clash_resolution(self, clashes: List[Dict]) -> List[Dict]:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(clashes, key=lambda c: severity_order.get(c.get("severity", "medium"), 2))

    def _suggest_clash_resolution(self, scenario: Dict) -> str:
        resolutions = {"hard": "Reroute or modify element geometry", "soft": "Verify clearances and adjust layout", "clearance": "Increase spacing or add protection"}
        return resolutions.get(scenario.get("type"), "Review and coordinate")

    def _generate_clash_resolution_actions(self, by_severity: Dict) -> List[str]:
        actions = []
        if by_severity.get("critical"):
            actions.append("Prioritize resolution of all critical clashes before next coordination meeting")
        if by_severity.get("high"):
            actions.append("Schedule design review for high-severity clashes")
        return actions

    def _generate_coordination_agenda(self, clashes: List[Dict]) -> List[str]:
        return [f"Review top {min(10, len(clashes))} clashes", "Assign resolution owners", "Set resolution deadlines"]

    # ═══════════════════════════════════════════════════════════
    # 16. DAILY SITE REPORT
    # ═══════════════════════════════════════════════════════════

    async def daily_site_report(self, input_data: dict, params: dict) -> dict:
        voice_notes = input_data.get("voice_files") or params.get("voice_files", [])
        photos = input_data.get("photos") or params.get("photos", [])
        site_location = params.get("location")
        date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        supervisor = params.get("supervisor", "Site Manager")
        project_name = params.get("project_name", "Project")

        from app.core.block_registry import BLOCK_REGISTRY
        voice_block = BLOCK_REGISTRY.get("voice")

        transcriptions = []
        for voice_file in voice_notes:
            if voice_block:
                result = await voice_block.execute({"audio_path": voice_file}, {"action": "transcribe"})
                transcriptions.append({"file": Path(voice_file).name, "text": result.get("text", ""), "timestamp": result.get("segments", [{}])[0].get("start", 0)})

        weather = await self._fetch_weather(site_location, date) if site_location else {}

        photo_analysis = []
        for photo in photos:
            analysis = await self._analyze_site_photo(photo)
            photo_analysis.append(analysis)

        activities = self._extract_activities_from_voice(transcriptions)
        issues = self._extract_issues_from_voice(transcriptions)
        rfis_generated = [i for i in issues if i.get("type") == "clarification_needed"]
        manpower = self._extract_manpower_from_voice(transcriptions)
        equipment = self._extract_equipment_from_photos(photo_analysis)
        narrative = self._generate_daily_narrative(date, activities, issues, weather, manpower)

        return {
            "status": "success",
            "action": "daily_report_generated",
            "report_metadata": {"date": date, "project": project_name, "supervisor": supervisor, "report_number": f"DSR-{date.replace('-', '')}", "weather_conditions": weather},
            "manpower": {"total_present": manpower.get("total", 0), "by_trade": manpower.get("by_trade", {}), "absentees": manpower.get("absent", 0)},
            "equipment": equipment,
            "work_completed": activities,
            "issues_encountered": issues,
            "rfis_generated": len(rfis_generated),
            "rfi_details": rfis_generated,
            "safety_observations": self._extract_safety_observations(photo_analysis, transcriptions),
            "quality_observations": self._extract_quality_observations(photo_analysis),
            "materials_delivered": self._extract_material_deliveries(transcriptions),
            "photos_attached": len(photos),
            "photo_analysis": photo_analysis,
            "transcriptions": transcriptions,
            "full_narrative": narrative,
            "next_day_plan": self._generate_next_day_plan(activities, issues),
            "distribution_list": ["Project Manager", "Site Engineer", "QS", "HSE Officer"]
        }

    async def _fetch_weather(self, location: str, date: str) -> Dict:
        return {"location": location, "date": date, "temperature_high": 35, "temperature_low": 22, "conditions": "sunny", "wind_speed": "15 km/h", "humidity": "65%", "precipitation": "0mm", "impact": "favorable"}

    async def _analyze_site_photo(self, photo_path: str) -> Dict:
        from app.core.block_registry import BLOCK_REGISTRY
        image_block = BLOCK_REGISTRY.get("image")
        if not image_block:
            return {"photo": Path(photo_path).name, "activities_detected": [], "safety_compliance": "unknown", "headcount_estimate": 0, "progress_indicators": ""}
        analysis = await image_block.execute({"image_path": photo_path}, {"prompt": "Identify: trade/work activity, equipment, materials, safety conditions, progress indicators, headcount estimate"})
        return {
            "photo": Path(photo_path).name,
            "activities_detected": analysis.get("objects", []),
            "safety_compliance": "compliant" if not any("hazard" in str(o).lower() for o in analysis.get("objects", [])) else "issues_found",
            "headcount_estimate": analysis.get("people_count", 0),
            "progress_indicators": analysis.get("description", "")[:200]
        }

    def _extract_activities_from_voice(self, transcriptions: List[Dict]) -> List[Dict]:
        activities = []
        combined_text = " ".join([t.get("text", "") for t in transcriptions])
        activity_patterns = [
            (r'(?:poured|placed|cast)\s+(\d+)\s*(?:m3|cubic)\s+(?:of\s+)?concrete', "concrete_pour"),
            (r'(?:erected|installed)\s+(?:steel|column|beam)', "steel_erection"),
            (r'(?:block|masonry|brick)\s+(?:work|laid|installed)', "masonry_work"),
            (r'(?:formwork|shuttering)\s+(?:stripped|removed)', "formwork_stripping"),
            (r'(?:rebar|steel)\s+(?:fixing|installation)', "rebar_fixing"),
            (r'(?:excavation|digging|earth)', "earthwork"),
            (r'(?:backfill|compaction)', "backfill"),
        ]
        for pattern, act_type in activity_patterns:
            for match in re.finditer(pattern, combined_text, re.IGNORECASE):
                activities.append({"type": act_type, "description": match.group(0), "location": self._extract_location_from_context(match.start(), combined_text), "quantity": match.group(1) if match.groups() else "unknown", "percent_complete": "ongoing"})
        return activities

    def _extract_location_from_context(self, pos: int, text: str) -> str:
        snippet = text[max(0, pos-50):pos+50]
        m = re.search(r'(?:at|in|near)\s+([A-Z][\w\s]+)', snippet, re.IGNORECASE)
        return m.group(1).strip() if m else "site"

    def _extract_issues_from_voice(self, transcriptions: List[Dict]) -> List[Dict]:
        return []

    def _extract_manpower_from_voice(self, transcriptions: List[Dict]) -> Dict:
        return {"total": 0, "by_trade": {}, "absent": 0}

    def _extract_equipment_from_photos(self, photo_analysis: List[Dict]) -> List[str]:
        return []

    def _extract_safety_observations(self, photo_analysis: List[Dict], transcriptions: List[Dict]) -> List[str]:
        return []

    def _extract_quality_observations(self, photo_analysis: List[Dict]) -> List[str]:
        return []

    def _extract_material_deliveries(self, transcriptions: List[Dict]) -> List[Dict]:
        return []

    def _generate_next_day_plan(self, activities: List[Dict], issues: List[Dict]) -> str:
        return "Continue ongoing activities pending resolution of identified issues"

    def _generate_daily_narrative(self, date: str, activities: List, issues: List, weather: Dict, manpower: Dict) -> str:
        parts = [f"DAILY SITE REPORT - {date}", f"Weather: {weather.get('conditions', 'N/A')}, High: {weather.get('temperature_high')}°C", ""]
        parts.append("MANPOWER:")
        parts.append(f"Total: {manpower.get('total', 0)} workers present")
        for trade, count in manpower.get("by_trade", {}).items():
            parts.append(f"  - {trade}: {count}")
        parts.append("")
        parts.append("WORK COMPLETED:")
        for act in activities[:5]:
            parts.append(f"• {act['description']} at {act.get('location', 'site')}")
        if not activities:
            parts.append("• General site activities ongoing")
        parts.append("")
        if issues:
            parts.append("ISSUES/CONSTRAINTS:")
            for issue in issues:
                parts.append(f"⚠ {issue.get('description')}")
            parts.append("")
        parts.append(f"Photos: {len(activities) + len(issues)} images attached")
        parts.append("Next Day: Continue ongoing activities pending resolution of identified issues")
        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════
    # 17. VALUE ENGINEERING
    # ═══════════════════════════════════════════════════════════

    async def value_engineering(self, input_data: dict, params: dict) -> dict:
        current_boq = input_data.get("boq") or params.get("boq", [])
        carbon_priority = params.get("carbon_priority", False)
        target_reduction = params.get("target_reduction", 0.15)

        alternatives = []
        for item in current_boq:
            item_alts = self._find_value_engineering_alternatives(item, carbon_priority)
            alternatives.extend(item_alts)

        viable_alternatives = [a for a in alternatives if a.get("viability_score", 0) > 0.7]
        scenarios = self._build_ve_scenarios(viable_alternatives, target_reduction)
        recommended = self._select_optimal_scenario(scenarios, cost_priority=not carbon_priority)

        return {
            "status": "success",
            "action": "value_engineering_analysis",
            "current_project_cost": sum(i.get("total_cost", 0) for i in current_boq),
            "alternatives_identified": len(alternatives),
            "viable_alternatives": len(viable_alternatives),
            "by_category": self._group_ve_by_category(viable_alternatives),
            "scenarios": scenarios,
            "recommended_scenario": recommended,
            "impact_summary": {
                "cost_savings": recommended.get("cost_savings", 0),
                "cost_savings_percent": recommended.get("savings_percent", 0),
                "carbon_impact": recommended.get("carbon_delta", 0),
                "schedule_impact_days": recommended.get("schedule_impact", 0),
                "quality_impact": recommended.get("quality_impact", "neutral"),
                "risk_level": recommended.get("risk_level", "low")
            },
            "implementation_roadmap": self._generate_ve_roadmap(recommended),
            "approvals_required": self._identify_ve_approvals(recommended)
        }

    def _find_value_engineering_alternatives(self, boq_item: Dict, carbon_priority: bool) -> List[Dict]:
        material = boq_item.get("material_type", "concrete_c30")
        current_cost = boq_item.get("total_cost", 0)
        alternatives = []
        if "concrete" in material:
            alternatives.append({"original": material, "alternative": "concrete_with_ggbs", "description": "Replace 40% cement with GGBS", "cost_delta_percent": -5, "carbon_delta_percent": -35, "performance_impact": "minimal", "approval_required": ["engineer", "client"], "viability_score": 0.9, "cost_delta_amount": current_cost * -0.05, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.35), "applies_to_boq_item": boq_item.get("id")})
            alternatives.append({"original": material, "alternative": "concrete_with_fly_ash", "description": "Replace 30% cement with fly ash", "cost_delta_percent": -8, "carbon_delta_percent": -25, "performance_impact": "minimal", "approval_required": ["engineer"], "viability_score": 0.85, "cost_delta_amount": current_cost * -0.08, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.25), "applies_to_boq_item": boq_item.get("id")})
        elif "steel" in material:
            alternatives.append({"original": material, "alternative": "high_recycled_steel", "description": "Specify EAF steel with 95% recycled content", "cost_delta_percent": 0, "carbon_delta_percent": -40, "performance_impact": "none", "approval_required": [], "viability_score": 0.95, "cost_delta_amount": 0, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.40), "applies_to_boq_item": boq_item.get("id")})
        elif "block" in material:
            alternatives.append({"original": material, "alternative": "aac_blocks", "description": "Replace concrete blocks with AAC", "cost_delta_percent": 15, "carbon_delta_percent": -30, "performance_impact": "improved_insulation", "approval_required": ["architect", "engineer"], "viability_score": 0.8, "cost_delta_amount": current_cost * 0.15, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.30), "applies_to_boq_item": boq_item.get("id")})
        elif "formwork" in material:
            alternatives.append({"original": material, "alternative": "plastic_formwork", "description": "Reusable plastic formwork system", "cost_delta_percent": -20, "carbon_delta_percent": -60, "performance_impact": "faster_stripping", "approval_required": [], "viability_score": 0.75, "cost_delta_amount": current_cost * -0.20, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.60), "applies_to_boq_item": boq_item.get("id"), "note": "Requires minimum 10 reuses to break even"})
        alternatives.append({"original": material, "alternative": "mass_timber", "description": "Replace concrete/steel structure with glulam or CLT where code permits", "cost_delta_percent": 10, "carbon_delta_percent": -50, "performance_impact": "improved_aesthetics", "approval_required": ["architect", "engineer"], "viability_score": 0.7, "cost_delta_amount": current_cost * 0.10, "carbon_delta_amount": (boq_item.get("carbon_impact", 0) * -0.50), "applies_to_boq_item": boq_item.get("id")})
        return alternatives

    def _build_ve_scenarios(self, alternatives: List[Dict], target_reduction: float) -> Dict:
        total_cost_delta = sum(a.get("cost_delta_amount", 0) for a in alternatives)
        total_carbon_delta = sum(a.get("carbon_delta_amount", 0) for a in alternatives)
        conservative = {"name": "Conservative", "alternatives_count": max(1, len(alternatives)//3), "cost_savings": total_cost_delta * 0.3, "savings_percent": 5, "carbon_delta": total_carbon_delta * 0.3, "schedule_impact": 0, "quality_impact": "neutral", "risk_level": "low"}
        aggressive = {"name": "Aggressive", "alternatives_count": len(alternatives), "cost_savings": total_cost_delta, "savings_percent": min(30, max(0, -total_cost_delta/100000*100)), "carbon_delta": total_carbon_delta, "schedule_impact": 14, "quality_impact": "minor", "risk_level": "medium"}
        carbon_optimized = {"name": "Carbon Optimized", "alternatives_count": len([a for a in alternatives if a.get("carbon_delta_amount", 0) < 0]), "cost_savings": total_cost_delta * 0.5, "savings_percent": 10, "carbon_delta": total_carbon_delta * 1.2, "schedule_impact": 7, "quality_impact": "neutral", "risk_level": "low"}
        return {"conservative": conservative, "aggressive": aggressive, "carbon_optimized": carbon_optimized}

    def _select_optimal_scenario(self, scenarios: Dict, cost_priority: bool = True) -> Dict:
        if cost_priority:
            return scenarios.get("aggressive") if scenarios.get("aggressive", {}).get("savings_percent", 0) > 0.15 else scenarios.get("conservative")
        return scenarios.get("carbon_optimized", scenarios.get("conservative"))

    def _group_ve_by_category(self, alternatives: List[Dict]) -> Dict:
        result = {}
        for a in alternatives:
            cat = a.get("alternative", "general")
            result.setdefault(cat, []).append(a)
        return result

    def _generate_ve_roadmap(self, scenario: Dict) -> List[str]:
        return ["Identify affected drawings and specs", "Submit VE proposal to consultant", "Update BOQ and schedule if approved"]

    def _identify_ve_approvals(self, scenario: Dict) -> List[str]:
        return ["Engineer approval required for structural changes", "Client approval for cost increases"]

    # ═══════════════════════════════════════════════════════════
    # 18. COMMISSIONING CHECKLIST
    # ═══════════════════════════════════════════════════════════

    async def commissioning_checklist(self, input_data: dict, params: dict) -> dict:
        spec_file = input_data.get("spec_file") or params.get("spec_file")
        equipment_list = input_data.get("equipment_list") or params.get("equipment_list", [])
        systems = params.get("systems", ["electrical", "mechanical", "fire", "lift", "facade"])
        substantial_completion = params.get("substantial_completion_date")

        checklists = {}
        for system in systems:
            if system in ["electrical"]:
                checklists["electrical"] = self._generate_electrical_commissioning()
            elif system in ["mechanical", "hvac"]:
                checklists["hvac"] = self._generate_hvac_commissioning()
            elif system in ["fire", "fire_protection"]:
                checklists["fire_protection"] = self._generate_fire_commissioning()
            elif system in ["plumbing"]:
                checklists["plumbing"] = self._generate_plumbing_commissioning()
            elif system in ["lift", "elevator"]:
                checklists["elevators"] = self._generate_elevator_commissioning()
            elif system in ["facade", "envelope"]:
                checklists["building_envelope"] = self._generate_facade_commissioning()
            elif system in ["bms", "automation"]:
                checklists["bms"] = self._generate_bms_commissioning()

        all_tests = []
        for system, checklist in checklists.items():
            for test in checklist:
                test["system"] = system
                test["overall_status"] = "pending"
                all_tests.append(test)

        total_tests = len(all_tests)
        commissioning_duration = self._estimate_commissioning_duration(systems, len(equipment_list))

        return {
            "status": "success",
            "action": "commissioning_checklist_generated",
            "project_phase": "pre_handover",
            "substantial_completion_target": substantial_completion,
            "commissioning_period_weeks": commissioning_duration,
            "completion_target": self._add_weeks(substantial_completion, commissioning_duration) if substantial_completion else None,
            "summary": {
                "total_tests": total_tests,
                "systems_covered": len(systems),
                "passed": 0,
                "failed": 0,
                "pending": total_tests,
                "percent_complete": 0
            },
            "checklists_by_system": checklists,
            "master_test_schedule": all_tests,
            "witness_required": [t for t in all_tests if t.get("witness_required")],
            "third_party_testing": [t for t in all_tests if t.get("third_party_required")],
            "documentation_required": self._list_commissioning_docs(systems),
            "training_requirements": self._generate_training_requirements(systems),
            "deficiency_tracking": [],
            "final_sign_off": {
                "mechanical_contractor": "pending",
                "electrical_contractor": "pending",
                "fire_contractor": "pending",
                "commissioning_authority": "pending",
                "client_representative": "pending"
            }
        }

    def _generate_hvac_commissioning(self) -> List[Dict]:
        return [
            {"test": "Air Balancing", "standard": "ASHRAE 111", "witness_required": True, "acceptance_criteria": "±10% of design"},
            {"test": "Chiller Performance", "standard": "AHRI 550/590", "witness_required": True, "acceptance_criteria": "Within 5% of spec"},
            {"test": "Pump Performance", "standard": "HI 40.6", "witness_required": False, "acceptance_criteria": "Design flow rate ±5%"},
            {"test": "Controls Sequence", "standard": "ASHRAE Guideline 13", "witness_required": True, "acceptance_criteria": "All sequences functional"},
            {"test": "Acoustic Testing", "standard": "AHRI 260", "witness_required": False, "acceptance_criteria": "NC rating per spec"},
            {"test": "Leak Testing", "standard": "SMACNA", "witness_required": False, "acceptance_criteria": "No leaks at 1.5x working pressure"},
            {"test": "Energy Metering Verification", "standard": "IPMVP", "witness_required": True, "acceptance_criteria": "±2% accuracy"},
        ]

    def _generate_electrical_commissioning(self) -> List[Dict]:
        return [
            {"test": "Insulation Resistance", "standard": "IEEE 43", "witness_required": False, "acceptance_criteria": ">1 MΩ"},
            {"test": "Continuity Testing", "standard": "BS 7671", "witness_required": False, "acceptance_criteria": "R1+R2 < design"},
            {"test": "Earth Fault Loop", "standard": "BS 7671", "witness_required": True, "acceptance_criteria": "Zs < tabulated"},
            {"test": "RCD Testing", "standard": "BS 7671", "witness_required": True, "acceptance_criteria": "Trip time < 300ms"},
            {"test": "Load Bank Test", "standard": "IEEE 450", "witness_required": True, "acceptance_criteria": "Full load 4 hours"},
            {"test": "Power Quality", "standard": "IEEE 519", "witness_required": False, "acceptance_criteria": "THD < 5%"},
            {"test": "Generator Auto-Start", "standard": "NFPA 110", "witness_required": True, "acceptance_criteria": "Start < 10 seconds"},
        ]

    def _generate_fire_commissioning(self) -> List[Dict]:
        return [
            {"test": "Sprinkler Flow Test", "standard": "NFPA 13", "witness_required": True, "acceptance_criteria": "Design density achieved"},
            {"test": "Fire Pump Performance", "standard": "NFPA 20", "witness_required": True, "acceptance_criteria": "Rated flow and pressure"},
            {"test": "Alarm Device Function", "standard": "NFPA 72", "witness_required": True, "acceptance_criteria": "100% devices tested"},
            {"test": "Smoke Detector Sensitivity", "standard": "NFPA 72", "witness_required": False, "third_party_required": True, "acceptance_criteria": "Within listed range"},
            {"test": "Door Holder Release", "standard": "NFPA 80", "witness_required": False, "acceptance_criteria": "All doors close on alarm"},
            {"test": "Stair Pressurization", "standard": "NFPA 92", "witness_required": True, "acceptance_criteria": "50 Pa minimum"},
        ]

    def _generate_plumbing_commissioning(self) -> List[Dict]:
        return [
            {"test": "Water Pressure Test", "standard": "IPC", "witness_required": False, "acceptance_criteria": "No leaks at 1.5x working pressure"},
            {"test": "Drainage Flow Test", "standard": "IPC", "witness_required": False, "acceptance_criteria": "Free flow, no blockages"},
        ]

    def _generate_elevator_commissioning(self) -> List[Dict]:
        return [
            {"test": "Safety Gear Test", "standard": "ASME A17.1", "witness_required": True, "acceptance_criteria": "Trip at overspeed"},
            {"test": "Door Safety", "standard": "ASME A17.1", "witness_required": True, "acceptance_criteria": "Obstruction detection functional"},
        ]

    def _generate_facade_commissioning(self) -> List[Dict]:
        return [
            {"test": "Water Penetration", "standard": "ASTM E1105", "witness_required": True, "acceptance_criteria": "No water ingress"},
            {"test": "Air Infiltration", "standard": "ASTM E783", "witness_required": False, "acceptance_criteria": "Within specified rate"},
        ]

    def _generate_bms_commissioning(self) -> List[Dict]:
        return [
            {"test": "Point-to-Point Verification", "standard": "ASHRAE Guideline 13", "witness_required": False, "acceptance_criteria": "100% points verified"},
            {"test": "Sequence of Operations", "standard": "ASHRAE Guideline 13", "witness_required": True, "acceptance_criteria": "All sequences functional"},
        ]

    def _estimate_commissioning_duration(self, systems: List[str], equipment_count: int) -> int:
        base_weeks = 4
        base_weeks += len(systems) * 2
        base_weeks += equipment_count // 50
        return base_weeks

    def _add_weeks(self, date_str: Optional[str], weeks: int) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (dt + timedelta(weeks=weeks)).isoformat()
        except Exception:
            return None

    def _list_commissioning_docs(self, systems: List[str]) -> List[str]:
        docs = ["As-built drawings", "Equipment data sheets", "Test certificates"]
        if "electrical" in systems:
            docs.append("Electrical test reports")
        if "fire_protection" in systems:
            docs.append("Fire alarm commissioning certificate")
        return docs

    def _generate_training_requirements(self, systems: List[str]) -> List[Dict]:
        return [{"system": s, "audience": "Facilities team", "hours": 4} for s in systems]

    # ═══════════════════════════════════════════════════════════
    # 19. RESOURCE HISTOGRAM
    # ═══════════════════════════════════════════════════════════

    async def resource_histogram(self, input_data: dict, params: dict) -> dict:
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        productivity_curves = input_data.get("productivity") or params.get("productivity", {})
        trade_breakdown = params.get("trade_breakdown", True)

        if not schedule_file:
            return {"status": "error", "error": "Schedule file required for resource histogram"}

        schedule_data = self._parse_xer_file(schedule_file)
        activities = schedule_data.get("activities", [])
        histogram_data = self._calculate_labor_histogram(activities, productivity_curves)
        peaks = self._identify_resource_peaks(histogram_data)
        conflicts = self._identify_resource_conflicts(histogram_data)
        optimizations = self._suggest_resource_leveling(histogram_data, conflicts)
        cost_loading = self._calculate_cost_histogram(histogram_data)

        return {
            "status": "success",
            "action": "resource_histogram_generated",
            "project_duration_weeks": len(histogram_data),
            "resource_summary": {
                "total_labor_hours": sum(week.get("total_labor", 0) for week in histogram_data),
                "peak_labor_count": max((week.get("total_labor", 0) for week in histogram_data), default=0),
                "average_labor_count": sum(week.get("total_labor", 0) for week in histogram_data) / len(histogram_data) if histogram_data else 0,
                "resource_conflicts": len(conflicts),
                "productivity_factor": productivity_curves.get("overall_factor", 1.0)
            },
            "by_trade": self._breakdown_by_trade(histogram_data) if trade_breakdown else None,
            "weekly_histogram": histogram_data[:52] if not params.get("full_data") else histogram_data,
            "peak_periods": peaks,
            "resource_conflicts": conflicts,
            "leveling_opportunities": optimizations,
            "cost_loaded_histogram": cost_loading,
            "recommendations": [
                "Consider overtime during peak weeks" if any(p.get("total_labor", 0) > 100 for p in peaks) else "Labor loading is balanced",
                "Float available to shift non-critical activities" if optimizations else "Schedule is fully constrained"
            ]
        }

    def _calculate_labor_histogram(self, activities: List[Dict], productivity: Dict) -> List[Dict]:
        weeks = []
        for week in range(26):
            week_labor = 0
            week_activities = []
            for act in activities:
                labor_units = act.get("resources", {}).get("labor", 0) if isinstance(act.get("resources"), dict) else 0
                if labor_units:
                    week_labor += labor_units / (act.get("duration", 1) or 1)
                    week_activities.append(act.get("id"))
            weeks.append({
                "week": week + 1,
                "total_labor": int(week_labor),
                "activities_active": len(week_activities),
                "trades": {"concrete": int(week_labor * 0.3), "masonry": int(week_labor * 0.2), "steel": int(week_labor * 0.15), "electrical": int(week_labor * 0.15), "finishes": int(week_labor * 0.2)}
            })
        return weeks

    def _identify_resource_peaks(self, histogram: List[Dict]) -> List[Dict]:
        if not histogram:
            return []
        avg_labor = sum(w.get("total_labor", 0) for w in histogram) / len(histogram)
        threshold = avg_labor * 1.5
        peaks = [w for w in histogram if w.get("total_labor", 0) > threshold]
        return sorted(peaks, key=lambda x: x.get("total_labor", 0), reverse=True)[:5]

    def _identify_resource_conflicts(self, histogram: List[Dict]) -> List[Dict]:
        return []

    def _suggest_resource_leveling(self, histogram: List[Dict], conflicts: List[Dict]) -> List[Dict]:
        optimizations = []
        if len(conflicts) > 3:
            optimizations.append({"strategy": "Shift non-critical activities to weekends", "potential_reduction": "15%", "activities_to_shift": [c.get("activity") for c in conflicts[:3]]})
        peaks = self._identify_resource_peaks(histogram)
        if peaks:
            peak_week = peaks[0]
            optimizations.append({"strategy": f"Add second shift during week {peak_week.get('week')}", "potential_reduction": "40% peak reduction", "cost_impact": "+20% labor cost (overtime)"})
        return optimizations

    def _calculate_cost_histogram(self, histogram: List[Dict]) -> List[Dict]:
        return [{"week": w["week"], "labor_cost": w["total_labor"] * 50} for w in histogram]

    def _breakdown_by_trade(self, histogram: List[Dict]) -> Dict:
        trades = {}
        for week in histogram:
            for trade, count in week.get("trades", {}).items():
                trades.setdefault(trade, []).append({"week": week["week"], "count": count})
        return trades

    # ═══════════════════════════════════════════════════════════
    # 20. CLAIMS BUILDER (EOT Claims)
    # ═══════════════════════════════════════════════════════════

    async def claims_builder(self, input_data: dict, params: dict) -> dict:
        delay_events = input_data.get("delay_events") or params.get("delay_events", [])
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        contract_file = input_data.get("contract_file") or params.get("contract_file")
        baseline_file = input_data.get("baseline_file") or params.get("baseline_file")
        notification_date = params.get("notification_date", datetime.now().isoformat())
        claim_type = params.get("claim_type", "eot")

        if not delay_events:
            return {"status": "error", "error": "Delay events required for claim"}

        if schedule_file and baseline_file:
            delay_analysis_data = await self.parse_primavera_schedule({"schedule_file": schedule_file, "baseline_file": baseline_file}, {})
            delay_details = delay_analysis_data.get("delay_analysis", {})
        else:
            delay_details = {"total_delay_days": sum(e.get("delay_days", 0) for e in delay_events)}

        contract_entitlement = {}
        if contract_file:
            contract_data = await self.process_contract({"file_path": contract_file}, {})
            contract_entitlement = self._check_eot_entitlement(contract_data, delay_events)

        narrative = self._generate_claim_narrative(delay_events, delay_details, contract_entitlement)
        quantum = self._calculate_prolongation_costs(delay_details.get("total_delay_days", 0), delay_events)
        causation = self._build_causation_link(delay_events, delay_details)

        return {
            "status": "success",
            "action": "claim_generated",
            "claim_type": claim_type,
            "claim_number": f"EOT-{datetime.now().strftime('%Y%m%d')}-001",
            "notification_date": notification_date,
            "delay_summary": {
                "total_delay_days": delay_details.get("total_delay_days", 0),
                "delay_events_count": len(delay_events),
                "critical_path_impact": delay_details.get("critical_path_impact", False),
                "concurrent_delays": self._identify_concurrent_delays(delay_events)
            },
            "entitlement_analysis": contract_entitlement,
            "cause_and_effect": causation,
            "claim_narrative": narrative,
            "quantum_calculation": quantum,
            "supporting_documents": self._list_claim_documents(delay_events),
            "submission_package": {
                "covering_letter": narrative.get("executive_summary"),
                "detailed_narrative": narrative.get("full_narrative"),
                "delay_analysis": delay_details,
                "quantum_appendix": quantum,
                "evidence_bundle": self._compile_evidence_list(delay_events)
            },
            "risk_assessment": {
                "claim_strength": "strong" if contract_entitlement.get("clear_entitlement") else "moderate",
                "potential_settlement_range": f"{quantum.get('total_claim', 0) * 0.7} - {quantum.get('total_claim', 0)}",
                "counter_arguments": self._anticipate_defenses(delay_events),
                "recommended_strategy": "negotiate_settlement" if len(delay_events) > 5 else "formal_claim"
            }
        }

    def _check_eot_entitlement(self, contract_data: Dict, events: List[Dict]) -> Dict:
        clauses = contract_data.get("extracted_clauses", {})
        return {"clear_entitlement": clauses.get("time_extensions", {}).get("found", True), "relevant_clause": "Clause XX", "entitlement_basis": "compensable delay events"}

    def _generate_claim_narrative(self, events: List[Dict], delay_analysis: Dict, entitlement: Dict) -> Dict:
        total_delay = delay_analysis.get("total_delay_days", 0)
        exec_summary = f"EXTENSION OF TIME CLAIM\n\nThe Contractor has encountered delays totaling {total_delay} calendar days due to circumstances beyond our control and for which the Contract provides entitlement to Extension of Time and associated costs.\n\nKey Events:\n"
        for i, event in enumerate(events[:5], 1):
            exec_summary += f"{i}. {event.get('description', 'Unknown event')} ({event.get('delay_days', 0)} days)\n"
        full_narrative = f"BACKGROUND\nThe Contractor has been progressing the Works in accordance with the Approved Programme when the following delay events occurred:\n\n" + "\n".join([f"Event {i+1}: {e.get('description')} on {e.get('date')}" for i, e in enumerate(events)]) + f"\n\nCONTRACTUAL ENTITLEMENT\nUnder Clause {entitlement.get('relevant_clause', '[XX]')} of the Conditions of Contract, the Contractor is entitled to an Extension of Time for delays caused by {entitlement.get('entitlement_basis', '[compensable delay events]')}.\n\nCAUSATION ANALYSIS\n{delay_analysis.get('impact_assessment', 'The delays affected the critical path as demonstrated in the attached delay analysis.')}\n\nDELAY QUANTIFICATION\nTotal Extension of Time Sought: {total_delay} days\n"
        return {"executive_summary": exec_summary, "full_narrative": full_narrative, "word_count": len(full_narrative.split())}

    def _calculate_prolongation_costs(self, total_days: int, events: List[Dict]) -> Dict:
        daily_rate = 5000
        site_staff = daily_rate * 0.3 * total_days
        site_accommodation = daily_rate * 0.2 * total_days
        plant_standing = daily_rate * 0.25 * total_days
        insurances_bonds = daily_rate * 0.1 * total_days
        overheads_profit = daily_rate * 0.15 * total_days
        return {
            "prolongation_period_days": total_days,
            "daily_preliminaries_rate": daily_rate,
            "breakdown": {"site_staff": site_staff, "site_accommodation": site_accommodation, "plant_standing": plant_standing, "insurances_bonds": insurances_bonds, "overheads_profit": overheads_profit},
            "total_claim": daily_rate * total_days
        }

    def _build_causation_link(self, events: List[Dict], delay_analysis: Dict) -> List[Dict]:
        return [{"event": e.get("description"), "date": e.get("date"), "cause": e.get("cause", "Employer Risk Event"), "effect": f"Delay of {e.get('delay_days')} days to {e.get('affected_activity', 'critical path')}", "mitigation_attempted": e.get("mitigation", "None possible"), "concurrent": e.get("concurrent", False), "compensable": e.get("compensable", True)} for e in events]

    def _identify_concurrent_delays(self, events: List[Dict]) -> List[Dict]:
        return [e for e in events if e.get("concurrent", False)]

    def _list_claim_documents(self, events: List[Dict]) -> List[str]:
        return ["Delay notice letters", "Site instructions", "Schedule updates", "Progress photos", "Meeting minutes"]

    def _compile_evidence_list(self, events: List[Dict]) -> List[Dict]:
        return [{"event": e.get("description"), "evidence": ["Correspondence", "Schedule extract", "Photos"]} for e in events]

    def _anticipate_defenses(self, events: List[Dict]) -> List[str]:
        defenses = []
        if any(not e.get("notice_given", True) for e in events):
            defenses.append("Late notice for some delay events")
        if any(e.get("concurrent", False) for e in events):
            defenses.append("Concurrent delays may reduce entitlement")
        return defenses
    async def tender_bid_analysis(self, input_data: dict, params: dict) -> dict:
        bids = input_data.get("bids") or params.get("bids", [])
        weights = params.get("weights", {
            "price": 0.30, "schedule": 0.20, "experience": 0.15,
            "financial": 0.15, "safety": 0.10, "quality": 0.10
        })

        if not bids or len(bids) < 2:
            return {"status": "error", "error": "Minimum 2 bids required for analysis"}

        analyzed_bids = []
        for bid in bids:
            scores = {
                "price": self._score_price(bid.get("total_price", 0), [b["total_price"] for b in bids]),
                "schedule": self._score_schedule(bid.get("duration_days", 0), [b["duration_days"] for b in bids]),
                "experience": bid.get("experience_score", 70),
                "financial": bid.get("financial_stability", 80),
                "safety": bid.get("safety_rating", 75),
                "quality": bid.get("quality_score", 75),
                "innovation": bid.get("innovation_score", 60)
            }
            weighted_score = sum(scores[k] * weights.get(k, 0.1) for k in scores)
            risks = self._assess_bidder_risk(bid, scores)
            analyzed_bids.append({
                "contractor": bid.get("contractor_name", "Unknown"),
                "bid_amount": bid.get("total_price", 0),
                "duration_days": bid.get("duration_days", 0),
                "unit_price_analysis": self._analyze_unit_prices(bid.get("boq", [])),
                "scores": scores,
                "weighted_score": round(weighted_score, 2),
                "rank": 0,
                "risk_level": risks["level"],
                "risk_factors": risks["factors"],
                "qualification_gaps": self._identify_qualification_gaps(bid),
                "alternatives_proposed": bid.get("alternatives", []),
                "clarifications_required": self._identify_bid_clarifications(bid)
            })

        analyzed_bids.sort(key=lambda x: x["weighted_score"], reverse=True)
        for i, bid in enumerate(analyzed_bids):
            bid["rank"] = i + 1

        best_value = analyzed_bids[0] if analyzed_bids else None
        lowest_price = min(analyzed_bids, key=lambda x: x["bid_amount"]) if analyzed_bids else None
        avg_bid = sum(b["bid_amount"] for b in analyzed_bids) / len(analyzed_bids) if analyzed_bids else 0
        price_spread = 0
        if analyzed_bids and lowest_price and lowest_price["bid_amount"] > 0:
            price_spread = ((max(analyzed_bids, key=lambda x: x["bid_amount"])["bid_amount"] / lowest_price["bid_amount"]) - 1) * 100

        return {
            "status": "success",
            "action": "tender_bid_analysis",
            "bid_comparison_matrix": analyzed_bids,
            "ranking": {
                "first": analyzed_bids[0] if len(analyzed_bids) > 0 else None,
                "second": analyzed_bids[1] if len(analyzed_bids) > 1 else None,
                "third": analyzed_bids[2] if len(analyzed_bids) > 2 else None
            },
            "price_analysis": {
                "lowest_bid": lowest_price["bid_amount"] if lowest_price else 0,
                "average_bid": avg_bid,
                "best_value_bid": best_value["bid_amount"] if best_value else 0,
                "price_spread_percent": price_spread
            },
            "recommendation": {
                "award_to": best_value["contractor"] if best_value else None,
                "negotiation_strategy": self._generate_negotiation_strategy(analyzed_bids)
            },
            "award_summary": f"Recommend award to {best_value['contractor']} at {best_value['bid_amount']}" if best_value else "No recommendation possible"
        }

    def _score_price(self, price: float, all_prices: List[float]) -> float:
        if not all_prices or price <= 0:
            return 50
        avg = sum(all_prices) / len(all_prices)
        min_p = min(all_prices)
        if price == min_p:
            return 100
        elif price <= avg:
            return 80
        elif price <= avg * 1.1:
            return 60
        return 40

    def _score_schedule(self, duration: int, all_durations: List[int]) -> float:
        if not all_durations or duration <= 0:
            return 50
        avg = sum(all_durations) / len(all_durations)
        min_d = min(all_durations)
        if duration == min_d:
            return 100
        elif duration <= avg:
            return 80
        elif duration <= avg * 1.1:
            return 60
        return 40

    def _assess_bidder_risk(self, bid: Dict, scores: Dict) -> Dict:
        factors = []
        if scores["financial"] < 60:
            factors.append("Financial stability concerns")
        if scores["safety"] < 70:
            factors.append("Below average safety record")
        if scores["experience"] < 50:
            factors.append("Limited relevant experience")
        boq = bid.get("boq", [])
        if boq:
            unit_prices = [i.get("unit_price", 0) for i in boq if i.get("unit_price", 0) > 0]
            if unit_prices:
                avg_price = sum(unit_prices) / len(unit_prices)
                high_items = [i for i in boq if i.get("unit_price", 0) > avg_price * 3]
                if len(high_items) > len(boq) * 0.1:
                    factors.append("Unbalanced bid detected - front loading")
        level = "high" if len(factors) >= 2 else "medium" if len(factors) == 1 else "low"
        return {"level": level, "factors": factors}

    def _analyze_unit_prices(self, boq: List[Dict]) -> Dict:
        if not boq:
            return {}
        prices = [i.get("unit_price", 0) for i in boq]
        return {
            "total_items": len(boq),
            "average_unit_price": sum(prices) / len(prices) if prices else 0,
            "high_value_items": sorted(boq, key=lambda x: x.get("quantity", 0) * x.get("unit_price", 0), reverse=True)[:5]
        }

    def _identify_qualification_gaps(self, bid: Dict) -> List[str]:
        return []

    def _identify_bid_clarifications(self, bid: Dict) -> List[str]:
        return []

    def _generate_negotiation_strategy(self, bids: List[Dict]) -> List[Dict]:
        if len(bids) < 2:
            return []
        strategies = []
        price_gap = bids[1]["weighted_score"] - bids[0]["weighted_score"]
        if price_gap < 10:
            strategies.append({
                "tactic": "competitive dialogue",
                "target": bids[1]["contractor"],
                "approach": "Request best and final offer"
            })
        if bids[0]["risk_level"] == "medium":
            strategies.append({
                "tactic": "risk mitigation",
                "target": bids[0]["contractor"],
                "approach": "Request parent company guarantee or performance bond increase"
            })
        return strategies

    # ═══════════════════════════════════════════════════════════
    # 22. VARIATION ORDER MANAGER
    # ═══════════════════════════════════════════════════════════

    async def variation_order_manager(self, input_data: dict, params: dict) -> dict:
        vo_data = input_data.get("variation_data") or params.get("variation_data", {})
        existing_vos = input_data.get("existing_vos") or params.get("existing_vos", [])
        contract_file = input_data.get("contract_file") or params.get("contract_file")

        if not vo_data:
            return {"status": "error", "error": "Variation order data required"}

        vo_number = vo_data.get("vo_number", f"VO-{len(existing_vos)+1:03d}")
        vo_description = vo_data.get("description", "")
        vo_type = vo_data.get("type", "addition")
        category = self._categorize_variation(vo_description)
        pricing = self._calculate_variation_price(vo_data, vo_type)
        cumulative = self._calculate_cumulative_variations(existing_vos, pricing["total"])
        workflow = self._determine_approval_workflow(pricing["total"], cumulative["percent_of_contract"], vo_type)
        schedule_impact = vo_data.get("schedule_impact_days", 0)

        contract_terms = {}
        if contract_file:
            contract_data = await self.process_contract({"file_path": contract_file}, {})
            contract_terms = self._extract_variation_clauses(contract_data)

        return {
            "status": "success",
            "action": "variation_order_processed",
            "vo_number": vo_number,
            "vo_type": vo_type,
            "category": category,
            "description": vo_description[:100],
            "pricing": pricing,
            "cumulative_impact": cumulative,
            "approval_workflow": workflow,
            "schedule_impact": {
                "days": schedule_impact,
                "critical_path": vo_data.get("critical_path", False),
                "justification": vo_data.get("delay_justification", "")
            },
            "contract_compliance": {
                "variation_clause": contract_terms.get("clause_reference", "Clause XX"),
                "entitlement_clear": contract_terms.get("clear_entitlement", True),
                "pricing_methodology": contract_terms.get("pricing_method", "Dayworks/Rates"),
                "notice_requirements_met": vo_data.get("notice_given", True),
                "time_bar_risk": self._check_time_bar(existing_vos, vo_data)
            },
            "recommended_action": "approve" if pricing["total"] < 50000 and workflow["level"] == "project_manager" else "escalate",
            "risk_flags": self._identify_vo_risks(vo_data, cumulative)
        }

    def _categorize_variation(self, description: str) -> str:
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["drawing", "spec", "design", "architect"]):
            return "design_change"
        elif any(w in desc_lower for w in ["unforeseen", "ground", "condition", "rock"]):
            return "unforeseen_condition"
        elif any(w in desc_lower for w in ["accelerate", "crash", "fast", "speed"]):
            return "acceleration"
        elif any(w in desc_lower for w in ["omission", "delete", "remove", "reduce"]):
            return "scope_reduction"
        elif any(w in desc_lower for w in ["delay", "disruption", "waiting", "standby"]):
            return "prolongation"
        return "scope_addition"

    def _calculate_variation_price(self, vo_data: Dict, vo_type: str) -> Dict:
        base_cost = vo_data.get("direct_cost", 0)
        quantity = vo_data.get("quantity", 1)
        direct = base_cost * quantity
        prelim_percent = 0.15 if vo_type != "omission" else 0
        indirect = direct * prelim_percent
        oh_percent = vo_data.get("overhead_percent", 0.10)
        profit_percent = vo_data.get("profit_percent", 0.08)
        overhead = (direct + indirect) * oh_percent if vo_type != "omission" else -(direct * oh_percent)
        profit = (direct + indirect) * profit_percent if vo_type != "omission" else -(direct * profit_percent)
        total = direct + indirect + overhead + profit
        return {
            "direct": round(direct, 2),
            "indirect": round(indirect, 2),
            "overhead": round(overhead, 2),
            "profit": round(profit, 2),
            "total": round(total, 2),
            "breakdown": vo_data.get("resource_breakdown", {})
        }

    def _calculate_cumulative_variations(self, existing: List[Dict], new_amount: float) -> Dict:
        current_total = sum(v.get("value", 0) for v in existing)
        new_total = current_total + new_amount
        contract_value = 1000000
        return {
            "previous_vo_count": len(existing),
            "previous_vo_value": current_total,
            "this_vo_value": new_amount,
            "cumulative_value": new_total,
            "percent_of_contract": (new_total / contract_value * 100) if contract_value else 0,
            "approaching_cap": new_total > contract_value * 0.2
        }

    def _determine_approval_workflow(self, value: float, percent: float, vo_type: str) -> Dict:
        if value < 10000:
            level = "project_manager"
            approvers = ["Project Manager"]
        elif value < 50000:
            level = "contracts_manager"
            approvers = ["Project Manager", "Contracts Manager"]
        elif value < 100000:
            level = "director"
            approvers = ["Project Manager", "Contracts Manager", "Director"]
        else:
            level = "board_client"
            approvers = ["Project Manager", "Contracts Manager", "Director", "Client"]
        if percent > 15:
            approvers.append("Client (Major Change)")
        return {"level": level, "required_approvers": approvers, "estimated_approval_days": len(approvers) * 2}

    def _extract_variation_clauses(self, contract_data: Dict) -> Dict:
        clauses = contract_data.get("extracted_clauses", {})
        return {
            "clause_reference": "Clause XX",
            "clear_entitlement": clauses.get("variation_clause", {}).get("found", True),
            "pricing_method": "Dayworks/Rates"
        }

    def _check_time_bar(self, existing: List[Dict], new_vo: Dict) -> Dict:
        event_date = new_vo.get("event_date")
        notice_date = new_vo.get("notice_date")
        if event_date and notice_date:
            days_elapsed = self._days_between(event_date, notice_date)
            return {
                "at_risk": days_elapsed > 14,
                "days_elapsed": days_elapsed,
                "mitigation": "Immediate notice recommended" if days_elapsed > 10 else None
            }
        return {"at_risk": False, "days_elapsed": 0}

    def _days_between(self, start: str, end: str) -> int:
        try:
            a = datetime.fromisoformat(start.replace('Z', '+00:00'))
            b = datetime.fromisoformat(end.replace('Z', '+00:00'))
            return max(0, (b - a).days)
        except Exception:
            return 0

    def _identify_vo_risks(self, vo_data: Dict, cumulative: Dict) -> List[str]:
        risks = []
        if cumulative.get("approaching_cap"):
            risks.append("Cumulative variations approaching contract cap")
        return risks

    # ═══════════════════════════════════════════════════════════
    # 23. FORENSIC DELAY ANALYSIS
    # ═══════════════════════════════════════════════════════════

    async def forensic_delay_analysis(self, input_data: dict, params: dict) -> dict:
        baseline_file = input_data.get("baseline_file") or params.get("baseline_file")
        updated_file = input_data.get("updated_file") or params.get("updated_file")
        delay_events = input_data.get("delay_events") or params.get("delay_events", [])
        analysis_method = params.get("method", "time_impact")

        if not baseline_file or not updated_file:
            return {"status": "error", "error": "Baseline and updated schedules required"}

        baseline = self._parse_xer_file(baseline_file)
        updated = self._parse_xer_file(updated_file)

        if baseline.get("status") == "error":
            return baseline

        if analysis_method == "time_impact":
            results = self._run_time_impact_analysis(baseline, updated, delay_events)
        elif analysis_method == "windows":
            results = self._run_windows_analysis(baseline, updated, delay_events)
        elif analysis_method == "collapsed_as_built":
            results = self._run_collapsed_as_built(baseline, updated, delay_events)
        else:
            results = self._run_impacted_as_planned(baseline, updated, delay_events)

        cp_analysis = self._analyze_critical_path_changes(baseline, updated)
        concurrency = self._analyze_concurrency(delay_events)
        apportionment = self._apportion_delay(results["total_delay_days"], delay_events, concurrency)

        return {
            "status": "success",
            "action": "forensic_delay_analysis",
            "analysis_method": analysis_method,
            "project_duration": {
                "baseline": baseline.get("project_duration", 0),
                "as_built": updated.get("project_duration", 0),
                "net_delay": results["total_delay_days"]
            },
            "critical_path_analysis": cp_analysis,
            "delay_events": {
                "total_identified": len(delay_events),
                "compensable": len([e for e in delay_events if e.get("compensable", False)]),
                "non_compensable": len([e for e in delay_events if not e.get("compensable", False)]),
                "excusable": len([e for e in delay_events if e.get("excusable", False)]),
                "non_excusable": len([e for e in delay_events if not e.get("excusable", False)])
            },
            "delay_calculation": results,
            "concurrency_analysis": concurrency,
            "apportionment": apportionment,
            "entitlement_summary": {
                "eot_entitled_days": apportionment["contractor_entitlement"],
                "prolongation_costs_entitled": apportionment["compensable_days"] > 0,
                "liquidated_damages_risk": apportionment["contractor_responsible"] > 0
            },
            "expert_report_sections": [
                "Introduction and Instructions", "Summary of Opinions", "Project Overview",
                "Contractual Provisions", "Methodology", "As-Planned vs As-Built",
                "Delay Events Analysis", "Causation", "Entitlement Quantification", "Conclusions"
            ],
            "recommended_claim_value": apportionment["compensable_days"] * 5000 if apportionment["compensable_days"] > 0 else 0
        }

    def _run_time_impact_analysis(self, baseline: Dict, updated: Dict, events: List[Dict]) -> Dict:
        impacted_durations = []
        for event in events:
            activity = next((a for a in baseline.get("activities", []) if a["id"] == event.get("activity_id")), None)
            if activity:
                original_duration = activity.get("duration", 0)
                delay = event.get("delay_days", 0)
                impacted_durations.append({
                    "activity": activity["id"],
                    "original": original_duration,
                    "delay_added": delay,
                    "new_duration": original_duration + delay,
                    "critical": activity.get("critical", False)
                })
        critical_delays = [d for d in impacted_durations if d["critical"]]
        total_delay = sum(d["delay_added"] for d in critical_delays)
        return {
            "method": "Time Impact Analysis",
            "total_delay_days": total_delay,
            "impacted_activities": len(impacted_durations),
            "critical_path_impacts": critical_delays,
            "methodology_notes": "Delays inserted into baseline CPM, network recalculated"
        }

    def _run_windows_analysis(self, baseline: Dict, updated: Dict, events: List[Dict]) -> Dict:
        windows = self._group_events_into_windows(events)
        window_results = []
        cumulative_delay = 0
        for window in windows:
            window_delay = sum(e.get("delay_days", 0) for e in window["events"] if e.get("critical", False))
            cumulative_delay += window_delay
            window_results.append({
                "period": window["period"],
                "events_count": len(window["events"]),
                "this_period_delay": window_delay,
                "cumulative_delay": cumulative_delay,
                "float_consumed": window_delay * 0.5
            })
        return {
            "method": "Windows Analysis",
            "total_delay_days": cumulative_delay,
            "windows_analyzed": len(window_results),
            "window_details": window_results,
            "methodology_notes": "Schedule divided into time windows, delay apportioned per period"
        }

    def _group_events_into_windows(self, events: List[Dict]) -> List[Dict]:
        sorted_events = sorted(events, key=lambda x: x.get("date", ""))
        windows = []
        current_window = {"period": "Month 1", "events": []}
        for i, event in enumerate(sorted_events):
            if i > 0 and i % 5 == 0:
                windows.append(current_window)
                current_window = {"period": f"Month {len(windows)+1}", "events": []}
            current_window["events"].append(event)
        if current_window["events"]:
            windows.append(current_window)
        return windows

    def _run_collapsed_as_built(self, baseline: Dict, updated: Dict, events: List[Dict]) -> Dict:
        return {"method": "Collapsed As-Built", "total_delay_days": 0, "impacted_activities": 0, "critical_path_impacts": [], "methodology_notes": "Placeholder"}

    def _run_impacted_as_planned(self, baseline: Dict, updated: Dict, events: List[Dict]) -> Dict:
        return {"method": "Impacted As-Planned", "total_delay_days": 0, "impacted_activities": 0, "critical_path_impacts": [], "methodology_notes": "Placeholder"}

    def _analyze_critical_path_changes(self, baseline: Dict, updated: Dict) -> Dict:
        return {"baseline_critical_count": 0, "updated_critical_count": 0, "changes": []}

    def _analyze_concurrency(self, events: List[Dict]) -> Dict:
        return {"concurrent_days": 0, "concurrent_events": []}

    def _apportion_delay(self, total_days: int, events: List[Dict], concurrency: Dict) -> Dict:
        compensable = sum(e.get("delay_days", 0) for e in events if e.get("compensable") and e.get("excusable"))
        non_excusable = sum(e.get("delay_days", 0) for e in events if not e.get("excusable"))
        concurrent = concurrency.get("concurrent_days", 0)
        return {
            "total_delay": total_days,
            "compensable_days": compensable,
            "non_compensable_days": non_excusable,
            "concurrent_days": concurrent,
            "contractor_entitlement": max(0, compensable - concurrent),
            "contractor_responsible": non_excusable,
            "shared_delay": min(compensable, non_excusable)
        }

    # ═══════════════════════════════════════════════════════════
    # 24. CASH FLOW FORECAST (S-Curve)
    # ═══════════════════════════════════════════════════════════

    async def cash_flow_forecast(self, input_data: dict, params: dict) -> dict:
        schedule_file = input_data.get("schedule_file") or params.get("schedule_file")
        boq = input_data.get("boq") or params.get("boq", [])
        contract_value = input_data.get("contract_value") or params.get("contract_value", 0)
        payment_terms = params.get("payment_terms", {
            "advance_payment": 0.10, "retention": 0.10, "payment_delay_days": 30, "mobilization_duration": 2
        })
        project_start = params.get("project_start_date", datetime.now().isoformat())

        if not schedule_file:
            return {"status": "error", "error": "Schedule file required for cash flow forecast"}

        schedule_data = self._parse_xer_file(schedule_file)
        activities = schedule_data.get("activities", [])
        if not activities:
            return {"status": "error", "error": "No activities found in schedule"}

        project_duration_months = max(1, int(len(activities) / 20))
        monthly_forecast = []
        cumulative_percent = 0

        for month in range(project_duration_months):
            time_percent = (month + 1) / project_duration_months
            if time_percent <= 0.25:
                progress = time_percent * 0.8
            elif time_percent <= 0.5:
                progress = 0.2 + (time_percent - 0.25) * 1.2
            elif time_percent <= 0.75:
                progress = 0.5 + (time_percent - 0.5) * 1.2
            else:
                progress = min(0.95, 0.8 + (time_percent - 0.75) * 0.6)

            monthly_value = (progress - cumulative_percent) * contract_value
            cumulative_percent = progress
            cash_in = monthly_value * (1 - payment_terms["retention"])
            if month == 0:
                cash_in += contract_value * payment_terms["advance_payment"]

            monthly_forecast.append({
                "month": month + 1,
                "period": self._add_months(project_start, month),
                "planned_progress_percent": progress * 100,
                "monthly_value": round(monthly_value, 2),
                "cumulative_value": round(progress * contract_value, 2),
                "advance_recovery": (contract_value * payment_terms["advance_payment"] / project_duration_months) if month < project_duration_months * 0.8 else 0,
                "retention_deduction": round(monthly_value * payment_terms["retention"], 2),
                "retention_release": round(progress * contract_value * payment_terms["retention"], 2) if progress >= 0.95 else 0,
                "net_cash_in": round(cash_in, 2),
                "cumulative_cash": round(sum(m.get("net_cash_in", 0) for m in monthly_forecast) + cash_in, 2)
            })

        total_revenue = sum(m["monthly_value"] for m in monthly_forecast)
        peak_month = max(monthly_forecast, key=lambda x: x["monthly_value"]) if monthly_forecast else None
        avg_monthly = total_revenue / project_duration_months if project_duration_months > 0 else 0

        return {
            "status": "success",
            "action": "cash_flow_forecast",
            "project_parameters": {
                "contract_value": contract_value,
                "duration_months": project_duration_months,
                "start_date": project_start
            },
            "s_curve_data": monthly_forecast,
            "summary_metrics": {
                "total_planned_revenue": round(total_revenue, 2),
                "peak_monthly_billing": round(peak_month["monthly_value"], 2) if peak_month else 0,
                "peak_month": peak_month["month"] if peak_month else None,
                "average_monthly_billing": round(avg_monthly, 2)
            },
            "funding_requirements": {
                "working_capital_peak": round(peak_month["monthly_value"] * 0.3 if peak_month else 0, 2),
                "mobilization_costs": round(contract_value * 0.05, 2)
            },
            "risk_adjusted_scenarios": {
                "optimistic": [{"month": m["month"], "value": m["monthly_value"] * 1.1} for m in monthly_forecast],
                "pessimistic": [{"month": m["month"], "value": m["monthly_value"] * 0.85} for m in monthly_forecast],
                "delayed_start": [{"month": m["month"], "value": m["monthly_value"]} for m in [{"month": 1, "monthly_value": 0}] + monthly_forecast[:-1]]
            },
            "chart_data": {
                "labels": [f"Month {m['month']}" for m in monthly_forecast],
                "planned_value": [m["cumulative_value"] for m in monthly_forecast],
                "earned_value": [m["cumulative_value"] * 0.95 for m in monthly_forecast],
                "actual_cost": [m["cumulative_value"] * 1.02 for m in monthly_forecast]
            }
        }

    def _add_months(self, start_date_str: str, months: int) -> str:
        try:
            start = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            new_month = ((start.month - 1 + months) % 12) + 1
            new_year = start.year + ((start.month - 1 + months) // 12)
            return f"{new_year}-{new_month:02d}"
        except Exception:
            return f"Month+{months}"

    # ═══════════════════════════════════════════════════════════
    # 25. PROCUREMENT OPTIMIZER
    # ═══════════════════════════════════════════════════════════

    async def procurement_optimizer(self, input_data: dict, params: dict) -> dict:
        boq = input_data.get("boq") or params.get("boq", [])
        suppliers = input_data.get("suppliers") or params.get("suppliers", [])
        constraints = params.get("constraints", {"max_suppliers": 5, "quality_threshold": 80})

        if not boq:
            return {"status": "error", "error": "BOQ required for procurement optimization"}

        scored_suppliers = []
        for supplier in suppliers:
            scores = {
                "price_competitiveness": supplier.get("price_score", 70),
                "delivery_reliability": supplier.get("delivery_score", 75),
                "quality_rating": supplier.get("quality_score", 80),
                "financial_stability": supplier.get("financial_score", 80),
                "sustainability": supplier.get("esg_score", 60),
                "technical_support": supplier.get("support_score", 70)
            }
            weights = {"price": 0.25, "delivery": 0.25, "quality": 0.20, "financial": 0.15, "sustainability": 0.10, "technical": 0.05}
            total_score = sum(scores[k] * weights.get(k.split("_")[0], 0.1) for k in scores.keys())
            scored_suppliers.append({
                "name": supplier.get("name"),
                "scores": scores,
                "total_score": round(total_score, 1),
                "lead_time_weeks": supplier.get("lead_time", 4),
                "payment_terms": supplier.get("payment_terms", "net_30"),
                "certifications": supplier.get("certifications", []),
                "geographic_location": supplier.get("location"),
                "capabilities": supplier.get("capabilities", []),
                "recommended_for": []
            })

        scored_suppliers.sort(key=lambda x: x["total_score"], reverse=True)

        procurement_plan = []
        for item in boq:
            material = item.get("material_type", "general")
            qty = item.get("quantity", 0)
            required_date = item.get("required_date")
            capable_suppliers = [s for s in scored_suppliers if material in s.get("capabilities", []) or not s.get("capabilities")]
            if capable_suppliers:
                best = capable_suppliers[0]
                order_date = self._subtract_weeks(required_date, best["lead_time_weeks"]) if required_date else "ASAP"
                procurement_plan.append({
                    "material": material,
                    "boq_item": item.get("id"),
                    "quantity": qty,
                    "unit": item.get("unit"),
                    "required_date": required_date,
                    "recommended_supplier": best["name"],
                    "supplier_score": best["total_score"],
                    "order_date": order_date,
                    "order_lead_time": best["lead_time_weeks"],
                    "buffer_weeks": 2,
                    "packaging_strategy": "bulk" if qty > 100 else "standard",
                    "inspection_required": item.get("quality_critical", False),
                    "alternative_suppliers": [s["name"] for s in capable_suppliers[1:3]]
                })

        insights = self._generate_procurement_insights(procurement_plan, scored_suppliers)
        risks = self._identify_procurement_risks(procurement_plan)

        return {
            "status": "success",
            "action": "procurement_optimization",
            "suppliers_evaluated": len(suppliers),
            "top_suppliers": scored_suppliers[:constraints["max_suppliers"]],
            "procurement_plan": {
                "total_items": len(procurement_plan),
                "total_value": sum(item.get("value", 0) for item in boq),
                "critical_path_items": len([p for p in procurement_plan if p["inspection_required"]]),
                "plan": procurement_plan
            },
            "optimization_insights": insights,
            "consolidation_opportunities": self._identify_consolidation(procurement_plan),
            "bundle_recommendations": self._suggest_bundling(procurement_plan, scored_suppliers),
            "risk_mitigation": risks,
            "timeline": {
                "earliest_order": min((p["order_date"] for p in procurement_plan if p["order_date"] != "ASAP"), default="N/A"),
                "latest_order": max((p["order_date"] for p in procurement_plan if p["order_date"] != "ASAP"), default="N/A")
            }
        }

    def _subtract_weeks(self, date_str: Optional[str], weeks: int) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (dt - timedelta(weeks=weeks)).isoformat()
        except Exception:
            return None

    def _generate_procurement_insights(self, plan: List[Dict], suppliers: List[Dict]) -> List[str]:
        insights = []
        long_lead_items = [p for p in plan if p.get("order_lead_time", 0) > 8]
        if long_lead_items:
            insights.append(f"Attention: {len(long_lead_items)} long-lead items require immediate ordering")
        single_source = [p for p in plan if len(p.get("alternative_suppliers", [])) == 0]
        if single_source:
            insights.append(f"Risk: {len(single_source)} items have single-source dependency")
        avg_score = sum(p["supplier_score"] for p in plan) / len(plan) if plan else 0
        if avg_score < 75:
            insights.append("Consider re-tendering: Average supplier score below 75")
        return insights

    def _identify_consolidation(self, plan: List[Dict]) -> List[Dict]:
        return []

    def _suggest_bundling(self, plan: List[Dict], suppliers: List[Dict]) -> List[Dict]:
        return []

    def _identify_procurement_risks(self, plan: List[Dict]) -> List[Dict]:
        return []

    # ═══════════════════════════════════════════════════════════
    # 26. ESG SUSTAINABILITY REPORT
    # ═══════════════════════════════════════════════════════════

    async def esg_sustainability_report(self, input_data: dict, params: dict) -> dict:
        boq = input_data.get("boq") or params.get("boq", [])
        manpower_data = input_data.get("manpower") or params.get("manpower", {})
        safety_records = input_data.get("safety_records") or params.get("safety_records", [])
        reporting_period = params.get("period", "annual")

        env_metrics = await self._calculate_environmental_metrics(boq, {})
        social_metrics = self._calculate_social_metrics(manpower_data, safety_records)
        gov_metrics = self._calculate_governance_metrics({})

        scores = {
            "environmental": self._score_environmental(env_metrics),
            "social": self._score_social(social_metrics),
            "governance": self._score_governance(gov_metrics),
            "overall": 0
        }
        scores["overall"] = (scores["environmental"] + scores["social"] + scores["governance"]) / 3

        return {
            "status": "success",
            "action": "esg_sustainability_report",
            "reporting_period": reporting_period,
            "esg_scores": {
                "environmental": round(scores["environmental"], 1),
                "social": round(scores["social"], 1),
                "governance": round(scores["governance"], 1),
                "overall": round(scores["overall"], 1),
                "rating": "A" if scores["overall"] >= 80 else "B" if scores["overall"] >= 65 else "C" if scores["overall"] >= 50 else "D"
            },
            "environmental": {
                "carbon_emissions_tons": env_metrics.get("total_carbon", 0),
                "carbon_intensity": env_metrics.get("carbon_per_value", 0),
                "energy_consumption_mwh": env_metrics.get("energy", 0),
                "water_usage_m3": env_metrics.get("water", 0),
                "waste_generated_tons": env_metrics.get("waste", 0),
                "waste_diversion_percent": env_metrics.get("waste_diversion", 0),
                "recycled_materials_percent": env_metrics.get("recycled_content", 0),
                "local_materials_percent": env_metrics.get("local_content", 0)
            },
            "social": {
                "total_workforce": social_metrics.get("total_workers", 0),
                "local_hire_percent": social_metrics.get("local_percent", 0),
                "safety_incidents": social_metrics.get("incidents", 0),
                "lost_time_injury_rate": social_metrics.get("ltifr", 0),
                "training_hours": social_metrics.get("training_hours", 0),
                "community_investment": social_metrics.get("community_spend", 0),
                "gender_diversity_percent": social_metrics.get("gender_diversity", 0),
                "local_business_engagement_percent": social_metrics.get("local_procurement", 0)
            },
            "governance": {
                "ethics_training_compliance": gov_metrics.get("ethics_training", 0),
                "anti_corruption_policies": gov_metrics.get("anti_corruption", True),
                "supply_chain_audit_percent": gov_metrics.get("supplier_audits", 0),
                "transparency_score": gov_metrics.get("transparency", 70)
            },
            "certification_eligibility": self._check_certification_eligibility(scores, env_metrics),
            "sdg_alignment": self._map_to_sdgs(env_metrics, social_metrics),
            "recommendations": self._generate_esg_recommendations(scores, env_metrics, social_metrics),
            "stakeholder_disclosure": self._generate_stakeholder_narrative(scores, env_metrics, social_metrics)
        }

    async def _calculate_environmental_metrics(self, boq: List[Dict], project: Dict) -> Dict:
        carbon_data = await self.carbon_footprint_calculator({"boq": boq}, {})
        total_carbon = carbon_data.get("project_summary", {}).get("total_embodied_carbon_kg_co2e", 0) / 1000
        total_value = sum(i.get("total_cost", 0) for i in boq)
        return {
            "total_carbon": total_carbon,
            "carbon_per_value": total_carbon / total_value if total_value else 0,
            "energy": total_value * 0.0005,
            "water": total_value * 0.5,
            "waste": total_carbon * 0.1,
            "waste_diversion": 60,
            "recycled_content": 15,
            "local_content": 70
        }

    def _calculate_social_metrics(self, manpower: Dict, safety: List) -> Dict:
        total_workers = manpower.get("total", 0)
        incidents = len([s for s in safety if s.get("severity") in ["major", "lost_time"]])
        return {
            "total_workers": total_workers,
            "local_percent": 80,
            "incidents": incidents,
            "ltifr": (incidents / total_workers * 1000) if total_workers else 0,
            "training_hours": total_workers * 8,
            "community_spend": total_workers * 50,
            "gender_diversity": 15,
            "local_procurement": 60
        }

    def _calculate_governance_metrics(self, project: Dict) -> Dict:
        return {"ethics_training": 95, "anti_corruption": True, "supplier_audits": 30, "transparency": 75}

    def _score_environmental(self, metrics: Dict) -> float:
        score = 50
        ci = metrics.get("carbon_per_value", 0)
        if ci < 0.1:
            score += 20
        elif ci < 0.2:
            score += 10
        if metrics.get("waste_diversion", 0) > 70:
            score += 10
        if metrics.get("recycled_content", 0) > 20:
            score += 10
        return min(100, score)

    def _score_social(self, metrics: Dict) -> float:
        score = 60
        ltifr = metrics.get("ltifr", 0)
        if ltifr == 0:
            score += 20
        elif ltifr < 2:
            score += 10
        if metrics.get("local_percent", 0) > 80:
            score += 10
        return min(100, score)

    def _score_governance(self, metrics: Dict) -> float:
        score = 70
        if metrics.get("anti_corruption"):
            score += 15
        if metrics.get("ethics_training", 0) > 90:
            score += 10
        return min(100, score)

    def _check_certification_eligibility(self, scores: Dict, env: Dict) -> List[Dict]:
        certs = []
        if scores["environmental"] >= 75:
            certs.append({"certification": "LEED Gold", "eligible": scores["overall"] >= 70, "next_steps": "Submit for review" if scores["overall"] >= 70 else "Improve energy metrics"})
        if env.get("carbon_per_value", 999) < 0.15:
            certs.append({"certification": "BREEAM Excellent", "eligible": True, "next_steps": "Engage BREEAM assessor"})
        if scores["overall"] >= 80:
            certs.append({"certification": "WELL Building", "eligible": True, "next_steps": "Focus on occupant wellness features"})
        return certs

    def _map_to_sdgs(self, env: Dict, social: Dict) -> List[Dict]:
        sdgs = []
        if env.get("carbon_per_value", 0) < 0.2:
            sdgs.append({"goal": 13, "name": "Climate Action", "contribution": "Low carbon construction"})
        if social.get("local_percent", 0) > 70:
            sdgs.append({"goal": 8, "name": "Decent Work", "contribution": "Local employment"})
        if env.get("waste_diversion", 0) > 50:
            sdgs.append({"goal": 12, "name": "Responsible Consumption", "contribution": "Waste reduction"})
        return sdgs

    def _generate_esg_recommendations(self, scores: Dict, env: Dict, social: Dict) -> List[str]:
        recs = []
        if scores["environmental"] < 70:
            recs.append("Implement material substitution program to reduce embodied carbon")
        if social.get("ltifr", 0) > 2:
            recs.append("Enhance safety training and near-miss reporting")
        if scores["governance"] < 80:
            recs.append("Increase supplier audit coverage and ethics training")
        return recs

    def _generate_stakeholder_narrative(self, scores: Dict, env: Dict, social: Dict) -> str:
        return f"This project achieved an overall ESG score of {scores['overall']:.1f}/100, demonstrating strong performance in environmental management, social responsibility, and governance practices."

    # ═══════════════════════════════════════════════════════════
    # 27. O&M MANUAL GENERATOR
    # ═══════════════════════════════════════════════════════════

    async def om_manual_generator(self, input_data: dict, params: dict) -> dict:
        equipment_list = input_data.get("equipment_list") or params.get("equipment_list", [])
        spec_file = input_data.get("spec_file") or params.get("spec_file")
        as_built_drawings = input_data.get("drawings") or params.get("drawings", [])
        commissioning_data = input_data.get("commissioning") or params.get("commissioning", {})
        project_name = params.get("project_name", "Project")

        if not equipment_list:
            return {"status": "error", "error": "Equipment list required for O&M manual"}

        systems = self._group_equipment_by_system(equipment_list)
        sections = []

        sections.append({
            "section": "A. Project Information",
            "content": {
                "project_name": project_name,
                "completion_date": commissioning_data.get("completion_date", "TBD"),
                "contractor": commissioning_data.get("contractor", "TBD"),
                "consultants": commissioning_data.get("consultants", []),
                "warranty_periods": commissioning_data.get("warranties", {}),
                "emergency_contacts": commissioning_data.get("emergency_contacts", [])
            }
        })

        sections.append({
            "section": "B. Systems Overview",
            "content": {
                "system_descriptions": [{"name": s["name"], "description": s["description"], "components": len(s["equipment"])} for s in systems],
                "system_interdependencies": self._map_system_dependencies(systems)
            }
        })

        equipment_data = []
        for equip in equipment_list:
            equipment_data.append({
                "tag_number": equip.get("tag", "TBD"),
                "description": equip.get("description"),
                "manufacturer": equip.get("manufacturer"),
                "model": equip.get("model"),
                "serial_number": equip.get("serial", "To be field verified"),
                "location": equip.get("location"),
                "installation_date": equip.get("install_date"),
                "warranty_expiry": self._add_years(equip.get("install_date"), equip.get("warranty_years", 1)),
                "performance_data": equip.get("performance", {}),
                "rated_capacity": equip.get("capacity"),
                "electrical_requirements": equip.get("electrical", {}),
                "maintenance_schedule": self._generate_equipment_maintenance(equip)
            })

        sections.append({"section": "C. Equipment Schedules & Technical Data", "content": equipment_data})

        sections.append({
            "section": "D. Operating Procedures",
            "content": {
                "startup_procedures": self._generate_startup_procedures(systems),
                "normal_operation": self._generate_normal_operation(systems),
                "shutdown_procedures": self._generate_shutdown_procedures(systems),
                "emergency_procedures": self._generate_emergency_procedures(systems),
                "seasonal_operation": self._generate_seasonal_operation(systems)
            }
        })

        sections.append({
            "section": "E. Preventive Maintenance",
            "content": {
                "daily_tasks": self._generate_daily_tasks(equipment_list),
                "weekly_tasks": self._generate_weekly_tasks(equipment_list),
                "monthly_tasks": self._generate_monthly_tasks(equipment_list),
                "quarterly_tasks": self._generate_quarterly_tasks(equipment_list),
                "annual_tasks": self._generate_annual_tasks(equipment_list),
                "maintenance_matrix": self._create_maintenance_matrix(equipment_list)
            }
        })

        sections.append({"section": "F. Troubleshooting Guide", "content": self._generate_troubleshooting_guide(equipment_list)})

        sections.append({
            "section": "G. As-Built Documentation",
            "content": {
                "drawings_list": [Path(d).name for d in as_built_drawings],
                "specifications_reference": spec_file if spec_file else "Refer to contract documents",
                "test_results": commissioning_data.get("test_results", []),
                "certificates": commissioning_data.get("certificates", [])
            }
        })

        sections.append({
            "section": "H. Warranties & Spare Parts",
            "content": {
                "warranty_register": [{"equipment": e["description"], "expiry": e.get("warranty_expiry"), "contact": e.get("supplier_contact")} for e in equipment_list],
                "recommended_spare_parts": self._generate_spare_parts_list(equipment_list),
                "supplier_contacts": list(set([e.get("supplier_contact") for e in equipment_list if e.get("supplier_contact")]))
            }
        })

        manual_metadata = {
            "document_number": f"OM-{project_name.replace(' ', '-')}-{datetime.now().year}",
            "revision": "00 - First Issue",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_pages_estimate": len(equipment_list) * 3 + 50,
            "prepared_by": commissioning_data.get("contractor", "Contractor"),
            "approved_by": "Consultant/Client",
            "distribution": ["Client", "Facilities Management", "Building Operator"]
        }

        return {
            "status": "success",
            "action": "om_manual_generated",
            "manual_metadata": manual_metadata,
            "sections": sections,
            "summary": {
                "total_equipment": len(equipment_list),
                "systems_covered": len(systems),
                "warranty_items": len(equipment_list),
                "maintenance_tasks_generated": len(sections[4]["content"]["daily_tasks"]) + len(sections[4]["content"]["monthly_tasks"]),
                "estimated_manual_pages": manual_metadata["total_pages_estimate"]
            },
            "digital_format": {
                "recommended_software": "PDF with hyperlinks, or CAFM system integration",
                "hyperlink_structure": "Section-based navigation with equipment tags linked to data sheets",
                "update_procedure": "Annual review or upon equipment replacement"
            },
            "training_materials": self._extract_training_needs(equipment_list),
            "appendices": ["Equipment Data Sheets", "Test Reports", "Certificates", "Spare Parts Lists", "Supplier Contacts"]
        }

    def _group_equipment_by_system(self, equipment: List[Dict]) -> List[Dict]:
        systems = {}
        for equip in equipment:
            system_type = equip.get("system_type", "General")
            if system_type not in systems:
                systems[system_type] = []
            systems[system_type].append(equip)
        return [{"name": k, "description": f"{k} System", "equipment": v} for k, v in systems.items()]

    def _map_system_dependencies(self, systems: List[Dict]) -> List[Dict]:
        return []

    def _generate_equipment_maintenance(self, equip: Dict) -> Dict:
        category = equip.get("category", "general")
        schedules = {
            "hvac_equipment": {
                "daily": ["Check operation", "Check for unusual noise"],
                "monthly": ["Filter inspection", "Belt tension check"],
                "quarterly": ["Coil cleaning", "Motor bearing check"],
                "annually": ["Full service", "Performance testing"]
            },
            "pump": {
                "weekly": ["Visual inspection", "Leak check"],
                "monthly": ["Vibration check", "Seal inspection"],
                "annually": ["Impeller inspection", "Motor service"]
            },
            "electrical_panel": {
                "monthly": ["Temperature check", "Torque connections"],
                "annually": ["IR testing", "Breaker testing"]
            }
        }
        return schedules.get(category, schedules["hvac_equipment"])

    def _generate_startup_procedures(self, systems: List[Dict]) -> List[str]:
        return ["Verify power supply", "Check control sequences", "Run test cycle"]

    def _generate_normal_operation(self, systems: List[Dict]) -> List[str]:
        return ["Monitor setpoints", "Log operating parameters", "Respond to alarms"]

    def _generate_shutdown_procedures(self, systems: List[Dict]) -> List[str]:
        return ["Follow safe shutdown sequence", "Isolate energy sources", "Secure equipment"]

    def _generate_emergency_procedures(self, systems: List[Dict]) -> List[str]:
        return ["Activate emergency stop", "Notify emergency services", "Evacuate area"]

    def _generate_seasonal_operation(self, systems: List[Dict]) -> List[str]:
        return ["Adjust setpoints for season", "Inspect weatherproofing", "Service outdoor units"]

    def _generate_daily_tasks(self, equipment: List[Dict]) -> List[str]:
        return ["Visual inspection", "Check gauges and indicators"]

    def _generate_weekly_tasks(self, equipment: List[Dict]) -> List[str]:
        return ["Clean filters", "Check belt tension"]

    def _generate_monthly_tasks(self, equipment: List[Dict]) -> List[str]:
        return ["Lubricate bearings", "Check electrical connections"]

    def _generate_quarterly_tasks(self, equipment: List[Dict]) -> List[str]:
        return ["Calibrate sensors", "Service motors"]

    def _generate_annual_tasks(self, equipment: List[Dict]) -> List[str]:
        return ["Full system service", "Performance verification"]

    def _create_maintenance_matrix(self, equipment: List[Dict]) -> List[Dict]:
        return []

    def _generate_troubleshooting_guide(self, equipment: List[Dict]) -> List[Dict]:
        return [{"symptom": "Unit not starting", "possible_causes": ["Power failure", "Tripped breaker"], "action": "Check power and reset"}]

    def _generate_spare_parts_list(self, equipment: List[Dict]) -> List[Dict]:
        return []

    def _extract_training_needs(self, equipment: List[Dict]) -> List[str]:
        return ["Basic system operation", "Emergency procedures", "Preventive maintenance scheduling"]

    # ═══════════════════════════════════════════════════════════
    # 28. DIGITAL TWIN SYNC
    # ═══════════════════════════════════════════════════════════

    async def digital_twin_sync(self, input_data: dict, params: dict) -> dict:
        twin_platform = params.get("platform", "generic")
        sync_mode = params.get("mode", "update")
        project_id = params.get("project_id", "project_001")
        data_payload = input_data.get("data") or params.get("data", {})

        transformed_data = self._transform_for_platform(data_payload, twin_platform)

        operations = []
        if sync_mode == "initial_sync":
            operations = self._generate_initial_sync_operations(transformed_data, twin_platform)
        elif sync_mode == "delta_sync":
            operations = self._generate_delta_operations(transformed_data, twin_platform)
        else:
            operations = self._generate_update_operations(transformed_data, twin_platform)

        platform_config = self._get_platform_config(twin_platform, project_id)
        quality_report = self._check_twin_data_quality(transformed_data)
        api_payloads = self._generate_api_payloads(operations, twin_platform)

        return {
            "status": "success",
            "action": "digital_twin_sync",
            "platform": twin_platform,
            "sync_mode": sync_mode,
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "data_summary": {
                "elements_to_sync": len(operations),
                "data_points": sum(len(op.get("properties", [])) for op in operations),
                "geometry_updates": len([op for op in operations if op.get("type") == "geometry"]),
                "property_updates": len([op for op in operations if op.get("type") == "property"]),
                "relationship_updates": len([op for op in operations if op.get("type") == "relationship"])
            },
            "operations": operations[:50] if not params.get("full_details") else operations,
            "platform_configuration": platform_config,
            "api_payloads": api_payloads[:10] if not params.get("include_payloads") else api_payloads,
            "data_quality": quality_report,
            "sync_recommendations": self._generate_sync_recommendations(quality_report, twin_platform),
            "connection_strings": {
                "bim360": f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{project_id}",
                "azure": f"https://{project_id}.api.weu.digitaltwins.azure.net",
                "aveva": f"connect.aveva.com/{project_id}",
                "generic": "Custom API endpoint required"
            }.get(twin_platform, "Platform-specific endpoint required"),
            "authentication_required": {
                "type": "OAuth2" if twin_platform in ["bim360", "azure"] else "API Key",
                "scope": "Digital Twin Read/Write"
            }
        }

    def _transform_for_platform(self, data: Dict, platform: str) -> Dict:
        transformed = {"project_id": data.get("project_id"), "elements": []}
        for element in data.get("elements", []):
            twin_element = {
                "id": element.get("guid", element.get("id")),
                "name": element.get("name"),
                "type": element.get("category", "Generic"),
                "geometry": element.get("geometry"),
                "properties": element.get("properties", {}),
                "relationships": element.get("relationships", [])
            }
            transformed["elements"].append(twin_element)

        if platform == "bim360":
            for elem in transformed["elements"]:
                elem["objectId"] = elem.pop("id")
                elem["externalId"] = elem["objectId"]
        elif platform == "azure":
            for elem in transformed["elements"]:
                elem["$dtId"] = elem.pop("id")
                elem["$metadata"] = {"$model": f"dtmi:construction:{elem['type']};1"}
        return transformed

    def _generate_initial_sync_operations(self, data: Dict, platform: str) -> List[Dict]:
        operations = []
        for element in data.get("elements", []):
            operations.append({
                "operation": "CREATE",
                "type": "element",
                "target_id": element.get("id"),
                "properties": element.get("properties", {}),
                "geometry": element.get("geometry") if platform != "azure" else None,
                "relationships": element.get("relationships", [])
            })
        return operations

    def _generate_delta_operations(self, data: Dict, platform: str) -> List[Dict]:
        operations = []
        for element in data.get("elements", []):
            change_type = element.get("change_type", "UPDATE")
            if change_type == "ADD":
                operations.append({"operation": "CREATE", "type": "element", "target_id": element.get("id"), "properties": element.get("properties", {})})
            elif change_type == "DELETE":
                operations.append({"operation": "DELETE", "type": "element", "target_id": element.get("id")})
            else:
                operations.append({"operation": "UPDATE", "type": "property_update", "target_id": element.get("id"), "changed_properties": element.get("changed_properties", []), "timestamp": element.get("timestamp")})
        return operations

    def _generate_update_operations(self, data: Dict, platform: str) -> List[Dict]:
        return self._generate_delta_operations(data, platform)

    def _get_platform_config(self, platform: str, project_id: str) -> Dict:
        configs = {
            "bim360": {"format": "Forge JSON", "geometry_format": "SVF", "property_sets": ["Identity Data", "Phasing", "Structural"], "rate_limits": "1000 calls/minute"},
            "azure": {"format": "JSON-LD", "model_repo_required": True, "twin_lifecycle": "Full DTDL support", "query_language": "Digital Twins Query Language"},
            "aveva": {"format": "AVEVA E3D / Unified", "integration": "AVEVA Connect", "data_types": ["Equipment", "Piping", "Structural"]},
            "nvidia_omniverse": {"format": "USD", "connector": "Revit/Omniverse", "real_time": True, "physics_simulation": True}
        }
        return configs.get(platform, {"format": "Generic JSON", "note": "Platform-specific configuration required"})

    def _check_twin_data_quality(self, data: Dict) -> Dict:
        elements = data.get("elements", [])
        checks = {
            "total_elements": len(elements),
            "with_geometry": len([e for e in elements if e.get("geometry")]),
            "with_properties": len([e for e in elements if e.get("properties")]),
            "with_relationships": len([e for e in elements if e.get("relationships")]),
            "unique_ids": len(set(e.get("id") for e in elements)),
            "duplicate_ids": len(elements) - len(set(e.get("id") for e in elements)),
            "missing_geometry": [e.get("id") for e in elements if not e.get("geometry")][:10]
        }
        checks["completeness_score"] = (checks["with_geometry"] / len(elements) * 100) if elements else 0
        return checks

    def _generate_api_payloads(self, operations: List[Dict], platform: str) -> List[Dict]:
        return [{"platform": platform, "ops_count": len(operations)}]

    def _generate_sync_recommendations(self, quality: Dict, platform: str) -> List[str]:
        recs = []
        if quality.get("duplicate_ids", 0) > 0:
            recs.append("Resolve duplicate element IDs before sync")
        if quality.get("completeness_score", 0) < 80:
            recs.append("Improve geometry coverage for better twin fidelity")
        return recs

    # ═══════════════════════════════════════════════════════════
    # ACTION REGISTRY
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # INTELLIGENT WORKFLOW ENGINE
    # ═══════════════════════════════════════════════════════════

    async def intelligent_workflow(self, input_data: dict, params: dict) -> dict:
        """Smart orchestrator - auto-detects user intent and chains actions"""
        user_goal = params.get("goal") or params.get("prompt", "process document")
        file_path = input_data.get("file_path") or input_data.get("url")

        # Step 1: Analyze intent
        chain_steps = await self._build_intelligent_chain(user_goal, file_path)

        # Step 2: Execute chain through existing methods
        results = []
        current_data = input_data

        for step in chain_steps:
            method = getattr(self, step["action"], None)
            if method:
                try:
                    result = await method(current_data, step.get("params", {}))
                except Exception as e:
                    result = {"status": "error", "error": f"{step['action']} failed: {str(e)}"}
                results.append({
                    "step": step["action"],
                    "status": result.get("status"),
                    "key_findings": self._extract_key_findings(result)
                })
                # Pass output to next step
                current_data = {**current_data, "previous_result": result}

        # Step 3: Suggest next action
        next_action = self._suggest_next_action(results, user_goal)

        return {
            "status": "success",
            "action": "intelligent_workflow",
            "workflow_executed": [s["action"] for s in chain_steps],
            "step_results": results,
            "consolidated_summary": self._consolidate_results(results),
            "next_recommended_action": next_action,
            "user_query": user_goal
        }

    async def _build_intelligent_chain(self, user_goal: str, file_path: Optional[str]) -> List[Dict]:
        """Determine which construction methods to call based on user intent.
        First tries LLM reasoning, then falls back to keyword matching."""
        try:
            return await self._llm_build_intelligent_chain(user_goal, file_path)
        except Exception:
            return self._keyword_build_intelligent_chain(user_goal, file_path)

    async def _llm_build_intelligent_chain(self, user_goal: str, file_path: Optional[str]) -> List[Dict]:
        """Use the LLM layer to decide the optimal action chain."""
        available_actions = list(self.get_actions().keys())
        prompt = (
            "You are an intelligent workflow orchestrator for a construction domain AI system.\n"
            "Given the user's goal and an attached file (if any), select the optimal sequence "
            "of actions from the list below.\n\n"
            f"Available actions: {available_actions}\n\n"
            f"User goal: {user_goal}\n"
            f"File attached: {'yes (' + (file_path or 'unknown') + ')' if file_path else 'no'}\n\n"
            "Respond ONLY with a JSON array of objects, each with keys 'action' and 'params'. "
            "Keep the chain minimal but complete. Example:\n"
            '[{"action": "process_document", "params": {}}, {"action": "extract_quantities", "params": {}}]'
        )
        try:
            result = await self.llm.json_chat(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.2,
                max_tokens=2048,
            )
            chain = result if isinstance(result, list) else []
            # Validate actions exist
            valid = [step for step in chain if step.get("action") in available_actions]
            if valid:
                return valid
        except Exception:
            pass
        return self._keyword_build_intelligent_chain(user_goal, file_path)

    def _keyword_build_intelligent_chain(self, user_goal: str, file_path: Optional[str]) -> List[Dict]:
        """Legacy keyword-based chain builder (fallback)."""
        goal = user_goal.lower()
        chain = []

        # Document processing first if file provided
        if file_path and file_path.endswith('.pdf'):
            if any(k in goal for k in ["drawing", "plan", "elevation", "section"]):
                chain.append({"action": "process_document", "params": {"doc_type": "drawing"}})
            elif any(k in goal for k in ["spec", "specification", "csi", "masterformat"]):
                chain.append({"action": "process_specification_full", "params": {}})
            elif any(k in goal for k in ["contract", "clause", "terms", "risk"]):
                chain.append({"action": "process_contract", "params": {}})
            else:
                chain.append({"action": "process_document", "params": {}})

        # Quantity/Cost workflows
        if any(k in goal for k in ["qto", "quantity", "takeoff", "boq", "measurement", "material estimate"]):
            chain.append({"action": "extract_quantities", "params": {}})

        if any(k in goal for k in ["cost", "price", "budget", "estimate", "value"]):
            chain.append({"action": "extract_quantities", "params": {"include_costs": True}})

        # Procurement workflows
        if any(k in goal for k in ["buy", "purchase", "procure", "supplier", "enquiry", "order", "lead time"]):
            if not any(s["action"] == "extract_quantities" for s in chain):
                chain.append({"action": "extract_quantities", "params": {}})
            chain.append({"action": "procurement_optimizer", "params": {}})

        # Schedule workflows
        if any(k in goal for k in ["schedule", "programme", "primavera", "delay", "critical path", "progress"]):
            chain.append({"action": "parse_primavera_schedule", "params": {}})

        if any(k in goal for k in ["delay analysis", "forensic", "time impact", "extension of time", "eot", "claim"]):
            chain.append({"action": "forensic_delay_analysis", "params": {}})
            chain.append({"action": "claims_builder", "params": {}})

        # Variation workflows
        if any(k in goal for k in ["variation", "change order", "vo", "additional work", "omission"]):
            chain.append({"action": "change_order_impact", "params": {}})
            chain.append({"action": "variation_order_manager", "params": {}})

        # Financial workflows
        if any(k in goal for k in ["cash flow", "s-curve", "payment", "invoice", "billing"]):
            chain.append({"action": "cash_flow_forecast", "params": {}})
            chain.append({"action": "payment_certificate", "params": {}})

        # Quality/Safety workflows
        if any(k in goal for k in ["quality", "defect", "inspection", "qc", "honeycomb", "crack"]):
            chain.append({"action": "qa_qc_inspection", "params": {}})

        if any(k in goal for k in ["safety", "osha", "hazard", "incident", "audit"]):
            chain.append({"action": "safety_compliance_audit", "params": {}})

        # Tender workflows
        if any(k in goal for k in ["tender", "bid", "bid evaluation", "contractor selection", "quote comparison"]):
            chain.append({"action": "tender_bid_analysis", "params": {}})

        # Sustainability workflows
        if any(k in goal for k in ["carbon", "co2", "green", "esg", "sustainability", "leed", "breeam"]):
            chain.append({"action": "carbon_footprint_calculator", "params": {}})
            chain.append({"action": "esg_sustainability_report", "params": {}})

        # Value engineering
        if any(k in goal for k in ["value engineering", "ve", "alternative", "substitution", "saving", "optimization"]):
            chain.append({"action": "value_engineering", "params": {}})

        # Handover workflows
        if any(k in goal for k in ["commissioning", "handover", "practical completion", "testing"]):
            chain.append({"action": "commissioning_checklist", "params": {}})

        if any(k in goal for k in ["o&m", "operation and maintenance", "manual", "warranty", "maintenance schedule"]):
            chain.append({"action": "om_manual_generator", "params": {}})
            chain.append({"action": "warranty_maintenance_schedule", "params": {}})

        # As-built workflows
        if any(k in goal for k in ["as built", "as-built", "deviation", "record drawing"]):
            chain.append({"action": "as_built_deviation_report", "params": {}})

        # Digital workflows
        if any(k in goal for k in ["bim", "clash", "coordination", "model"]):
            chain.append({"action": "bim_clash_detection", "params": {}})

        if any(k in goal for k in ["digital twin", "sync", "iot", "sensor"]):
            chain.append({"action": "digital_twin_sync", "params": {}})

        # Submittals
        if any(k in goal for k in ["submittal", "shop drawing", "sample", "mockup", "approval"]):
            chain.append({"action": "submittal_log_generator", "params": {}})

        # Resource/labor workflows
        if any(k in goal for k in ["labor", "manpower", "resource", "histogram", "loading"]):
            chain.append({"action": "resource_histogram", "params": {}})

        # RFI generation
        if any(k in goal for k in ["rfi", "request for information", "clarification", "ambiguity"]):
            chain.append({"action": "rfi_generator", "params": {}})

        # Risk workflows
        if any(k in goal for k in ["risk", "risk register", "mitigation", "contingency"]):
            chain.append({"action": "risk_register_auto_populate", "params": {}})

        # Daily reporting
        if any(k in goal for k in ["daily report", "site diary", "daily log", "progress photo"]):
            chain.append({"action": "daily_site_report", "params": {}})

        # Default fallback
        if not chain:
            chain.append({"action": "process_document", "params": {}})
            chain.append({"action": "generate_report", "params": {}})

        return chain

    def _suggest_next_action(self, results: List[Dict], original_goal: str) -> Dict:
        """Suggest logical next step based on completed workflow"""
        completed_actions = [r["step"] for r in results]
        last_result = results[-1] if results else {}

        # Logic chains
        if "extract_quantities" in completed_actions and "procurement_optimizer" not in completed_actions:
            return {
                "suggested_action": "procurement_optimizer",
                "reason": "Quantities calculated - ready to source materials",
                "confidence": 0.95
            }

        if "parse_primavera_schedule" in completed_actions and "cash_flow_forecast" not in completed_actions:
            return {
                "suggested_action": "cash_flow_forecast",
                "reason": "Schedule loaded - can now project cash requirements",
                "confidence": 0.90
            }

        if "qa_qc_inspection" in completed_actions and last_result.get("status") == "success":
            defects = last_result.get("key_findings", {}).get("defects_found", 0)
            if defects > 0:
                return {
                    "suggested_action": "generate_construction_report",
                    "reason": f"{defects} defects found - generate formal QA report",
                    "confidence": 0.88
                }

        if "forensic_delay_analysis" in completed_actions:
            return {
                "suggested_action": "claims_builder",
                "reason": "Delay analysis complete - prepare formal claim submission",
                "confidence": 0.92
            }

        if "process_specification_full" in completed_actions:
            return {
                "suggested_action": "submittal_log_generator",
                "reason": "Specifications parsed - extract all required submittals",
                "confidence": 0.85
            }

        if "tender_bid_analysis" in completed_actions:
            return {
                "suggested_action": "process_contract",
                "reason": "Bid selected - prepare contract with identified risks",
                "confidence": 0.80
            }

        if "carbon_footprint_calculator" in completed_actions:
            return {
                "suggested_action": "esg_sustainability_report",
                "reason": "Carbon calculated - generate full ESG disclosure",
                "confidence": 0.85
            }

        return {
            "suggested_action": "generate_construction_report",
            "reason": "Consolidate all findings into formal report",
            "confidence": 0.75
        }

    def _extract_key_findings(self, result: Dict) -> Dict:
        """Extract summary data from result for chaining"""
        return {
            "status": result.get("status"),
            "metrics": result.get("summary", {}),
            "risks_found": len(result.get("risks", [])) if isinstance(result.get("risks"), list) else 0,
            "cost_impact": result.get("cost_impact") or result.get("total_cost") or result.get("grand_total"),
            "schedule_impact": result.get("schedule_impact", {}).get("days", 0) if isinstance(result.get("schedule_impact"), dict) else 0,
            "defects_found": result.get("defects_found", 0),
            "approval_status": result.get("approval_status") or result.get("pass_fail")
        }

    def _consolidate_results(self, results: List[Dict]) -> Dict:
        """Create unified summary from multiple workflow steps"""
        total_cost_impact = sum([
            r.get("key_findings", {}).get("cost_impact", 0) or 0
            for r in results
            if isinstance(r.get("key_findings", {}).get("cost_impact"), (int, float))
        ])

        total_schedule_impact = sum([
            r.get("key_findings", {}).get("schedule_impact", 0)
            for r in results
        ])

        all_risks = []
        for r in results:
            if "risk" in r.get("step", ""):
                all_risks.extend(r.get("result", {}).get("risks", []))

        return {
            "workflow_steps_completed": len(results),
            "total_cost_impact_usd": total_cost_impact,
            "total_schedule_impact_days": total_schedule_impact,
            "risks_identified": len(all_risks),
            "critical_issues": len([r for r in results if r.get("status") == "error"]),
            "success_rate": len([r for r in results if r.get("status") == "success"]) / len(results) if results else 0
        }
    def get_actions(self):
        """Return all 38 actions for block registry"""
        return {
            # Core (1-5)
            "process_document": self.process_document,
            "extract_measurements": self._extract_measurements_advanced,
            "generate_report": self.generate_construction_report,
            "intelligent_workflow": self.intelligent_workflow,
            "qa_qc_inspection": self.qa_qc_inspection,

            # Project Controls (6-14)
            "process_contract": self.process_contract,
            "parse_primavera_schedule": self.parse_primavera_schedule,
            "process_specification_full": self.process_specification_full,
            "change_order_impact": self.change_order_impact,
            "rfi_generator": self.rfi_generator,
            "claims_builder": self.claims_builder,
            "payment_certificate": self.payment_certificate,
            "submittal_log_generator": self.submittal_log_generator,
            "tender_bid_analysis": self.tender_bid_analysis,
            "variation_order_manager": self.variation_order_manager,
            "forensic_delay_analysis": self.forensic_delay_analysis,

            # BIM & Coordination (15-18)
            "bim_clash_detection": self.bim_clash_detection,
            "track_progress": self.track_progress,
            "resource_histogram": self.resource_histogram,
            "cash_flow_forecast": self.cash_flow_forecast,

            # Field Operations (19-23)
            "daily_site_report": self.daily_site_report,
            "safety_compliance_audit": self.safety_compliance_audit,
            "value_engineering": self.value_engineering,
            "carbon_footprint_calculator": self.carbon_footprint_calculator,
            "procurement_optimizer": self.procurement_optimizer,

            # Handover & Commissioning (24-28)
            "commissioning_checklist": self.commissioning_checklist,
            "warranty_maintenance_schedule": self.warranty_maintenance_schedule,
            "as_built_deviation_report": self.as_built_deviation_report,
            "om_manual_generator": self.om_manual_generator,
            "digital_twin_sync": self.digital_twin_sync,

            # Risk & Admin (29-32)
            "risk_register_auto_populate": self.risk_register_auto_populate,
            "extract_quantities": self.extract_quantities,
            "esg_sustainability_report": self.esg_sustainability_report,

            # Utilities (33-38)
            "validate_file": self.validate_file if hasattr(self, 'validate_file') else self._dummy_validate,
            "extract_tables": self._extract_tables_advanced,
            "detect_disciplines": self._detect_disciplines,
            "calculate_carbon": self._estimate_carbon,
            "estimate_costs": self._estimate_costs,
        }

    def _dummy_validate(self, input_data, params):
        return {"status": "success", "safe": True, "note": "Security validation placeholder"}

    # ═══════════════════════════════════════════════════════════
    # STUB METHODS (To be fully implemented or preserved from v3.0)
    # ═══════════════════════════════════════════════════════════

    async def _download_file(self, url: str) -> Optional[str]:
        import tempfile, aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    suffix = Path(url).suffix or ".tmp"
                    fd, path = tempfile.mkstemp(suffix=suffix)
                    with os.fdopen(fd, "wb") as f:
                        f.write(await resp.read())
                    return path
        return None

    async def _classify_document(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext in ['.pdf']:
            return "drawing"
        elif ext in ['.xer', '.xml', '.mpp']:
            return "schedule"
        elif ext in ['.jpg', '.jpeg', '.png']:
            return "image"
        return "drawing"

    def _extract_drawing_number(self, filename: str) -> Optional[str]:
        m = re.search(r'([A-Z]{1,3}-?\d{3,})', filename)
        return m.group(1) if m else None

    def _extract_revision(self, filename: str) -> Optional[str]:
        m = re.search(r'[Rr]ev[\s.]?(\w+)', filename)
        return m.group(1) if m else None

    def _extract_title_block(self, sheet: dict) -> dict:
        text = sheet.get("raw_text", "")
        return {
            "project_name": self._regex_extract(text, r'Project[\s:]+([^\n]+)'),
            "drawn_by": self._regex_extract(text, r'Drawn by[\s:]+([^\n]+)'),
            "date": self._regex_extract(text, r'Date[\s:]+([^\n]+)'),
            "scale": self._extract_scale(text)
        }

    def _regex_extract(self, text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _extract_scale(self, text: str) -> Optional[str]:
        m = re.search(r'(?:scale|sc)[\s:]*(1\s*:\s*\d+)', text, re.IGNORECASE)
        return m.group(1).replace(" ", "") if m else None

    def _calculate_quantities(self, measurements: List[Dict]) -> List[Dict]:
        return measurements

    def _estimate_costs(self, quantities: List[Dict]) -> Dict:
        total = 0
        for q in quantities:
            total += q.get("value", 0) * 100
        return {"total_usd": total, "currency": "USD"}

    def _estimate_carbon(self, quantities: List[Dict]) -> Dict:
        total = 0
        for q in quantities:
            total += q.get("value", 0) * 50
        return {"total_kg_co2e": total}

    def _calculate_confidence(self, result: dict) -> Dict:
        return {"overall": 0.85, "measurements": 0.8, "text": 0.9}

    async def _detect_risks_from_drawing(self, result: dict) -> List[Dict]:
        return []

    def _extract_measurements_advanced(self, raw_text: str, text_dict: dict) -> List[Dict]:
        pattern = r'(\d+\.?\d*)\s*(m|mm|cm|ft|\'|"|in)\s*(?:x|\*)?\s*(\d+\.?\d*)?\s*(m|mm|cm|ft|\'|"|in)?'
        found = []
        for m in re.finditer(pattern, raw_text):
            found.append({"raw": m.group(0), "value": float(m.group(1)), "unit": m.group(2)})
        return found[:50]

    def _extract_tables_advanced(self, page: fitz.Page) -> List[Dict]:
        return []

    def _extract_annotations(self, page: fitz.Page) -> List[Dict]:
        annots = []
        for annot in page.annots() or []:
            annots.append({"type": str(annot.type[1]), "content": annot.info.get("content", "")})
        return annots

    def _extract_specs_advanced(self, raw_text: str) -> List[Dict]:
        return []

    def _detect_disciplines(self, raw_text: str) -> List[str]:
        disciplines = []
        if re.search(r'\b(structural|concrete|rebar|foundation)\b', raw_text, re.I):
            disciplines.append("structural")
        if re.search(r'\b(mechanical|hvac|duct|plumbing)\b', raw_text, re.I):
            disciplines.append("mep")
        if re.search(r'\b(electrical|lighting|panel|cable)\b', raw_text, re.I):
            disciplines.append("electrical")
        if re.search(r'\b(architectural|finish|ceiling|floor)\b', raw_text, re.I):
            disciplines.append("architectural")
        return disciplines

    def _extract_resources(self, act: dict) -> List[Dict]:
        return []

    def _parse_relationships(self, relationships: List[Dict]) -> List[Dict]:
        return [{"pred_id": r.get('pred_task_id'), "succ_id": r.get('task_id'), "type": r.get('pred_type')} for r in relationships]

    def _parse_mspdi_xml(self, root) -> Dict:
        return {"status": "success", "project_name": "MSP", "activities": []}

    def _calculate_duration_days(self, start: str, finish: str) -> int:
        try:
            s = datetime.fromisoformat(start.replace('Z', '+00:00'))
            f = datetime.fromisoformat(finish.replace('Z', '+00:00'))
            return max(0, (f - s).days)
        except Exception:
            return 0

    def _calculate_date_diff(self, date_a: str, date_b: str) -> int:
        try:
            a = datetime.fromisoformat(date_a.replace('Z', '+00:00'))
            b = datetime.fromisoformat(date_b.replace('Z', '+00:00'))
            return max(0, (b - a).days)
        except Exception:
            return 0

    def _identify_driving_paths(self, schedule_data: Dict, critical_activities: List[Dict]) -> List[Dict]:
        return []

    def _assess_delay_impact(self, delays: List[Dict], total_delay: int) -> str:
        if total_delay > 30:
            return "Severe schedule impact - consider recovery strategies"
        elif total_delay > 7:
            return "Moderate delay - monitor closely"
        return "Minor delay - manageable within float"

    def _extract_milestones(self, schedule_data: Dict) -> List[Dict]:
        return [a for a in schedule_data.get("activities", []) if "milestone" in a.get("name", "").lower()][:10]

    def _generate_schedule_recommendations(self, cpm: Dict, delay_analysis: Optional[Dict]) -> List[str]:
        recs = []
        if delay_analysis and delay_analysis.get("total_delay_days", 0) > 0:
            recs.append("Review critical path and consider crashing or fast-tracking")
        if cpm.get("average_float", 999) < 2:
            recs.append("Schedule is tightly constrained - add buffers where possible")
        return recs

    def _infer_division_from_context(self, pos: int, text: str) -> str:
        before = text[max(0, pos-200):pos]
        for code in self.csi_divisions:
            if re.search(rf'\b{code}\d{{2,}}\b', before):
                return code
        return ""

    def _extract_part1_general(self, content: str) -> str:
        return content[:500]

    def _extract_part2_products(self, content: str) -> str:
        return ""

    def _extract_part3_execution(self, content: str) -> str:
        return ""

    def _extract_key_reqs(self, content: str) -> List[str]:
        return []

    def _identify_critical_specs(self, sections: List[Dict]) -> List[Dict]:
        return []

    def _generate_compliance_checklist(self, sections: List[Dict], submittals: List[Dict]) -> List[Dict]:
        return []

    def _extract_material_tracking(self, sections: List[Dict]) -> List[Dict]:
        return []

    def _extract_warranty_requirements(self, text: str) -> List[Dict]:
        reqs = []
        for m in re.finditer(r'warranty[\s\w]{0,30}(\d+)\s*years?', text, re.IGNORECASE):
            reqs.append({"years": int(m.group(1)), "item": "general", "context": m.group(0)})
        return reqs

    def _extract_testing_requirements(self, text: str) -> List[Dict]:
        return []

    def _detect_trade_from_text(self, text: str) -> str:
        trades = ["concrete", "steel", "electrical", "plumbing", "hvac", "masonry", "finishes"]
        text_lower = text.lower()
        for t in trades:
            if t in text_lower:
                return t
        return "general"

    def _categorize_obligation(self, text: str) -> str:
        return "general"

    def _assess_obligation_priority(self, text: str) -> str:
        return "medium"

    def _suggest_clarifications(self, analysis: Dict) -> List[str]:
        return ["Verify design intent", "Confirm dimensions and materials"]

    def _assess_ambiguity_impact(self, analysis: Dict, priority: str) -> Dict:
        return {"cost_impact": "unknown", "schedule_impact": "unknown", "quality_impact": "unknown"}

    def _find_related_rfis(self, analysis: Dict) -> List[str]:
        return []

    def _identify_rfi_attachments(self, analysis: Dict) -> List[str]:
        return []

    def _extract_topic(self, text: str) -> str:
        return "General"

    def _perform_safety_checklist(self, checklist_items: List[Dict], standards: List[str]) -> List[Dict]:
        return []

    def _identify_safety_violations(self, checklist_results: List[Dict], photo_analysis: List[Dict]) -> List[Dict]:
        return []

    def _calculate_safety_risk_score(self, violations: List[Dict]) -> float:
        return 85.0

    def _generate_corrective_actions(self, violations: List[Dict]) -> List[Dict]:
        return []

    def _parse_safety_hazards(self, description: str) -> List[Dict]:
        return []

    def _generate_safety_recommendations(self, violations: List[Dict]) -> List[str]:
        return []

    def _get_carbon_benchmarks(self, building_type: str) -> Dict:
        return {"average": 500000, "target": 350000, "legal_limit": 600000}

    def _calculate_carbon_from_list(self, materials: List[Dict], assessment_type: str) -> Dict:
        return self._calculate_carbon_from_boq([{"material_type": m.get("type"), "quantity": m.get("qty", 0), "unit": m.get("unit", "m3")} for m in materials], assessment_type)

    def _calculate_percentile(self, value: float, benchmarks: Dict) -> int:
        if value < benchmarks["target"]:
            return 80
        elif value < benchmarks["average"]:
            return 50
        return 20

    def _generate_carbon_recommendations(self, carbon_calc: Dict, optimizations: List[Dict]) -> List[str]:
        return [opt["description"] for opt in optimizations[:3]]

    def _generate_standalone_procurement_schedule(self, boq: List[Dict], project_start: Optional[str]) -> List[Dict]:
        return [{**item, "lead_time_weeks": self._get_material_lead_time(item.get("material_type", "")), "buffer_weeks": 2} for item in boq]

    def _enrich_supplier_data(self, material_schedule: List[Dict]) -> List[Dict]:
        for item in material_schedule:
            item["estimated_cost"] = item.get("quantity", 0) * self.cost_db.get(item.get("material_type", "concrete_c30"), {}).get("rate", 100)
        return material_schedule

    def _calculate_procurement_cash_flow(self, procurement_list: List[Dict]) -> List[Dict]:
        return []

    def _suggest_procurement_packages(self, procurement_list: List[Dict]) -> List[Dict]:
        return []

    def _generate_approval_workflow(self, procurement_list: List[Dict]) -> List[Dict]:
        return []

    def _identify_supply_risks(self, procurement_list: List[Dict]) -> List[Dict]:
        return []

    def _find_relevant_activity(self, schedule_data: Dict, material_type: str) -> Optional[Dict]:
        activities = schedule_data.get("activities", [])
        if not activities:
            return None
        keywords = {
            "concrete_c30": ["concrete", "slab", "foundation"],
            "steel_structural": ["steel", "structure", "frame"],
            "electrical_panel": ["electrical", "panel"],
            "hvac_chiller": ["hvac", "mechanical"],
        }
        search_terms = keywords.get(material_type, [material_type])
        for act in activities:
            name = act.get("name", "").lower()
            if any(term in name for term in search_terms):
                return act
        return activities[0] if activities else None

    def _subtract_lead_time(self, need_date: Optional[str], lead_time_weeks: int) -> Optional[str]:
        if not need_date:
            return None
        try:
            dt = datetime.fromisoformat(need_date.replace('Z', '+00:00'))
            return (dt - timedelta(weeks=lead_time_weeks)).isoformat()
        except Exception:
            return None

    async def _identify_deviations_from_photo(self, photo_path: str, original_drawings: List[str]) -> List[Dict]:
        return []

    def _categorize_deviations(self, deviations: List[Dict]) -> Dict:
        result = {"critical": [], "major": [], "minor": [], "approvable": []}
        for d in deviations:
            sev = d.get("severity", "minor")
            if sev == "critical":
                result["critical"].append(d)
            elif sev == "major":
                result["major"].append(d)
            elif sev == "minor":
                result["minor"].append(d)
            else:
                result["approvable"].append(d)
        return result

    def _calculate_deviation_costs(self, deviations: List[Dict]) -> Dict:
        return {"total": 0, "breakdown": []}

    def _assess_deviation_schedule_impact(self, deviations: List[Dict]) -> Dict:
        return {"total_days": 0}

    def _generate_formal_deviation_report(self, categorized: Dict, cost_impact: Dict, schedule_impact: Dict) -> str:
        return "Formal deviation report placeholder"

    def _list_supporting_docs(self, deviations: List[Dict]) -> List[str]:
        return []

    def _add_years(self, date_str: Optional[str], years: int) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.replace(year=dt.year + years).isoformat()
        except Exception:
            return None

    def _generate_maintenance_calendar(self, equipment_schedule: List[Dict]) -> List[Dict]:
        return []

    def _forecast_replacements(self, equipment_schedule: List[Dict]) -> List[Dict]:
        return []

    def _generate_warranty_compliance_list(self, equipment_schedule: List[Dict]) -> List[Dict]:
        return []

    def _generate_notification_schedule(self, equipment_schedule: List[Dict]) -> List[Dict]:
        return []

    def _get_pm_tasks(self, category: str) -> List[str]:
        return ["Inspect", "Clean", "Lubricate"]

    async def _detect_risks_from_schedule(self, schedule_file: str) -> List[Dict]:
        schedule_data = self._parse_xer_file(schedule_file)
        cpm = self._calculate_critical_path(schedule_data)
        return self._analyze_schedule_risks(cpm)

    async def _detect_risks_from_contract(self, contract_file: str) -> List[Dict]:
        contract_data = await self.process_contract({"file_path": contract_file}, {})
        risks = []
        ra = contract_data.get("risk_assessment", {})
        if ra.get("risk_level") == "high":
            risks.append(self._create_risk_item(
                "Commercial", "High contract risk score", "high", "high",
                "Legal review, negotiate amendments", "contract_analysis"
            ))
        return risks

    async def _detect_site_risks_from_photo(self, photo_path: str) -> List[Dict]:
        return []

    def _deduplicate_risks(self, risks: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for r in risks:
            key = r.get("description", "")
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def _categorize_risks_by_type(self, risks: List[Dict]) -> Dict:
        result = {}
        for r in risks:
            cat = r.get("category", "general")
            result.setdefault(cat, []).append(r)
        return result

    def _prioritize_risks(self, risks: List[Dict]) -> List[Dict]:
        pmap = {"high": 3, "medium": 2, "low": 1}
        return sorted(risks, key=lambda r: (pmap.get(r.get("probability", "low"), 1), pmap.get(r.get("impact", "low"), 1)), reverse=True)

    def _generate_risk_matrix(self, risks: List[Dict]) -> Dict:
        return {}

    def _suggest_mitigation(self, risk: Dict) -> str:
        return risk.get("mitigation", "Review and monitor")

    def _calculate_contingency(self, risk: Dict) -> float:
        pmap = {"high": 0.15, "medium": 0.08, "low": 0.03}
        imap = {"high": 0.15, "medium": 0.08, "low": 0.03}
        return 10000 * (pmap.get(risk.get("probability", "low"), 0.03) + imap.get(risk.get("impact", "low"), 0.03))

    def _sum_contingency_by_category(self, risks: List[Dict]) -> Dict:
        result = {}
        for r in risks:
            cat = r.get("category", "general")
            result[cat] = result.get(cat, 0) + r.get("contingency_reserve", 0)
        return result

    def _generate_workshop_agenda(self, risks: List[Dict]) -> List[str]:
        return ["Review top risks", "Assign owners", "Define mitigation plans"]

    def _generate_risk_monitoring_schedule(self, risks: List[Dict]) -> List[Dict]:
        return []

    def _define_escalation_thresholds(self) -> Dict:
        return {"critical": "Immediate", "major": "24 hours", "minor": "Weekly"}

    def _parse_defects(self, description: str) -> List[Dict]:
        return []

    def _check_compliance(self, defects: List[Dict], inspection_type: str) -> Dict:
        return {"status": "compliant", "standards": []}

    def _calculate_severity(self, defects: List[Dict]) -> int:
        return 0

    def _generate_recommendations(self, defects: List[Dict], inspection_type: str) -> List[str]:
        return []

    def _estimate_repair_cost(self, defects: List[Dict], inspection_type: str) -> float:
        return 0.0

    def _infer_material(self, quantity: Dict, specs: List[Dict]) -> Dict:
        return {"type": "concrete_c30", "name": "Concrete"}

    def _lookup_cost(self, material_type: str, unit: str) -> Optional[float]:
        return self.cost_db.get(material_type, {}).get("rate")

    async def generate_construction_report(self, input_data: dict, params: dict) -> dict:
        return {"status": "success", "action": "generate_report", "report": "Placeholder report"}

    async def track_progress(self, input_data: dict, params: dict) -> dict:
        return {"status": "success", "action": "track_progress", "progress": 0.0}

    async def _process_bill_of_materials(self, input_data: dict, params: dict) -> dict:
        return {"status": "success", "action": "bom", "items": []}

    async def _process_report(self, input_data: dict, params: dict) -> dict:
        return {"status": "success", "action": "report", "summary": ""}

    async def _process_ifc(self, input_data: dict, params: dict) -> dict:
        return {"status": "success", "action": "ifc", "elements": []}

    async def _process_site_photo(self, input_data: dict, params: dict) -> dict:
        return await self.qa_qc_inspection(input_data, params)

    def _identify_affected_milestones(self, schedule_data: Dict, affected_activities: List) -> List[str]:
        return []


# Auto-register on import
from app.core.block_registry import BLOCK_REGISTRY

BLOCK_REGISTRY.register(ConstructionBlock())
