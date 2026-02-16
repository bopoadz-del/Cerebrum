"""
As-Built Documentation - Laser Scan Point Cloud Integration
Capture and compare as-built conditions
"""
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4
import numpy as np

logger = logging.getLogger(__name__)


class ScanFormat(Enum):
    """Point cloud formats"""
    E57 = "e57"
    LAS = "las"
    LAZ = "laz"
    PLY = "ply"
    PTS = "pts"
    XYZ = "xyz"
    RCP = "rcp"  # Autodesk Recap


class DeviationStatus(Enum):
    """Deviation analysis status"""
    WITHIN_TOLERANCE = "within_tolerance"
    MINOR_DEVIATION = "minor_deviation"
    MAJOR_DEVIATION = "major_deviation"
    CRITICAL_DEVIATION = "critical_deviation"


@dataclass
class PointCloud:
    """Point cloud data"""
    scan_id: str
    name: str
    format: ScanFormat
    file_path: str
    point_count: int
    bounding_box: Dict[str, List[float]]
    coordinate_system: str
    scan_date: datetime
    scanned_by: str
    scanner_model: str
    scan_resolution_mm: float
    accuracy_mm: float
    registered: bool = False
    registration_error_mm: Optional[float] = None
    colorized: bool = False
    intensity_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanRegistration:
    """Scan registration information"""
    registration_id: str
    scan_ids: List[str]
    target_model_id: str
    transformation_matrix: List[List[float]]
    registration_date: datetime
    registered_by: str
    error_rms_mm: float
    control_points_used: int
    is_valid: bool = True


@dataclass
class DeviationAnalysis:
    """Deviation analysis result"""
    analysis_id: str
    scan_id: str
    model_id: str
    analyzed_at: datetime
    tolerance_mm: float
    total_points_analyzed: int
    points_within_tolerance: int
    mean_deviation_mm: float
    max_deviation_mm: float
    std_deviation_mm: float
    deviation_histogram: Dict[str, int] = field(default_factory=dict)
    hotspot_regions: List[Dict] = field(default_factory=list)
    report_path: Optional[str] = None


@dataclass
class AsBuiltComparison:
    """As-built vs design comparison"""
    comparison_id: str
    scan_id: str
    design_model_id: str
    compared_at: datetime
    overall_status: DeviationStatus
    completeness_percent: float
    element_comparisons: List[Dict] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    extra_elements: List[str] = field(default_factory=list)


class PointCloudManager:
    """Manages point cloud data"""
    
    def __init__(self):
        self._point_clouds: Dict[str, PointCloud] = {}
        self._registrations: Dict[str, ScanRegistration] = {}
    
    def import_scan(self, name: str,
                    file_path: str,
                    scan_format: ScanFormat,
                    scan_date: datetime,
                    scanned_by: str,
                    scanner_model: str = "",
                    metadata: Dict = None) -> PointCloud:
        """Import point cloud scan"""
        # In practice, this would parse the file to get point count and bounds
        scan = PointCloud(
            scan_id=str(uuid4()),
            name=name,
            format=scan_format,
            file_path=file_path,
            point_count=0,  # Would be populated from file
            bounding_box={'min': [0, 0, 0], 'max': [0, 0, 0]},
            coordinate_system="local",
            scan_date=scan_date,
            scanned_by=scanned_by,
            scanner_model=scanner_model,
            scan_resolution_mm=5.0,
            accuracy_mm=2.0,
            metadata=metadata or {}
        )
        
        self._point_clouds[scan.scan_id] = scan
        
        logger.info(f"Imported point cloud: {scan.scan_id}")
        
        return scan
    
    def register_scan(self, scan_id: str,
                      target_model_id: str,
                      control_points: List[Tuple],
                      registered_by: str) -> ScanRegistration:
        """Register scan to design model"""
        scan = self._point_clouds.get(scan_id)
        if not scan:
            raise ValueError(f"Scan not found: {scan_id}")
        
        # Calculate registration transformation
        # This would use actual registration algorithm (ICP, etc.)
        transformation = self._calculate_registration(control_points)
        
        # Calculate registration error
        error_rms = self._calculate_registration_error(control_points, transformation)
        
        registration = ScanRegistration(
            registration_id=str(uuid4()),
            scan_ids=[scan_id],
            target_model_id=target_model_id,
            transformation_matrix=transformation.tolist(),
            registration_date=datetime.utcnow(),
            registered_by=registered_by,
            error_rms_mm=error_rms,
            control_points_used=len(control_points)
        )
        
        self._registrations[registration.registration_id] = registration
        
        # Update scan
        scan.registered = True
        scan.registration_error_mm = error_rms
        
        logger.info(f"Registered scan: {scan_id} to model: {target_model_id}")
        
        return registration
    
    def _calculate_registration(self, control_points: List[Tuple]) -> np.ndarray:
        """Calculate registration transformation"""
        # Simplified - would use actual registration algorithm
        return np.eye(4)
    
    def _calculate_registration_error(self, control_points: List[Tuple],
                                       transformation: np.ndarray) -> float:
        """Calculate RMS registration error"""
        # Simplified - would calculate actual error
        return 2.5
    
    def get_scan(self, scan_id: str) -> Optional[PointCloud]:
        """Get scan by ID"""
        return self._point_clouds.get(scan_id)
    
    def get_scans_for_model(self, model_id: str) -> List[PointCloud]:
        """Get all scans registered to a model"""
        scan_ids = set()
        
        for reg in self._registrations.values():
            if reg.target_model_id == model_id:
                scan_ids.update(reg.scan_ids)
        
        return [self._point_clouds[sid] for sid in scan_ids if sid in self._point_clouds]


class DeviationAnalyzer:
    """Analyzes deviations between scan and design"""
    
    def __init__(self):
        self._analyses: Dict[str, DeviationAnalysis] = {}
        self._tolerance_levels = {
            'within': 10.0,      # mm
            'minor': 25.0,
            'major': 50.0,
            'critical': float('inf')
        }
    
    def analyze_deviations(self, scan_id: str,
                           model_id: str,
                           tolerance_mm: float = 10.0) -> DeviationAnalysis:
        """Analyze deviations between scan and design model"""
        # This would perform actual deviation analysis
        # For now, return placeholder
        
        analysis = DeviationAnalysis(
            analysis_id=str(uuid4()),
            scan_id=scan_id,
            model_id=model_id,
            analyzed_at=datetime.utcnow(),
            tolerance_mm=tolerance_mm,
            total_points_analyzed=1000000,
            points_within_tolerance=950000,
            mean_deviation_mm=5.2,
            max_deviation_mm=45.0,
            std_deviation_mm=8.5,
            deviation_histogram={
                '0-5mm': 600000,
                '5-10mm': 350000,
                '10-25mm': 45000,
                '25-50mm': 4000,
                '50mm+': 1000
            },
            hotspot_regions=[
                {
                    'location': [10.5, 20.3, 3.2],
                    'deviation_mm': 45.0,
                    'affected_area_m2': 2.5
                }
            ]
        )
        
        self._analyses[analysis.analysis_id] = analysis
        
        logger.info(f"Completed deviation analysis: {analysis.analysis_id}")
        
        return analysis
    
    def get_deviation_status(self, deviation_mm: float) -> DeviationStatus:
        """Get status for deviation amount"""
        if deviation_mm <= self._tolerance_levels['within']:
            return DeviationStatus.WITHIN_TOLERANCE
        elif deviation_mm <= self._tolerance_levels['minor']:
            return DeviationStatus.MINOR_DEVIATION
        elif deviation_mm <= self._tolerance_levels['major']:
            return DeviationStatus.MAJOR_DEVIATION
        else:
            return DeviationStatus.CRITICAL_DEVIATION
    
    def generate_deviation_map(self, analysis_id: str) -> Dict:
        """Generate deviation map for visualization"""
        analysis = self._analyses.get(analysis_id)
        if not analysis:
            return None
        
        return {
            'analysis_id': analysis_id,
            'color_scale': {
                DeviationStatus.WITHIN_TOLERANCE.value: '#2ecc71',
                DeviationStatus.MINOR_DEVIATION.value: '#f1c40f',
                DeviationStatus.MAJOR_DEVIATION.value: '#e67e22',
                DeviationStatus.CRITICAL_DEVIATION.value: '#e74c3c'
            },
            'hotspots': analysis.hotspot_regions,
            'statistics': {
                'mean': analysis.mean_deviation_mm,
                'max': analysis.max_deviation_mm,
                'std': analysis.std_deviation_mm,
                'within_tolerance_percent': 
                    analysis.points_within_tolerance / analysis.total_points_analyzed * 100
            }
        }


class AsBuiltComparator:
    """Compares as-built scan with design model"""
    
    def __init__(self):
        self._comparisons: Dict[str, AsBuiltComparison] = {}
    
    def compare_scan_to_design(self, scan_id: str,
                                design_model_id: str) -> AsBuiltComparison:
        """Compare as-built scan with design model"""
        # This would perform actual comparison
        # For now, return placeholder
        
        comparison = AsBuiltComparison(
            comparison_id=str(uuid4()),
            scan_id=scan_id,
            design_model_id=design_model_id,
            compared_at=datetime.utcnow(),
            overall_status=DeviationStatus.WITHIN_TOLERANCE,
            completeness_percent=95.5,
            element_comparisons=[
                {
                    'element_id': 'wall-001',
                    'element_type': 'wall',
                    'design_position': [0, 0, 0],
                    'as_built_position': [0.005, 0.002, 0],
                    'deviation_mm': 5.4,
                    'status': DeviationStatus.WITHIN_TOLERANCE.value
                }
            ],
            missing_elements=[],
            extra_elements=['temp-structure-001']
        )
        
        self._comparisons[comparison.comparison_id] = comparison
        
        return comparison
    
    def generate_completeness_report(self, comparison_id: str) -> Dict:
        """Generate completeness report"""
        comparison = self._comparisons.get(comparison_id)
        if not comparison:
            return None
        
        return {
            'comparison_id': comparison_id,
            'completeness_percent': comparison.completeness_percent,
            'missing_elements_count': len(comparison.missing_elements),
            'extra_elements_count': len(comparison.extra_elements),
            'missing_elements': comparison.missing_elements,
            'extra_elements': comparison.extra_elements,
            'recommendations': self._generate_recommendations(comparison)
        }
    
    def _generate_recommendations(self, comparison: AsBuiltComparison) -> List[str]:
        """Generate recommendations based on comparison"""
        recommendations = []
        
        if comparison.completeness_percent < 90:
            recommendations.append("Additional scanning required for complete coverage")
        
        if comparison.missing_elements:
            recommendations.append("Verify missing elements with site inspection")
        
        if comparison.extra_elements:
            recommendations.append("Review extra elements for temporary structures")
        
        return recommendations


class AsBuiltDocumentation:
    """Generates as-built documentation"""
    
    def generate_report(self, project_id: str,
                        scan_ids: List[str],
                        comparison_ids: List[str]) -> Dict:
        """Generate as-built documentation report"""
        return {
            'project_id': project_id,
            'generated_at': datetime.utcnow().isoformat(),
            'scans_included': scan_ids,
            'comparisons_included': comparison_ids,
            'sections': [
                {
                    'title': 'Executive Summary',
                    'content': 'Overall as-built status summary'
                },
                {
                    'title': 'Scan Registration',
                    'content': 'Details of scan registration process'
                },
                {
                    'title': 'Deviation Analysis',
                    'content': 'Statistical analysis of deviations'
                },
                {
                    'title': 'Hotspot Locations',
                    'content': 'Areas requiring attention'
                },
                {
                    'title': 'Recommendations',
                    'content': 'Recommended actions'
                }
            ]
        }


# Global instances
point_cloud_manager = PointCloudManager()
deviation_analyzer = DeviationAnalyzer()
as_built_comparator = AsBuiltComparator()
as_built_docs = AsBuiltDocumentation()