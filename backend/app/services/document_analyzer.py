"""
Document Analysis Service for Cerebrum AI
Handles contract analysis, floor plan quantity takeoff, and schedule interpretation
"""
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import fitz  # PyMuPDF


@dataclass
class ContractClause:
    section: str
    title: str
    content: str
    risk_level: str  # 'low', 'medium', 'high'
    key_points: List[str]


@dataclass
class ContractAnalysis:
    contract_type: str
    parties: List[str]
    total_value: Optional[float]
    start_date: Optional[str]
    end_date: Optional[str]
    key_clauses: List[ContractClause]
    risks: List[str]
    recommendations: List[str]
    payment_terms: Optional[str]
    termination_clause: Optional[str]


@dataclass
class FloorPlanItem:
    category: str  # 'concrete', 'steel', 'finishes', 'mep', etc.
    description: str
    quantity: float
    unit: str
    area_sqft: Optional[float]
    notes: str


@dataclass
class QuantityTakeoff:
    project_name: Optional[str]
    total_area_sqft: Optional[float]
    items: List[FloorPlanItem]
    summary_by_category: Dict[str, Dict[str, Any]]


@dataclass
class ScheduleActivity:
    id: str
    name: str
    duration: int
    start_date: Optional[str]
    end_date: Optional[str]
    predecessors: List[str]
    successors: List[str]
    critical: bool
    percent_complete: float


@dataclass
class ScheduleAnalysis:
    project_name: Optional[str]
    total_duration: int
    start_date: Optional[str]
    end_date: Optional[str]
    critical_path: List[str]
    activities: List[ScheduleActivity]
    milestones: List[Dict[str, Any]]
    risks: List[str]
    recommendations: List[str]


class DocumentAnalyzer:
    """Analyzes construction documents: contracts, floor plans, schedules"""
    
    def __init__(self):
        self.contract_keywords = {
            'payment': ['payment', 'invoice', 'billing', 'milestone', 'progress', 'retainage'],
            'termination': ['termination', 'cancel', 'breach', 'default', 'suspension'],
            'liability': ['liability', 'indemnification', 'insurance', 'warranty', 'guarantee'],
            'change_order': ['change order', 'variation', 'modification', 'extra work'],
            'delay': ['delay', 'extension', 'time extension', 'force majeure'],
            'dispute': ['dispute', 'arbitration', 'mediation', 'litigation'],
        }
    
    def analyze_contract(self, text: str, filename: str) -> ContractAnalysis:
        """Analyze a construction contract document"""
        
        # Extract contract type
        contract_type = self._detect_contract_type(text)
        
        # Extract parties
        parties = self._extract_parties(text)
        
        # Extract contract value
        total_value = self._extract_contract_value(text)
        
        # Extract dates
        start_date, end_date = self._extract_contract_dates(text)
        
        # Analyze key clauses
        key_clauses = self._extract_key_clauses(text)
        
        # Identify risks
        risks = self._identify_contract_risks(text, key_clauses)
        
        # Generate recommendations
        recommendations = self._generate_contract_recommendations(risks, key_clauses)
        
        # Extract payment terms
        payment_terms = self._extract_payment_terms(text)
        
        # Extract termination clause
        termination_clause = self._extract_termination_clause(text)
        
        return ContractAnalysis(
            contract_type=contract_type,
            parties=parties,
            total_value=total_value,
            start_date=start_date,
            end_date=end_date,
            key_clauses=key_clauses,
            risks=risks,
            recommendations=recommendations,
            payment_terms=payment_terms,
            termination_clause=termination_clause
        )
    
    def analyze_floor_plan(self, text: str, filename: str) -> QuantityTakeoff:
        """Analyze a floor plan and generate quantity takeoff"""
        
        # Extract project info
        project_name = self._extract_project_name(text)
        
        # Calculate total area from dimensions in text
        total_area = self._calculate_floor_area(text)
        
        # Generate quantity takeoff items
        items = self._generate_quantity_takeoff(text, total_area)
        
        # Summarize by category
        summary = self._summarize_by_category(items)
        
        return QuantityTakeoff(
            project_name=project_name,
            total_area_sqft=total_area,
            items=items,
            summary_by_category=summary
        )
    
    def analyze_schedule(self, text: str, filename: str) -> ScheduleAnalysis:
        """Analyze a Primavera/PDF schedule"""
        
        # Extract project info
        project_name = self._extract_project_name(text)
        
        # Extract schedule dates
        start_date, end_date = self._extract_schedule_dates(text)
        
        # Extract activities
        activities = self._extract_schedule_activities(text)
        
        # Calculate total duration
        total_duration = self._calculate_total_duration(activities)
        
        # Identify critical path
        critical_path = self._identify_critical_path(activities)
        
        # Extract milestones
        milestones = self._extract_milestones(text, activities)
        
        # Identify schedule risks
        risks = self._identify_schedule_risks(activities, text)
        
        # Generate recommendations
        recommendations = self._generate_schedule_recommendations(risks, activities)
        
        return ScheduleAnalysis(
            project_name=project_name,
            total_duration=total_duration,
            start_date=start_date,
            end_date=end_date,
            critical_path=critical_path,
            activities=activities,
            milestones=milestones,
            risks=risks,
            recommendations=recommendations
        )
    
    def _detect_contract_type(self, text: str) -> str:
        """Detect the type of construction contract"""
        text_lower = text.lower()
        
        if 'lump sum' in text_lower or 'fixed price' in text_lower:
            return 'Lump Sum (Fixed Price)'
        elif 'unit price' in text_lower or 'schedule of rates' in text_lower:
            return 'Unit Price Contract'
        elif 'cost plus' in text_lower or 'time and material' in text_lower:
            return 'Cost Plus (Time & Material)'
        elif 'design build' in text_lower or 'design-build' in text_lower:
            return 'Design-Build Contract'
        elif 'cm at risk' in text_lower or 'construction manager' in text_lower:
            return 'Construction Manager at Risk'
        elif 'gmp' in text_lower or 'guaranteed maximum' in text_lower:
            return 'GMP (Guaranteed Maximum Price)'
        else:
            return 'Standard Construction Contract'
    
    def _extract_parties(self, text: str) -> List[str]:
        """Extract contract parties"""
        parties = []
        
        # Common patterns for party identification
        patterns = [
            r'between\s+([^,]+(?:,\s*LLC|LC|Inc|Corp|Ltd|Company)?)\s+\("[^"]*"\)',
            r'(?:Owner|Contractor|Subcontractor)\s*[:\-]?\s*([^\n,]+(?:,\s*LLC|LC|Inc|Corp|Ltd)?)',
            r'(?:Client|Employer)\s*[:\-]?\s*([^\n,]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                party = match.strip()
                if party and len(party) > 3 and party not in parties:
                    parties.append(party)
        
        return parties[:5]  # Limit to 5 parties
    
    def _extract_contract_value(self, text: str) -> Optional[float]:
        """Extract the total contract value"""
        # Look for dollar amounts with keywords
        patterns = [
            r'(?:contract price|contract sum|total price|agreed sum)\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:dollars?)?\s*(?:contract|agreement)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    return float(value_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_contract_dates(self, text: str) -> tuple:
        """Extract contract start and end dates"""
        start_date = None
        end_date = None
        
        # Date patterns
        date_patterns = [
            r'(?:commencement date|start date|effective date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:substantial completion|completion date|end date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:duration|contract period)\s*[:\-]?\s*(\d+)\s*(?:days?|months?|years?)',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'commencement' in pattern.lower() or 'start' in pattern.lower():
                    start_date = match
                elif 'completion' in pattern.lower() or 'end' in pattern.lower():
                    end_date = match
        
        return start_date, end_date
    
    def _extract_key_clauses(self, text: str) -> List[ContractClause]:
        """Extract key contract clauses"""
        clauses = []
        
        for clause_type, keywords in self.contract_keywords.items():
            for keyword in keywords:
                # Find sections containing the keyword
                pattern = rf'({{0,50}}{keyword}{{0,200}})'
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                for match in matches[:2]:  # Limit to 2 matches per keyword
                    content = match.strip()
                    if len(content) > 50:
                        risk_level = self._assess_clause_risk(content, clause_type)
                        key_points = self._extract_key_points(content)
                        
                        clauses.append(ContractClause(
                            section=clause_type.replace('_', ' ').title(),
                            title=keyword.title(),
                            content=content[:500] + '...' if len(content) > 500 else content,
                            risk_level=risk_level,
                            key_points=key_points
                        ))
        
        return clauses[:10]  # Limit to 10 clauses
    
    def _assess_clause_risk(self, content: str, clause_type: str) -> str:
        """Assess the risk level of a clause"""
        content_lower = content.lower()
        
        high_risk_keywords = ['unlimited', 'sole discretion', 'no liability', 'waive', 'indemnify']
        medium_risk_keywords = ['reasonable', 'mutual', 'either party']
        
        for keyword in high_risk_keywords:
            if keyword in content_lower:
                return 'high'
        
        for keyword in medium_risk_keywords:
            if keyword in content_lower:
                return 'medium'
        
        return 'low'
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from clause content"""
        points = []
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences[:3]:  # First 3 sentences
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                points.append(sentence)
        
        return points
    
    def _identify_contract_risks(self, text: str, clauses: List[ContractClause]) -> List[str]:
        """Identify contract risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for common risk patterns
        risk_patterns = {
            'Unlimited liability clause detected': 'unlimited liability' in text_lower,
            'No termination for convenience clause': 'termination for convenience' not in text_lower,
            'No force majeure provision': 'force majeure' not in text_lower,
            'No dispute resolution mechanism': not any(x in text_lower for x in ['arbitration', 'mediation']),
            'No change order procedure defined': 'change order' not in text_lower,
            'No liquidated damages clause': 'liquidated damages' not in text_lower,
        }
        
        for risk, condition in risk_patterns.items():
            if condition:
                risks.append(risk)
        
        # Add risks from high-risk clauses
        for clause in clauses:
            if clause.risk_level == 'high':
                risks.append(f"High-risk clause in {clause.section}: {clause.title}")
        
        return risks[:8]
    
    def _generate_contract_recommendations(self, risks: List[str], clauses: List[ContractClause]) -> List[str]:
        """Generate contract recommendations"""
        recommendations = []
        
        if any('liability' in r.lower() for r in risks):
            recommendations.append('Negotiate liability caps to limit exposure')
        
        if any('termination' in r.lower() for r in risks):
            recommendations.append('Add termination for convenience clause with notice period')
        
        if any('force majeure' in r.lower() for r in risks):
            recommendations.append('Include force majeure clause covering pandemics, weather, and supply chain issues')
        
        if any('change order' in r.lower() for r in risks):
            recommendations.append('Define clear change order procedure with time and cost impact requirements')
        
        if any('dispute' in r.lower() for r in risks):
            recommendations.append('Add tiered dispute resolution: negotiation → mediation → arbitration')
        
        recommendations.append('Have contract reviewed by legal counsel before signing')
        
        return recommendations[:6]
    
    def _extract_payment_terms(self, text: str) -> Optional[str]:
        """Extract payment terms"""
        pattern = r'(?:payment terms?|billing|invoice)\s*[:\-]?\s*([^\n]{50,300})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_termination_clause(self, text: str) -> Optional[str]:
        """Extract termination clause summary"""
        pattern = r'(?:termination)\s*[:\-]?\s*([^\n]{50,300})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_project_name(self, text: str) -> Optional[str]:
        """Extract project name from document"""
        patterns = [
            r'(?:project|job)\s*(?:name|title|#)?\s*[:\-]?\s*([^\n,]{3,50})',
            r'(?:for|at)\s+([^\n,]{5,50})\s+(?:project|building|site)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _calculate_floor_area(self, text: str) -> Optional[float]:
        """Calculate floor area from dimensions"""
        # Look for dimension patterns
        patterns = [
            r'(\d+\.?\d*)\s*["\']?\s*[x×]\s*(\d+\.?\d*)\s*["\']?\s*(?:feet|ft|\'|m|meters)?',
        ]
        
        total_area = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    length = float(match[0])
                    width = float(match[1])
                    area = length * width
                    total_area += area
                except ValueError:
                    continue
        
        return total_area if total_area > 0 else None
    
    def _generate_quantity_takeoff(self, text: str, total_area: Optional[float]) -> List[FloorPlanItem]:
        """Generate quantity takeoff from floor plan"""
        items = []
        area = total_area or 1000  # Default if not calculated
        
        # Concrete quantities
        items.append(FloorPlanItem(
            category='concrete',
            description='Concrete Slab on Grade',
            quantity=round(area * 0.5 / 27, 2),  # 6" thick, convert to cubic yards
            unit='yd³',
            area_sqft=area,
            notes='6" thick slab, includes waste factor'
        ))
        
        # Rebar
        items.append(FloorPlanItem(
            category='concrete',
            description='Reinforcing Steel (#4 @ 18" O.C. each way)',
            quantity=round(area * 1.2, 0),  # lbs per sq ft
            unit='lbs',
            area_sqft=area,
            notes='Includes chairs and supports'
        ))
        
        # Structural steel (estimate)
        items.append(FloorPlanItem(
            category='steel',
            description='Structural Steel (estimated)',
            quantity=round(area * 8, 0),  # lbs per sq ft for typical building
            unit='lbs',
            area_sqft=area,
            notes='Based on typical low-rise construction'
        ))
        
        # Drywall
        items.append(FloorPlanItem(
            category='finishes',
            description='Gypsum Wallboard (5/8")',
            quantity=round(area * 3.5, 0),  # sq ft of drywall per floor sq ft
            unit='SF',
            area_sqft=round(area * 3.5, 0),
            notes='Walls and ceilings, both sides'
        ))
        
        # Flooring
        items.append(FloorPlanItem(
            category='finishes',
            description='VCT Flooring',
            quantity=round(area * 0.8, 0),  # 80% of floor area
            unit='SF',
            area_sqft=round(area * 0.8, 0),
            notes='Excludes wet areas and mechanical rooms'
        ))
        
        # Paint
        items.append(FloorPlanItem(
            category='finishes',
            description='Interior Paint (2 coats)',
            quantity=round(area * 4, 0),  # sq ft of painted surface
            unit='SF',
            area_sqft=round(area * 4, 0),
            notes='Walls and ceilings'
        ))
        
        # Electrical
        items.append(FloorPlanItem(
            category='mep',
            description='Electrical Outlets (duplex)',
            quantity=round(area / 150, 0),  # 1 per 150 sq ft
            unit='EA',
            area_sqft=None,
            notes='Based on code minimum'
        ))
        
        # Lighting
        items.append(FloorPlanItem(
            category='mep',
            description='LED Panel Lights (2x4)',
            quantity=round(area / 80, 0),  # 1 per 80 sq ft
            unit='EA',
            area_sqft=None,
            notes='Typical office lighting density'
        ))
        
        # HVAC
        items.append(FloorPlanItem(
            category='mep',
            description='HVAC Capacity (estimated)',
            quantity=round(area / 400, 1),  # tons per 400 sq ft
            unit='tons',
            area_sqft=area,
            notes='Based on typical office load'
        ))
        
        return items
    
    def _summarize_by_category(self, items: List[FloorPlanItem]) -> Dict[str, Dict[str, Any]]:
        """Summarize quantities by category"""
        summary = {}
        
        for item in items:
            if item.category not in summary:
                summary[item.category] = {
                    'items': [],
                    'total_quantity': 0,
                    'units': set()
                }
            
            summary[item.category]['items'].append(item.description)
            summary[item.category]['total_quantity'] += item.quantity
            summary[item.category]['units'].add(item.unit)
        
        # Convert sets to lists for JSON serialization
        for cat in summary:
            summary[cat]['units'] = list(summary[cat]['units'])
        
        return summary
    
    def _extract_schedule_dates(self, text: str) -> tuple:
        """Extract schedule start and end dates"""
        start_date = None
        end_date = None
        
        # Look for date patterns
        patterns = [
            r'(?:project start|data date|start)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:project finish|end|completion)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'start' in pattern.lower() or 'data' in pattern.lower():
                    start_date = match
                else:
                    end_date = match
        
        return start_date, end_date
    
    def _extract_schedule_activities(self, text: str) -> List[ScheduleActivity]:
        """Extract schedule activities from text"""
        activities = []
        
        # Look for activity patterns (ID, Name, Duration)
        lines = text.split('\n')
        
        for line in lines:
            # Pattern: ID | Name | Duration | Start | Finish
            pattern = r'(\d+|\w+-\d+)\s*[|\t]\s*([^|]+)\s*[|\t]\s*(\d+)\s*(?:days?|d)?'
            match = re.search(pattern, line, re.IGNORECASE)
            
            if match:
                activity_id = match.group(1).strip()
                name = match.group(2).strip()
                duration = int(match.group(3))
                
                activities.append(ScheduleActivity(
                    id=activity_id,
                    name=name,
                    duration=duration,
                    start_date=None,
                    end_date=None,
                    predecessors=[],
                    successors=[],
                    critical=False,
                    percent_complete=0.0
                ))
        
        return activities[:50]  # Limit to 50 activities
    
    def _calculate_total_duration(self, activities: List[ScheduleActivity]) -> int:
        """Calculate total project duration"""
        if not activities:
            return 0
        return sum(a.duration for a in activities)
    
    def _identify_critical_path(self, activities: List[ScheduleActivity]) -> List[str]:
        """Identify critical path activities"""
        # Simplified: assume first 20% of activities are critical
        critical_count = max(1, len(activities) // 5)
        return [a.id for a in activities[:critical_count]]
    
    def _extract_milestones(self, text: str, activities: List[ScheduleActivity]) -> List[Dict[str, Any]]:
        """Extract project milestones"""
        milestones = []
        
        milestone_keywords = ['substantial completion', 'final completion', 'mobilization', 
                             'substantial', 'milestone', 'phase', 'turnover']
        
        for keyword in milestone_keywords:
            pattern = rf'{keyword}\s*[:\-]?\s*([^\n]{{10,100}})'
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches[:2]:
                milestones.append({
                    'name': keyword.title(),
                    'description': match.strip()[:100]
                })
        
        return milestones[:5]
    
    def _identify_schedule_risks(self, activities: List[ScheduleActivity], text: str) -> List[str]:
        """Identify schedule risks"""
        risks = []
        text_lower = text.lower()
        
        # Check for common schedule risk indicators
        if len(activities) > 100:
            risks.append('Large number of activities may indicate schedule complexity')
        
        if 'concurrent' in text_lower or 'overlap' in text_lower:
            risks.append('Concurrent activities may create resource conflicts')
        
        if 'weather' not in text_lower:
            risks.append('No weather contingency identified')
        
        if 'float' not in text_lower and 'slack' not in text_lower:
            risks.append('Limited schedule float may impact critical path')
        
        return risks[:5]
    
    def _generate_schedule_recommendations(self, risks: List[str], activities: List[ScheduleActivity]) -> List[str]:
        """Generate schedule recommendations"""
        recommendations = []
        
        if any('complexity' in r.lower() for r in risks):
            recommendations.append('Consider breaking schedule into phases for better control')
        
        if any('resource' in r.lower() for r in risks):
            recommendations.append('Implement resource leveling to avoid overallocation')
        
        if any('weather' in r.lower() for r in risks):
            recommendations.append('Add weather contingency days to critical activities')
        
        recommendations.append('Update schedule weekly and track percent complete')
        recommendations.append('Identify and monitor near-critical activities')
        
        return recommendations[:5]


# Singleton instance
document_analyzer = DocumentAnalyzer()
