"""
Clash Reporting - PDF/Excel Clash Report Generation
Generates professional clash detection reports for coordination meetings.
"""
import io
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .clash_detection import ClashResult, Clash, ClashType, ClashSeverity, ClashStatus

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report formats."""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    JSON = "json"
    BCF = "bcf"


@dataclass
class ReportTemplate:
    """Template for clash reports."""
    name: str
    include_screenshots: bool = True
    include_3d_view: bool = False
    include_statistics: bool = True
    include_recommendations: bool = True
    group_by: str = "severity"  # severity, type, discipline, level
    sort_by: str = "severity"   # severity, date, element_name
    logo_url: Optional[str] = None
    company_name: str = "Cerebrum AI"
    project_name: Optional[str] = None


@dataclass
class ClashReport:
    """Generated clash report."""
    id: str
    title: str
    generated_at: datetime
    clash_result: ClashResult
    template: ReportTemplate
    content: bytes
    format: ReportFormat
    file_size: int
    page_count: Optional[int] = None


class PDFReportGenerator:
    """Generates PDF clash reports."""
    
    def __init__(self):
        self.styles = self._define_styles()
    
    def _define_styles(self) -> Dict[str, Any]:
        """Define PDF styles."""
        # Placeholder - would use reportlab
        return {
            'title': {'fontSize': 24, 'spaceAfter': 30},
            'heading1': {'fontSize': 18, 'spaceAfter': 12},
            'heading2': {'fontSize': 14, 'spaceAfter': 10},
            'normal': {'fontSize': 10, 'spaceAfter': 6},
            'table_header': {'fontSize': 10, 'textColor': 'white', 'backColor': '#2E5090'},
            'critical': {'textColor': '#DC2626', 'backColor': '#FEE2E2'},
            'high': {'textColor': '#EA580C', 'backColor': '#FFEDD5'},
            'medium': {'textColor': '#CA8A04', 'backColor': '#FEF9C3'},
            'low': {'textColor': '#16A34A', 'backColor': '#DCFCE7'},
        }
    
    def generate(self, clash_result: ClashResult, 
                template: ReportTemplate) -> bytes:
        """Generate PDF report."""
        # Placeholder - would use reportlab to generate actual PDF
        logger.info(f"Generating PDF report for {clash_result.clash_count} clashes")
        
        # Create report content structure
        content = self._build_report_content(clash_result, template)
        
        # For now, return placeholder content
        # In production, use reportlab to generate actual PDF
        pdf_content = f"""
CLASH DETECTION REPORT
======================

Project: {template.project_name or 'N/A'}
Generated: {clash_result.run_at.isoformat()}
Report ID: {clash_result.id}

SUMMARY
-------
Total Clashes: {clash_result.clash_count}
Elements Checked: {clash_result.total_elements_checked}
Pairs Checked: {clash_result.total_pairs_checked}
Execution Time: {clash_result.execution_time_ms:.2f} ms

BY SEVERITY
-----------
"""
        for severity, count in clash_result.clashes_by_severity.items():
            pdf_content += f"  {severity.upper()}: {count}\n"
        
        pdf_content += "\nBY TYPE\n-------\n"
        for clash_type, count in clash_result.clashes_by_type.items():
            pdf_content += f"  {clash_type}: {count}\n"
        
        pdf_content += "\nCLASH DETAILS\n-------------\n"
        for clash in clash_result.clashes:
            pdf_content += f"""
Clash ID: {clash.id}
Type: {clash.clash_type.value}
Severity: {clash.severity.value}
Status: {clash.status.value}

Element A: {clash.element_a.name} ({clash.element_a.element_type.value})
Discipline: {clash.element_a.discipline.value}

Element B: {clash.element_b.name} ({clash.element_b.element_type.value})
Discipline: {clash.element_b.discipline.value}

Intersection Volume: {clash.intersection_volume:.6f} m³
Penetration Depth: {clash.penetration_depth:.4f} m
Location: ({clash.intersection_center.x:.3f}, {clash.intersection_center.y:.3f}, {clash.intersection_center.z:.3f})

---
"""
        
        return pdf_content.encode('utf-8')
    
    def _build_report_content(self, clash_result: ClashResult,
                             template: ReportTemplate) -> Dict[str, Any]:
        """Build report content structure."""
        content = {
            'title': f"Clash Detection Report - {template.project_name or 'Project'}",
            'generated_at': clash_result.run_at.isoformat(),
            'summary': {
                'total_clashes': clash_result.clash_count,
                'elements_checked': clash_result.total_elements_checked,
                'pairs_checked': clash_result.total_pairs_checked,
                'execution_time_ms': clash_result.execution_time_ms,
            },
            'statistics': {
                'by_severity': clash_result.clashes_by_severity,
                'by_type': clash_result.clashes_by_type,
            },
            'clashes': [c.to_dict() for c in clash_result.clashes]
        }
        return content


class ExcelReportGenerator:
    """Generates Excel clash reports."""
    
    def __init__(self):
        self.column_widths = {
            'A': 15,  # Clash ID
            'B': 12,  # Type
            'C': 10,  # Severity
            'D': 10,  # Status
            'E': 25,  # Element A
            'F': 15,  # Discipline A
            'G': 25,  # Element B
            'H': 15,  # Discipline B
            'I': 15,  # Volume
            'J': 15,  # Penetration
            'K': 20,  # Location
            'L': 20,  # Created At
        }
    
    def generate(self, clash_result: ClashResult,
                template: ReportTemplate) -> bytes:
        """Generate Excel report."""
        logger.info(f"Generating Excel report for {clash_result.clash_count} clashes")
        
        # Placeholder - would use openpyxl
        # For now, return CSV-like content
        lines = [
            "Clash ID,Type,Severity,Status,Element A,Discipline A,Element B,Discipline B,Volume (m³),Penetration (m),Location,Created At"
        ]
        
        for clash in clash_result.clashes:
            location = f"({clash.intersection_center.x:.2f}, {clash.intersection_center.y:.2f}, {clash.intersection_center.z:.2f})"
            lines.append(
                f'"{clash.id}","{clash.clash_type.value}","{clash.severity.value}",'
                f'"{clash.status.value}","{clash.element_a.name}","{clash.element_a.discipline.value}",'
                f'"{clash.element_b.name}","{clash.element_b.discipline.value}",'
                f'{clash.intersection_volume:.6f},{clash.penetration_depth:.4f},'
                f'"{location}","{clash.created_at.isoformat()}"'
            )
        
        return '\n'.join(lines).encode('utf-8')
    
    def generate_multi_sheet(self, clash_result: ClashResult,
                            template: ReportTemplate) -> bytes:
        """Generate multi-sheet Excel report."""
        # Would create multiple sheets:
        # - Summary
        # - All Clashes
        # - By Severity
        # - By Type
        # - By Discipline
        return self.generate(clash_result, template)


class HTMLReportGenerator:
    """Generates HTML clash reports."""
    
    def generate(self, clash_result: ClashResult,
                template: ReportTemplate) -> bytes:
        """Generate HTML report."""
        logger.info(f"Generating HTML report for {clash_result.clash_count} clashes")
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Clash Detection Report - {template.project_name or 'Project'}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2E5090; border-bottom: 3px solid #2E5090; padding-bottom: 10px; }}
        h2 {{ color: #4A6FA5; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card .number {{ font-size: 36px; font-weight: bold; color: #2E5090; }}
        .summary-card .label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #2E5090; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .severity-critical {{ color: #DC2626; font-weight: bold; }}
        .severity-high {{ color: #EA580C; font-weight: bold; }}
        .severity-medium {{ color: #CA8A04; }}
        .severity-low {{ color: #16A34A; }}
        .status-new {{ background: #FEE2E2; padding: 4px 8px; border-radius: 4px; }}
        .status-resolved {{ background: #DCFCE7; padding: 4px 8px; border-radius: 4px; }}
        .status-ignored {{ background: #E5E7EB; padding: 4px 8px; border-radius: 4px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Clash Detection Report</h1>
        <p><strong>Project:</strong> {template.project_name or 'N/A'}</p>
        <p><strong>Generated:</strong> {clash_result.run_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Report ID:</strong> {clash_result.id}</p>
        
        <h2>Summary</h2>
        <div class="summary">
            <div class="summary-card">
                <div class="number">{clash_result.clash_count}</div>
                <div class="label">Total Clashes</div>
            </div>
            <div class="summary-card">
                <div class="number">{clash_result.total_elements_checked}</div>
                <div class="label">Elements Checked</div>
            </div>
            <div class="summary-card">
                <div class="number">{clash_result.total_pairs_checked:,}</div>
                <div class="label">Pairs Checked</div>
            </div>
            <div class="summary-card">
                <div class="number">{clash_result.execution_time_ms:.0f}</div>
                <div class="label">Execution Time (ms)</div>
            </div>
        </div>
        
        <h2>Clashes by Severity</h2>
        <table>
            <tr><th>Severity</th><th>Count</th></tr>
"""
        
        for severity, count in clash_result.clashes_by_severity.items():
            html += f'            <tr><td class="severity-{severity.lower()}">{severity.upper()}</td><td>{count}</td></tr>\n'
        
        html += """        </table>
        
        <h2>Clash Details</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Element A</th>
                <th>Discipline A</th>
                <th>Element B</th>
                <th>Discipline B</th>
            </tr>
"""
        
        for clash in clash_result.clashes:
            html += f"""            <tr>
                <td>{clash.id[:8]}</td>
                <td>{clash.clash_type.value}</td>
                <td class="severity-{clash.severity.value.lower()}">{clash.severity.value.upper()}</td>
                <td><span class="status-{clash.status.value.lower()}">{clash.status.value.upper()}</span></td>
                <td>{clash.element_a.name}</td>
                <td>{clash.element_a.discipline.value}</td>
                <td>{clash.element_b.name}</td>
                <td>{clash.element_b.discipline.value}</td>
            </tr>
"""
        
        html += f"""        </table>
        
        <div class="footer">
            <p>Generated by Cerebrum AI - Clash Detection System</p>
            <p>Report ID: {clash_result.id}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html.encode('utf-8')


class ReportManager:
    """Manages clash report generation and storage."""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.generators = {
            ReportFormat.PDF: PDFReportGenerator(),
            ReportFormat.EXCEL: ExcelReportGenerator(),
            ReportFormat.HTML: HTMLReportGenerator(),
        }
    
    def generate_report(self, clash_result: ClashResult,
                       format: ReportFormat,
                       template: Optional[ReportTemplate] = None) -> ClashReport:
        """Generate a clash report in specified format."""
        template = template or ReportTemplate(name="default")
        
        generator = self.generators.get(format)
        if not generator:
            raise ValueError(f"Unsupported format: {format.value}")
        
        content = generator.generate(clash_result, template)
        
        report = ClashReport(
            id=f"report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            title=f"Clash Report - {template.project_name or 'Project'}",
            generated_at=datetime.utcnow(),
            clash_result=clash_result,
            template=template,
            content=content,
            format=format,
            file_size=len(content)
        )
        
        # Store report
        if self.storage:
            self.storage.store_report(report)
        
        logger.info(f"Generated {format.value} report: {report.id}")
        return report
    
    def generate_all_formats(self, clash_result: ClashResult,
                            template: Optional[ReportTemplate] = None) -> Dict[ReportFormat, ClashReport]:
        """Generate reports in all supported formats."""
        reports = {}
        for format in [ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.HTML]:
            try:
                reports[format] = self.generate_report(clash_result, format, template)
            except Exception as e:
                logger.error(f"Failed to generate {format.value} report: {e}")
        return reports
    
    def get_report(self, report_id: str) -> Optional[ClashReport]:
        """Retrieve a stored report."""
        if self.storage:
            return self.storage.get_report(report_id)
        return None
    
    def list_reports(self, project_id: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """List available reports."""
        if self.storage:
            return self.storage.list_reports(project_id, limit)
        return []


# Convenience functions
def generate_quick_report(clash_result: ClashResult, 
                         format: ReportFormat = ReportFormat.HTML) -> bytes:
    """Generate a quick clash report."""
    manager = ReportManager()
    report = manager.generate_report(clash_result, format)
    return report.content
