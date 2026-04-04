"""
2D Drawing Generation
Automated 2D drawing generation from BIM models
"""
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class DrawingType(Enum):
    """Types of 2D drawings"""
    PLAN = "plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SCHEDULE = "schedule"
    LEGEND = "legend"
    COVER_SHEET = "cover_sheet"


class DrawingScale(Enum):
    """Standard drawing scales"""
    SCALE_1_1 = "1:1"
    SCALE_1_5 = "1:5"
    SCALE_1_10 = "1:10"
    SCALE_1_20 = "1:20"
    SCALE_1_50 = "1:50"
    SCALE_1_100 = "1:100"
    SCALE_1_200 = "1:200"
    SCALE_1_500 = "1:500"


@dataclass
class DrawingSheet:
    """Drawing sheet configuration"""
    sheet_id: str
    name: str
    drawing_type: DrawingType
    scale: DrawingScale
    title_block: str
    sheet_size: str  # A0, A1, A2, A3, A4, etc.
    viewports: List[Dict] = field(default_factory=list)
    annotations: List[Dict] = field(default_factory=list)
    revision_history: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class DrawingViewport:
    """Viewport on drawing sheet"""
    viewport_id: str
    name: str
    view_type: str  # plan, elevation, section, 3d
    model_view_id: str
    location: Dict[str, float]  # x, y on sheet
    size: Dict[str, float]  # width, height
    scale: DrawingScale
    crop_region: Optional[Dict] = None
    visibility_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DrawingAnnotation:
    """Drawing annotation"""
    annotation_id: str
    annotation_type: str  # dimension, text, tag, symbol, etc.
    location: Dict[str, float]
    properties: Dict[str, Any] = field(default_factory=dict)
    associated_element_id: Optional[str] = None


class DrawingGenerator:
    """Generates 2D drawings from BIM models"""
    
    def __init__(self):
        self._sheets: Dict[str, DrawingSheet] = {}
        self._viewports: Dict[str, DrawingViewport] = {}
        self._templates: Dict[str, Dict] = {}
    
    def create_sheet(self, name: str,
                     drawing_type: DrawingType,
                     scale: DrawingScale,
                     sheet_size: str = "A1",
                     title_block: str = "standard",
                     created_by: str = "") -> DrawingSheet:
        """Create new drawing sheet"""
        sheet = DrawingSheet(
            sheet_id=str(uuid4()),
            name=name,
            drawing_type=drawing_type,
            scale=scale,
            sheet_size=sheet_size,
            title_block=title_block,
            created_by=created_by
        )
        
        self._sheets[sheet.sheet_id] = sheet
        
        logger.info(f"Created drawing sheet: {sheet.sheet_id}")
        
        return sheet
    
    def add_viewport(self, sheet_id: str,
                     name: str,
                     view_type: str,
                     model_view_id: str,
                     location: Dict[str, float],
                     size: Dict[str, float],
                     scale: DrawingScale) -> Optional[DrawingViewport]:
        """Add viewport to sheet"""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None
        
        viewport = DrawingViewport(
            viewport_id=str(uuid4()),
            name=name,
            view_type=view_type,
            model_view_id=model_view_id,
            location=location,
            size=size,
            scale=scale
        )
        
        self._viewports[viewport.viewport_id] = viewport
        
        sheet.viewports.append({
            'viewport_id': viewport.viewport_id,
            'name': viewport.name,
            'location': viewport.location,
            'size': viewport.size
        })
        
        return viewport
    
    def generate_floor_plan(self, model_id: str,
                            level: str,
                            scale: DrawingScale = DrawingScale.SCALE_1_100,
                            options: Dict = None) -> DrawingSheet:
        """Generate floor plan drawing"""
        sheet = self.create_sheet(
            name=f"Floor Plan - {level}",
            drawing_type=DrawingType.PLAN,
            scale=scale
        )
        
        # Add main plan viewport
        self.add_viewport(
            sheet_id=sheet.sheet_id,
            name=f"{level} Plan",
            view_type="plan",
            model_view_id=f"{model_id}:plan:{level}",
            location={'x': 25, 'y': 50},
            size={'width': 250, 'height': 180},
            scale=scale
        )
        
        # Add annotations
        self._add_plan_annotations(sheet, level)
        
        return sheet
    
    def generate_elevation(self, model_id: str,
                           direction: str,  # north, south, east, west
                           scale: DrawingScale = DrawingScale.SCALE_1_100,
                           options: Dict = None) -> DrawingSheet:
        """Generate elevation drawing"""
        sheet = self.create_sheet(
            name=f"Elevation - {direction.title()}",
            drawing_type=DrawingType.ELEVATION,
            scale=scale
        )
        
        # Add elevation viewport
        self.add_viewport(
            sheet_id=sheet.sheet_id,
            name=f"{direction.title()} Elevation",
            view_type="elevation",
            model_view_id=f"{model_id}:elevation:{direction}",
            location={'x': 25, 'y': 50},
            size={'width': 250, 'height': 150},
            scale=scale
        )
        
        return sheet
    
    def generate_section(self, model_id: str,
                         section_name: str,
                         cut_line: List[Tuple[float, float]],
                         scale: DrawingScale = DrawingScale.SCALE_1_50,
                         options: Dict = None) -> DrawingSheet:
        """Generate section drawing"""
        sheet = self.create_sheet(
            name=f"Section - {section_name}",
            drawing_type=DrawingType.SECTION,
            scale=scale
        )
        
        # Add section viewport
        self.add_viewport(
            sheet_id=sheet.sheet_id,
            name=f"Section {section_name}",
            view_type="section",
            model_view_id=f"{model_id}:section:{section_name}",
            location={'x': 25, 'y': 50},
            size={'width': 250, 'height': 150},
            scale=scale
        )
        
        return sheet
    
    def _add_plan_annotations(self, sheet: DrawingSheet, level: str):
        """Add standard plan annotations"""
        # Room tags
        # Door/window tags
        # Grid lines
        # Dimensions
        # Level markers
        pass
    
    def export_to_pdf(self, sheet_id: str,
                      output_path: str = None) -> str:
        """Export sheet to PDF"""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            raise ValueError(f"Sheet not found: {sheet_id}")
        
        output_path = output_path or f"/drawings/{sheet_id}.pdf"
        
        # In practice, this would generate actual PDF
        logger.info(f"Exported sheet to PDF: {output_path}")
        
        return output_path
    
    def export_to_dwg(self, sheet_id: str,
                      output_path: str = None) -> str:
        """Export sheet to DWG"""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            raise ValueError(f"Sheet not found: {sheet_id}")
        
        output_path = output_path or f"/drawings/{sheet_id}.dwg"
        
        logger.info(f"Exported sheet to DWG: {output_path}")
        
        return output_path
    
    def create_drawing_set(self, project_id: str,
                           model_id: str,
                           levels: List[str]) -> List[DrawingSheet]:
        """Create complete drawing set for project"""
        sheets = []
        
        # Floor plans
        for level in levels:
            plan = self.generate_floor_plan(model_id, level)
            sheets.append(plan)
        
        # Elevations
        for direction in ['north', 'south', 'east', 'west']:
            elevation = self.generate_elevation(model_id, direction)
            sheets.append(elevation)
        
        # Sections
        section = self.generate_section(
            model_id, "A-A",
            [(0, 0), (10000, 0)]
        )
        sheets.append(section)
        
        return sheets


class ScheduleGenerator:
    """Generates schedules from BIM models"""
    
    def generate_door_schedule(self, model_id: str,
                               elements: List[Dict]) -> Dict:
        """Generate door schedule"""
        schedule = {
            'title': 'Door Schedule',
            'columns': ['Mark', 'Type', 'Width', 'Height', 'Fire Rating', 'Frame', 'Finish'],
            'rows': []
        }
        
        for i, element in enumerate(elements):
            if element.get('type') == 'door':
                schedule['rows'].append({
                    'Mark': f"D{i+1}",
                    'Type': element.get('type_name', 'Standard'),
                    'Width': element.get('parameters', {}).get('Width', 900),
                    'Height': element.get('parameters', {}).get('Height', 2100),
                    'Fire Rating': element.get('parameters', {}).get('FireRating', '-'),
                    'Frame': element.get('parameters', {}).get('FrameMaterial', 'Steel'),
                    'Finish': element.get('parameters', {}).get('Finish', 'Painted')
                })
        
        return schedule
    
    def generate_window_schedule(self, model_id: str,
                                  elements: List[Dict]) -> Dict:
        """Generate window schedule"""
        schedule = {
            'title': 'Window Schedule',
            'columns': ['Mark', 'Type', 'Width', 'Height', 'Glazing', 'Frame'],
            'rows': []
        }
        
        for i, element in enumerate(elements):
            if element.get('type') == 'window':
                schedule['rows'].append({
                    'Mark': f"W{i+1}",
                    'Type': element.get('type_name', 'Standard'),
                    'Width': element.get('parameters', {}).get('Width', 1200),
                    'Height': element.get('parameters', {}).get('Height', 1200),
                    'Glazing': element.get('parameters', {}).get('Glazing', 'Double'),
                    'Frame': element.get('parameters', {}).get('FrameMaterial', 'Aluminum')
                })
        
        return schedule
    
    def generate_room_schedule(self, model_id: str,
                               rooms: List[Dict]) -> Dict:
        """Generate room schedule"""
        schedule = {
            'title': 'Room Schedule',
            'columns': ['Number', 'Name', 'Area', 'Level', 'Department'],
            'rows': []
        }
        
        for room in rooms:
            schedule['rows'].append({
                'Number': room.get('number', ''),
                'Name': room.get('name', ''),
                'Area': room.get('area', 0),
                'Level': room.get('level', ''),
                'Department': room.get('department', '')
            })
        
        return schedule


class TitleBlockManager:
    """Manages drawing title blocks"""
    
    def __init__(self):
        self._title_blocks: Dict[str, Dict] = {}
    
    def register_title_block(self, name: str,
                             sheet_size: str,
                             layout: Dict):
        """Register title block template"""
        self._title_blocks[name] = {
            'name': name,
            'sheet_size': sheet_size,
            'layout': layout
        }
    
    def get_title_block(self, name: str) -> Optional[Dict]:
        """Get title block by name"""
        return self._title_blocks.get(name)
    
    def fill_title_block(self, title_block_name: str,
                         project_info: Dict,
                         sheet_info: Dict) -> Dict:
        """Fill title block with project information"""
        title_block = self._title_blocks.get(title_block_name, {})
        
        filled = {
            'project_name': project_info.get('name', ''),
            'project_number': project_info.get('number', ''),
            'sheet_name': sheet_info.get('name', ''),
            'sheet_number': sheet_info.get('number', ''),
            'scale': sheet_info.get('scale', ''),
            'drawn_by': sheet_info.get('drawn_by', ''),
            'checked_by': sheet_info.get('checked_by', ''),
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'revision': sheet_info.get('revision', 'A')
        }
        
        return filled


# Global instances
drawing_generator = DrawingGenerator()
schedule_generator = ScheduleGenerator()
title_block_manager = TitleBlockManager()