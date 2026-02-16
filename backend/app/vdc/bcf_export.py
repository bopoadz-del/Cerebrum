"""
BCF Export - BIM Collaboration Format Export
Exports clashes and issues to BCF format for BIM collaboration tools.
"""
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64
import json
import logging

from .clash_detection import Clash, ClashStatus, ClashSeverity

logger = logging.getLogger(__name__)


class BCFVersion(str, Enum):
    """BCF schema versions."""
    V2_1 = "2.1"
    V3_0 = "3.0"


@dataclass
class BCFViewpoint:
    """BCF viewpoint (camera position and visibility)."""
    viewpoint_id: str
    camera_position: Dict[str, float]  # x, y, z
    camera_direction: Dict[str, float]  # x, y, z
    camera_up: Dict[str, float]  # x, y, z
    field_of_view: float = 60.0
    aspect_ratio: float = 1.0
    snapshot: Optional[bytes] = None  # PNG image data
    snapshot_mime: str = "image/png"
    components: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_xml(self) -> str:
        """Convert viewpoint to BCF XML."""
        root = ET.Element("VisualizationInfo")
        root.set("Guid", self.viewpoint_id)
        
        # Camera
        camera = ET.SubElement(root, "PerspectiveCamera")
        
        cam_pos = ET.SubElement(camera, "CameraViewPoint")
        ET.SubElement(cam_pos, "X").text = str(self.camera_position['x'])
        ET.SubElement(cam_pos, "Y").text = str(self.camera_position['y'])
        ET.SubElement(cam_pos, "Z").text = str(self.camera_position['z'])
        
        cam_dir = ET.SubElement(camera, "CameraDirection")
        ET.SubElement(cam_dir, "X").text = str(self.camera_direction['x'])
        ET.SubElement(cam_dir, "Y").text = str(self.camera_direction['y'])
        ET.SubElement(cam_dir, "Z").text = str(self.camera_direction['z'])
        
        cam_up = ET.SubElement(camera, "CameraUpVector")
        ET.SubElement(cam_up, "X").text = str(self.camera_up['x'])
        ET.SubElement(cam_up, "Y").text = str(self.camera_up['y'])
        ET.SubElement(cam_up, "Z").text = str(self.camera_up['z'])
        
        ET.SubElement(camera, "FieldOfView").text = str(self.field_of_view)
        ET.SubElement(camera, "AspectRatio").text = str(self.aspect_ratio)
        
        # Components visibility
        if self.components:
            components_elem = ET.SubElement(root, "Components")
            for comp in self.components:
                comp_elem = ET.SubElement(components_elem, "Component")
                comp_elem.set("IfcGuid", comp.get('ifc_guid', ''))
                ET.SubElement(comp_elem, "OriginatingSystem").text = comp.get('system', 'Cerebrum')
                ET.SubElement(comp_elem, "AuthoringToolId").text = comp.get('id', '')
                visibility = ET.SubElement(comp_elem, "Visibility")
                visibility.set("DefaultVisibility", "true" if comp.get('visible', True) else "false")
        
        return ET.tostring(root, encoding='unicode')


@dataclass
class BCFTopic:
    """BCF topic (issue/clash)."""
    topic_id: str
    title: str
    description: str
    creation_date: datetime
    creation_author: str
    modified_date: datetime
    modified_author: str
    assigned_to: Optional[str] = None
    topic_status: str = "open"  # open, closed, reopened
    topic_type: str = "clash"   # clash, request, issue, remark
    priority: str = "normal"    # low, normal, high, critical
    stage: Optional[str] = None
    due_date: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    reference_links: List[str] = field(default_factory=list)
    viewpoints: List[BCFViewpoint] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    document_references: List[Dict[str, Any]] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    bim_snippet: Optional[Dict[str, Any]] = None
    
    def to_markup_xml(self) -> str:
        """Convert topic to BCF markup XML."""
        root = ET.Element("Markup")
        
        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "File").set("IfcProject", "")
        
        # Topic
        topic = ET.SubElement(root, "Topic")
        topic.set("Guid", self.topic_id)
        topic.set("TopicType", self.topic_type)
        topic.set("TopicStatus", self.topic_status)
        
        ET.SubElement(topic, "ReferenceLink")
        ET.SubElement(topic, "Title").text = self.title
        ET.SubElement(topic, "Priority").text = self.priority
        ET.SubElement(topic, "Index").text = "0"
        
        if self.labels:
            labels_elem = ET.SubElement(topic, "Labels")
            for label in self.labels:
                ET.SubElement(labels_elem, "Label").text = label
        
        ET.SubElement(topic, "CreationDate").text = self.creation_date.isoformat()
        ET.SubElement(topic, "CreationAuthor").text = self.creation_author
        ET.SubElement(topic, "ModifiedDate").text = self.modified_date.isoformat()
        ET.SubElement(topic, "ModifiedAuthor").text = self.modified_author
        
        if self.due_date:
            ET.SubElement(topic, "DueDate").text = self.due_date.isoformat()
        
        ET.SubElement(topic, "AssignedTo").text = self.assigned_to or ""
        ET.SubElement(topic, "Description").text = self.description
        
        # Viewpoints
        for vp in self.viewpoints:
            vp_elem = ET.SubElement(topic, "Viewpoints")
            vp_elem.set("Guid", vp.viewpoint_id)
            ET.SubElement(vp_elem, "Viewpoint").text = f"{vp.viewpoint_id}.bcfv"
            ET.SubElement(vp_elem, "Snapshot").text = f"{vp.viewpoint_id}.png"
        
        # Comments
        for comment in self.comments:
            comment_elem = ET.SubElement(root, "Comment")
            comment_elem.set("Guid", comment.get('id', ''))
            ET.SubElement(comment_elem, "Date").text = comment.get('date', datetime.utcnow().isoformat())
            ET.SubElement(comment_elem, "Author").text = comment.get('author', '')
            ET.SubElement(comment_elem, "Comment").text = comment.get('text', '')
            if comment.get('viewpoint_id'):
                ET.SubElement(comment_elem, "Viewpoint").set("Guid", comment['viewpoint_id'])
        
        return ET.tostring(root, encoding='unicode')


class BCFExporter:
    """Exports clashes to BCF format."""
    
    def __init__(self, version: BCFVersion = BCFVersion.V2_1):
        self.version = version
    
    def export_clash(self, clash: Clash, 
                    author: str = "Cerebrum",
                    project_name: str = "") -> BCFTopic:
        """Convert a clash to BCF topic."""
        topic_id = clash.id
        
        # Create title
        title = f"{clash.clash_type.value.replace('_', ' ').title()}: " \
                f"{clash.element_a.name} vs {clash.element_b.name}"
        
        # Create description
        description = f"""Clash Detection Result

Type: {clash.clash_type.value}
Severity: {clash.severity.value}
Status: {clash.status.value}

Element A:
- Name: {clash.element_a.name}
- Type: {clash.element_a.element_type.value}
- Discipline: {clash.element_a.discipline.value}

Element B:
- Name: {clash.element_b.name}
- Type: {clash.element_b.element_type.value}
- Discipline: {clash.element_b.discipline.value}

Intersection Details:
- Volume: {clash.intersection_volume:.6f} m³
- Penetration Depth: {clash.penetration_depth:.4f} m
- Location: ({clash.intersection_center.x:.3f}, {clash.intersection_center.y:.3f}, {clash.intersection_center.z:.3f})

Detected: {clash.created_at.isoformat()}
"""
        
        # Create viewpoint
        viewpoint = self._create_viewpoint_for_clash(clash)
        
        # Map severity to priority
        priority_map = {
            ClashSeverity.CRITICAL: "critical",
            ClashSeverity.HIGH: "high",
            ClashSeverity.MEDIUM: "normal",
            ClashSeverity.LOW: "low"
        }
        
        # Map status
        status_map = {
            ClashStatus.NEW: "open",
            ClashStatus.ACTIVE: "open",
            ClashStatus.RESOLVED: "closed",
            ClashStatus.IGNORED: "closed",
            ClashStatus.APPROVED: "closed"
        }
        
        topic = BCFTopic(
            topic_id=topic_id,
            title=title,
            description=description,
            creation_date=clash.created_at,
            creation_author=author,
            modified_date=clash.resolved_at or clash.created_at,
            modified_author=clash.resolved_by or author,
            assigned_to=clash.assigned_to,
            topic_status=status_map.get(clash.status, "open"),
            topic_type="clash",
            priority=priority_map.get(clash.severity, "normal"),
            labels=[clash.element_a.discipline.value, clash.element_b.discipline.value],
            viewpoints=[viewpoint]
        )
        
        return topic
    
    def _create_viewpoint_for_clash(self, clash: Clash) -> BCFViewpoint:
        """Create a BCF viewpoint for a clash."""
        center = clash.intersection_center
        
        # Camera positioned to view clash
        camera_pos = {
            'x': center.x + 5.0,  # Offset for viewing
            'y': center.y + 5.0,
            'z': center.z + 3.0
        }
        
        # Direction towards clash center
        camera_dir = {
            'x': center.x - camera_pos['x'],
            'y': center.y - camera_pos['y'],
            'z': center.z - camera_pos['z']
        }
        
        # Normalize direction
        import math
        length = math.sqrt(sum(v**2 for v in camera_dir.values()))
        if length > 0:
            camera_dir = {k: v/length for k, v in camera_dir.items()}
        
        # Up vector
        camera_up = {'x': 0, 'y': 0, 'z': 1}
        
        # Components (clashing elements)
        components = [
            {
                'ifc_guid': clash.element_a.global_id,
                'id': clash.element_a.id,
                'system': 'Cerebrum',
                'visible': True
            },
            {
                'ifc_guid': clash.element_b.global_id,
                'id': clash.element_b.id,
                'system': 'Cerebrum',
                'visible': True
            }
        ]
        
        return BCFViewpoint(
            viewpoint_id=f"vp-{clash.id[:8]}",
            camera_position=camera_pos,
            camera_direction=camera_dir,
            camera_up=camera_up,
            field_of_view=60.0,
            components=components
        )
    
    def export_clashes_to_bcfzip(self, clashes: List[Clash],
                                 output_path: str,
                                 author: str = "Cerebrum",
                                 project_name: str = "") -> str:
        """Export multiple clashes to BCFzip file."""
        topics = [self.export_clash(c, author, project_name) for c in clashes]
        return self._create_bcfzip(topics, output_path, project_name)
    
    def _create_bcfzip(self, topics: List[BCFTopic], 
                      output_path: str,
                      project_name: str) -> str:
        """Create BCFzip archive from topics."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write project info
            project_xml = self._create_project_xml(project_name)
            zf.writestr('project.bcfp', project_xml)
            
            # Write version
            version_xml = self._create_version_xml()
            zf.writestr('bcf.version', version_xml)
            
            # Write each topic
            for topic in topics:
                topic_dir = topic.topic_id
                
                # Markup
                zf.writestr(f"{topic_dir}/markup.bcf", topic.to_markup_xml())
                
                # Viewpoints
                for vp in topic.viewpoints:
                    zf.writestr(f"{topic_dir}/{vp.viewpoint_id}.bcfv", vp.to_xml())
                    
                    # Snapshot (placeholder)
                    if vp.snapshot:
                        zf.writestr(f"{topic_dir}/{vp.viewpoint_id}.png", vp.snapshot)
        
        logger.info(f"Created BCFzip: {output_path} with {len(topics)} topics")
        return output_path
    
    def _create_project_xml(self, project_name: str) -> str:
        """Create BCF project XML."""
        root = ET.Element("ProjectExtension")
        
        project = ET.SubElement(root, "Project")
        project.set("ProjectId", "cerebrum-project")
        ET.SubElement(project, "Name").text = project_name or "Cerebrum Project"
        
        ET.SubElement(root, "ExtensionSchema")
        
        return ET.tostring(root, encoding='unicode')
    
    def _create_version_xml(self) -> str:
        """Create BCF version XML."""
        root = ET.Element("Version")
        root.set("VersionId", self.version.value)
        ET.SubElement(root, "DetailedVersion").text = f"BCF {self.version.value}"
        
        return ET.tostring(root, encoding='unicode')
    
    def export_to_bytes(self, clashes: List[Clash],
                       author: str = "Cerebrum",
                       project_name: str = "") -> bytes:
        """Export clashes to BCFzip as bytes."""
        buffer = io.BytesIO()
        
        topics = [self.export_clash(c, author, project_name) for c in clashes]
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('project.bcfp', self._create_project_xml(project_name))
            zf.writestr('bcf.version', self._create_version_xml())
            
            for topic in topics:
                topic_dir = topic.topic_id
                zf.writestr(f"{topic_dir}/markup.bcf", topic.to_markup_xml())
                
                for vp in topic.viewpoints:
                    zf.writestr(f"{topic_dir}/{vp.viewpoint_id}.bcfv", vp.to_xml())
        
        return buffer.getvalue()


class BCFImporter:
    """Import BCF files."""
    
    def import_bcfzip(self, file_path: str) -> List[BCFTopic]:
        """Import topics from BCFzip file."""
        topics = []
        
        with zipfile.ZipFile(file_path, 'r') as zf:
            # List all files
            for name in zf.namelist():
                if name.endswith('/markup.bcf'):
                    topic_id = name.split('/')[0]
                    markup_content = zf.read(name).decode('utf-8')
                    topic = self._parse_markup(markup_content, topic_id)
                    if topic:
                        topics.append(topic)
        
        return topics
    
    def _parse_markup(self, markup_xml: str, topic_id: str) -> Optional[BCFTopic]:
        """Parse BCF markup XML."""
        try:
            root = ET.fromstring(markup_xml)
            
            topic_elem = root.find('Topic')
            if topic_elem is None:
                return None
            
            title = topic_elem.findtext('Title', '')
            description = topic_elem.findtext('Description', '')
            priority = topic_elem.findtext('Priority', 'normal')
            
            creation_date_str = topic_elem.findtext('CreationDate', datetime.utcnow().isoformat())
            creation_author = topic_elem.findtext('CreationAuthor', '')
            
            return BCFTopic(
                topic_id=topic_id,
                title=title,
                description=description,
                creation_date=datetime.fromisoformat(creation_date_str.replace('Z', '+00:00')),
                creation_author=creation_author,
                modified_date=datetime.utcnow(),
                modified_author=creation_author,
                priority=priority
            )
        
        except Exception as e:
            logger.error(f"Failed to parse BCF markup: {e}")
            return None
