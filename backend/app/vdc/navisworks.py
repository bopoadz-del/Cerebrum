"""
Navisworks Integration - NWD/BCF Export
Export to Navisworks format and BCF issues
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4
import zipfile
import io

logger = logging.getLogger(__name__)


class NavisworksFormat(Enum):
    """Navisworks formats"""
    NWD = "nwd"
    NWF = "nwf"
    NWC = "nwc"


@dataclass
class NavisworksExport:
    """Navisworks export configuration"""
    export_id: str
    federation_id: str
    format: NavisworksFormat
    file_path: str
    exported_at: datetime = field(default_factory=datetime.utcnow)
    exported_by: str = ""
    options: Dict[str, Any] = field(default_factory=dict)
    clash_tests_included: List[str] = field(default_factory=list)
    viewpoint_included: bool = True
    properties_included: bool = True


@dataclass
class BCFTopic:
    """BCF topic/issue"""
    topic_id: str
    title: str
    description: str
    status: str = "open"
    priority: str = "normal"
    topic_type: str = "coordination"
    creation_date: datetime = field(default_factory=datetime.utcnow)
    creation_author: str = ""
    modified_date: datetime = field(default_factory=datetime.utcnow)
    assigned_to: str = ""
    due_date: Optional[datetime] = None
    comments: List[Dict] = field(default_factory=list)
    viewpoints: List[Dict] = field(default_factory=list)
    related_clash_id: Optional[str] = None


class NavisworksExporter:
    """Export to Navisworks formats"""
    
    def __init__(self):
        self._exports: Dict[str, NavisworksExport] = {}
    
    def export_nwd(self, federation_id: str,
                   model_references: List[Dict],
                   options: Dict = None) -> NavisworksExport:
        """Export federated model to NWD"""
        # In practice, this would use Navisworks API or generate NWD file
        
        export = NavisworksExport(
            export_id=str(uuid4()),
            federation_id=federation_id,
            format=NavisworksFormat.NWD,
            file_path=f"/exports/{federation_id}.nwd",
            options=options or {}
        )
        
        self._exports[export.export_id] = export
        
        logger.info(f"Exported NWD: {export.export_id}")
        
        return export
    
    def export_nwf(self, federation_id: str,
                   model_references: List[Dict]) -> NavisworksExport:
        """Export to NWF (working file with references)"""
        export = NavisworksExport(
            export_id=str(uuid4()),
            federation_id=federation_id,
            format=NavisworksFormat.NWF,
            file_path=f"/exports/{federation_id}.nwf"
        )
        
        self._exports[export.export_id] = export
        
        return export
    
    def generate_clash_report_xml(self, clashes: List[Any]) -> str:
        """Generate Navisworks clash report XML"""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<exchange xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        xml += '  <batchtest name="Clash Detection Report">\n'
        xml += '    <clashtests>\n'
        
        for clash in clashes:
            xml += self._clash_to_xml(clash)
        
        xml += '    </clashtests>\n'
        xml += '  </batchtest>\n'
        xml += '</exchange>'
        
        return xml
    
    def _clash_to_xml(self, clash: Any) -> str:
        """Convert clash to Navisworks XML format"""
        clash_id = getattr(clash, 'clash_id', str(uuid4()))
        
        xml = f'      <clashresult name="Clash {clash_id}"\n'
        xml += f'                   status="new"\n'
        xml += f'                   image="">\n'
        xml += '        <resultstatus>new</resultstatus>\n'
        xml += '        <gridlocation></gridlocation>\n'
        xml += '      </clashresult>\n'
        
        return xml


class BCFExporter:
    """Export to BCF (BIM Collaboration Format)"""
    
    def __init__(self):
        self._topics: Dict[str, BCFTopic] = {}
    
    def create_topic_from_clash(self, clash: Any,
                                 author: str = "") -> BCFTopic:
        """Create BCF topic from clash"""
        clash_id = getattr(clash, 'clash_id', str(uuid4()))
        
        topic = BCFTopic(
            topic_id=str(uuid4()),
            title=f"Clash: {getattr(clash, 'clash_type', 'Unknown')}",
            description=f"Detected clash between elements",
            creation_author=author,
            related_clash_id=clash_id
        )
        
        # Add viewpoint
        viewpoint = self._create_viewpoint_from_clash(clash)
        topic.viewpoints.append(viewpoint)
        
        self._topics[topic.topic_id] = topic
        
        return topic
    
    def _create_viewpoint_from_clash(self, clash: Any) -> Dict:
        """Create BCF viewpoint from clash"""
        # Get intersection point if available
        intersection = getattr(clash, 'intersection_point', None)
        
        if intersection is not None:
            try:
                camera_target = {
                    'x': float(intersection[0]),
                    'y': float(intersection[1]),
                    'z': float(intersection[2])
                }
            except (TypeError, IndexError):
                camera_target = {'x': 0, 'y': 0, 'z': 0}
        else:
            camera_target = {'x': 0, 'y': 0, 'z': 0}
        
        return {
            'viewpoint_id': str(uuid4()),
            'camera_position': {
                'x': camera_target['x'] + 10,
                'y': camera_target['y'] + 10,
                'z': camera_target['z'] + 10
            },
            'camera_direction': {
                'x': -0.577,
                'y': -0.577,
                'z': -0.577
            },
            'camera_up': {
                'x': 0,
                'y': 0,
                'z': 1
            },
            'field_of_view': 60,
            'target': camera_target
        }
    
    def export_bcf(self, topic_ids: List[str],
                   project_name: str = "Project") -> bytes:
        """Export topics to BCF zip file"""
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add version file
            zf.writestr('bcf.version', 
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Version VersionId="2.1"/>')
            
            # Add project file
            project_xml = self._generate_project_xml(project_name)
            zf.writestr('project.bcfp', project_xml)
            
            # Add topics
            for topic_id in topic_ids:
                topic = self._topics.get(topic_id)
                if topic:
                    self._add_topic_to_zip(zf, topic)
        
        buffer.seek(0)
        return buffer.read()
    
    def _generate_project_xml(self, project_name: str) -> str:
        """Generate BCF project XML"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<ProjectExtension xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Project>
        <Name>{project_name}</Name>
    </Project>
    <ExtensionSchema/>
</ProjectExtension>"""
    
    def _add_topic_to_zip(self, zf: zipfile.ZipFile, topic: BCFTopic):
        """Add topic to BCF zip"""
        topic_dir = f"{topic.topic_id}/"
        
        # Add markup.bcf
        markup_xml = self._generate_markup_xml(topic)
        zf.writestr(f"{topic_dir}markup.bcf", markup_xml)
        
        # Add viewpoints
        for i, viewpoint in enumerate(topic.viewpoints):
            viewpoint_xml = self._generate_viewpoint_xml(viewpoint)
            zf.writestr(f"{topic_dir}viewpoint_{i}.bcfv", viewpoint_xml)
    
    def _generate_markup_xml(self, topic: BCFTopic) -> str:
        """Generate BCF markup XML"""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Topic Guid="{topic.topic_id}" TopicType="{topic.topic_type}" TopicStatus="{topic.status}">
        <Title>{topic.title}</Title>
        <Priority>{topic.priority}</Priority>
        <CreationDate>{topic.creation_date.isoformat()}</CreationDate>
        <CreationAuthor>{topic.creation_author}</CreationAuthor>
        <ModifiedDate>{topic.modified_date.isoformat()}</ModifiedDate>
        <Description>{topic.description}</Description>
    </Topic>
"""
        
        # Add comments
        for comment in topic.comments:
            xml += f"""    <Comment Guid="{comment.get('id', str(uuid4()))}">
        <Date>{comment.get('date', datetime.utcnow().isoformat())}</Date>
        <Author>{comment.get('author', '')}</Author>
        <Comment>{comment.get('text', '')}</Comment>
    </Comment>
"""
        
        # Add viewpoints
        xml += "    <Viewpoints>\n"
        for i, viewpoint in enumerate(topic.viewpoints):
            xml += f"""        <ViewPoint Guid="{viewpoint['viewpoint_id']}">
            <Viewpoint>viewpoint_{i}.bcfv</Viewpoint>
            <Snapshot>snapshot_{i}.png</Snapshot>
        </ViewPoint>
"""
        xml += "    </Viewpoints>\n"
        
        xml += "</Markup>"
        
        return xml
    
    def _generate_viewpoint_xml(self, viewpoint: Dict) -> str:
        """Generate BCF viewpoint XML"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<VisualizationInfo Guid="{viewpoint['viewpoint_id']}">
    <Components/>
    <PerspectiveCamera>
        <CameraViewPoint>
            <X>{viewpoint['camera_position']['x']}</X>
            <Y>{viewpoint['camera_position']['y']}</Y>
            <Z>{viewpoint['camera_position']['z']}</Z>
        </CameraViewPoint>
        <CameraDirection>
            <X>{viewpoint['camera_direction']['x']}</X>
            <Y>{viewpoint['camera_direction']['y']}</Y>
            <Z>{viewpoint['camera_direction']['z']}</Z>
        </CameraDirection>
        <CameraUpVector>
            <X>{viewpoint['camera_up']['x']}</X>
            <Y>{viewpoint['camera_up']['y']}</Y>
            <Z>{viewpoint['camera_up']['z']}</Z>
        </CameraUpVector>
        <FieldOfView>{viewpoint['field_of_view']}</FieldOfView>
    </PerspectiveCamera>
</VisualizationInfo>"""


class ClashToBCFConverter:
    """Converts clash data to BCF format"""
    
    def __init__(self):
        self.bcf_exporter = BCFExporter()
    
    def convert_clashes(self, clashes: List[Any],
                        project_name: str = "Project") -> bytes:
        """Convert list of clashes to BCF"""
        topic_ids = []
        
        for clash in clashes:
            topic = self.bcf_exporter.create_topic_from_clash(clash)
            topic_ids.append(topic.topic_id)
        
        return self.bcf_exporter.export_bcf(topic_ids, project_name)


# Global instances
navisworks_exporter = NavisworksExporter()
bcf_exporter = BCFExporter()
clash_converter = ClashToBCFConverter()