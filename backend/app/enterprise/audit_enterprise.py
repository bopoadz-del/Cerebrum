"""
Enterprise Audit Module - Admin audit logs and compliance dashboards
Item 288: Enterprise audit logs and compliance dashboards
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import json

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum
import hashlib


class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    MFA_ENABLED = "auth.mfa_enabled"
    MFA_DISABLED = "auth.mfa_disabled"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_RESET = "auth.password_reset"
    SESSION_EXPIRED = "auth.session_expired"
    
    # User management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_DELETED = "user.deleted"
    USER_INVITED = "user.invited"
    USER_ROLE_CHANGED = "user.role_changed"
    
    # Tenant management
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_SUSPENDED = "tenant.suspended"
    TENANT_DELETED = "tenant.deleted"
    
    # Data access
    DATA_VIEWED = "data.viewed"
    DATA_EXPORTED = "data.exported"
    DATA_IMPORTED = "data.imported"
    DATA_DELETED = "data.deleted"
    
    # Configuration changes
    SETTINGS_CHANGED = "config.settings_changed"
    INTEGRATION_ADDED = "config.integration_added"
    INTEGRATION_REMOVED = "config.integration_removed"
    SSO_CONFIGURED = "config.sso_configured"
    
    # Security
    PERMISSION_DENIED = "security.permission_denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    IP_BLOCKED = "security.ip_blocked"
    API_KEY_CREATED = "security.api_key_created"
    API_KEY_REVOKED = "security.api_key_revoked"


class ComplianceStandard(str, Enum):
    """Compliance standards"""
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


# Database Models

class EnterpriseAuditLog(Base):
    """Comprehensive audit log"""
    __tablename__ = 'enterprise_audit_log'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default='info')  # debug, info, warning, error, critical
    
    # Actor information
    actor_type = Column(String(50), default='user')  # user, system, api, integration
    actor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    actor_email = Column(String(255), nullable=True)
    
    # Target information
    target_type = Column(String(100), nullable=True)  # user, project, document, etc.
    target_id = Column(String(255), nullable=True)
    target_name = Column(String(500), nullable=True)
    
    # Context
    action = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Data changes
    before_values = Column(JSONB, nullable=True)
    after_values = Column(JSONB, nullable=True)
    changes_summary = Column(JSONB, nullable=True)
    
    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Location
    country_code = Column(String(5), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Compliance
    compliance_tags = Column(JSONB, default=list)
    retention_until = Column(DateTime, nullable=True)
    
    # Integrity
    log_hash = Column(String(64), nullable=True)
    previous_log_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_audit_logs_tenant_event', 'tenant_id', 'event_type'),
        Index('ix_audit_logs_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_audit_logs_actor', 'actor_id', 'created_at'),
        Index('ix_audit_logs_target', 'target_type', 'target_id'),
        Index('ix_audit_logs_compliance', 'compliance_tags'),
    )


class ComplianceReport(Base):
    """Compliance report generation"""
    __tablename__ = 'compliance_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Report details
    name = Column(String(255), nullable=False)
    standard = Column(String(50), nullable=False)
    report_type = Column(String(50), nullable=False)
    
    # Date range
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String(50), default='pending')  # pending, generating, completed, failed
    
    # Results
    findings = Column(JSONB, default=list)
    summary = Column(JSONB, default=dict)
    
    # File
    file_url = Column(String(500), nullable=True)
    file_format = Column(String(20), default='pdf')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class DataRetentionPolicy(Base):
    """Data retention policies"""
    __tablename__ = 'data_retention_policies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    
    retention_days = Column(Integer, nullable=False)
    archive_after_days = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class EnterpriseAuditLogCreateRequest(BaseModel):
    """Create audit log entry"""
    event_type: str
    event_category: str = 'general'
    severity: str = 'info'
    actor_type: str = 'user'
    actor_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    before_values: Optional[Dict[str, Any]] = None
    after_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    compliance_tags: List[str] = Field(default_factory=list)


class EnterpriseAuditLogQuery(BaseModel):
    """Query audit logs"""
    tenant_id: Optional[str] = None
    event_types: List[str] = Field(default_factory=list)
    event_categories: List[str] = Field(default_factory=list)
    actor_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    severity: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    compliance_standard: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ComplianceReportRequest(BaseModel):
    """Generate compliance report"""
    name: str
    standard: ComplianceStandard
    report_type: str = 'full'
    period_start: datetime
    period_end: datetime


class ComplianceDashboardStats(BaseModel):
    """Compliance dashboard statistics"""
    total_events: int
    events_by_category: Dict[str, int]
    events_by_severity: Dict[str, int]
    recent_security_events: List[Dict[str, Any]]
    compliance_status: Dict[str, Any]


# Service Classes

class AuditService:
    """Service for audit logging"""
    
    def __init__(self, db: Session):
        self.db = db
        self._last_hash = None
    
    def log_event(
        self,
        tenant_id: Optional[str],
        event_type: str,
        event_category: str = 'general',
        severity: str = 'info',
        actor_type: str = 'user',
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        action: Optional[str] = None,
        description: Optional[str] = None,
        before_values: Optional[Dict] = None,
        after_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None
    ) -> EnterpriseAuditLog:
        """Create audit log entry"""
        
        # Calculate changes summary
        changes_summary = None
        if before_values and after_values:
            changes_summary = self._calculate_changes(before_values, after_values)
        
        # Get location from IP
        country_code, city = self._get_location(ip_address)
        
        # Create log entry
        log = EnterpriseAuditLog(
            tenant_id=tenant_id,
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_email=actor_email,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            action=action,
            description=description,
            before_values=before_values,
            after_values=after_values,
            changes_summary=changes_summary,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            country_code=country_code,
            city=city,
            compliance_tags=compliance_tags or []
        )
        
        self.db.add(log)
        self.db.flush()
        
        # Calculate integrity hash
        log.log_hash = self._calculate_hash(log)
        log.previous_log_hash = self._last_hash
        self._last_hash = log.log_hash
        
        self.db.commit()
        
        return log
    
    def _calculate_changes(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate what changed between before and after"""
        
        changes = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)
            
            if key not in before:
                changes['added'][key] = after_val
            elif key not in after:
                changes['removed'][key] = before_val
            elif before_val != after_val:
                changes['modified'][key] = {
                    'from': before_val,
                    'to': after_val
                }
        
        return changes
    
    def _get_location(self, ip_address: Optional[str]) -> tuple:
        """Get location from IP address"""
        
        if not ip_address:
            return None, None
        
        # In production, use a GeoIP service
        # For now, return placeholder
        return None, None
    
    def _calculate_hash(self, log: EnterpriseAuditLog) -> str:
        """Calculate integrity hash for log entry"""
        
        data = {
            'id': str(log.id),
            'tenant_id': str(log.tenant_id) if log.tenant_id else None,
            'event_type': log.event_type,
            'created_at': log.created_at.isoformat() if log.created_at else None,
            'actor_id': str(log.actor_id) if log.actor_id else None,
            'previous_hash': self._last_hash
        }
        
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    
    def query_logs(
        self,
        query: EnterpriseAuditLogQuery
    ) -> tuple:
        """Query audit logs with filters"""
        
        q = self.db.query(EnterpriseAuditLog)
        
        if query.tenant_id:
            q = q.filter(EnterpriseAuditLog.tenant_id == query.tenant_id)
        
        if query.event_types:
            q = q.filter(EnterpriseAuditLog.event_type.in_(query.event_types))
        
        if query.event_categories:
            q = q.filter(EnterpriseAuditLog.event_category.in_(query.event_categories))
        
        if query.actor_id:
            q = q.filter(EnterpriseAuditLog.actor_id == query.actor_id)
        
        if query.target_type:
            q = q.filter(EnterpriseAuditLog.target_type == query.target_type)
        
        if query.target_id:
            q = q.filter(EnterpriseAuditLog.target_id == query.target_id)
        
        if query.severity:
            q = q.filter(EnterpriseAuditLog.severity == query.severity)
        
        if query.date_from:
            q = q.filter(EnterpriseAuditLog.created_at >= query.date_from)
        
        if query.date_to:
            q = q.filter(EnterpriseAuditLog.created_at <= query.date_to)
        
        if query.compliance_standard:
            q = q.filter(
                EnterpriseAuditLog.compliance_tags.contains([query.compliance_standard])
            )
        
        total = q.count()
        
        logs = q.order_by(EnterpriseAuditLog.created_at.desc()).offset(
            query.offset
        ).limit(query.limit).all()
        
        return logs, total
    
    def get_user_activity(
        self,
        tenant_id: str,
        user_id: str,
        days: int = 30
    ) -> List[EnterpriseAuditLog]:
        """Get activity for a specific user"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(EnterpriseAuditLog).filter(
            EnterpriseAuditLog.tenant_id == tenant_id,
            EnterpriseAuditLog.actor_id == user_id,
            EnterpriseAuditLog.created_at >= since
        ).order_by(EnterpriseAuditLog.created_at.desc()).all()
    
    def get_security_events(
        self,
        tenant_id: str,
        days: int = 7
    ) -> List[EnterpriseAuditLog]:
        """Get security-related events"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        security_categories = ['auth', 'security']
        
        return self.db.query(EnterpriseAuditLog).filter(
            EnterpriseAuditLog.tenant_id == tenant_id,
            EnterpriseAuditLog.event_category.in_(security_categories),
            EnterpriseAuditLog.created_at >= since
        ).order_by(EnterpriseAuditLog.created_at.desc()).limit(100).all()


class ComplianceService:
    """Service for compliance reporting"""
    
    COMPLIANCE_CONTROLS = {
        ComplianceStandard.SOC2: {
            'CC6.1': 'Logical access security',
            'CC6.2': 'Access removal',
            'CC6.3': 'Access establishment',
            'CC7.2': 'System monitoring',
            'CC7.3': 'Incident detection'
        },
        ComplianceStandard.ISO27001: {
            'A.9.1.1': 'Access control policy',
            'A.9.2.1': 'User registration',
            'A.9.2.2': 'Access to privileged accounts',
            'A.9.2.6': 'Removal of access rights',
            'A.12.4': 'Logging and monitoring'
        },
        ComplianceStandard.GDPR: {
            'Article 5': 'Data processing principles',
            'Article 17': 'Right to erasure',
            'Article 25': 'Data protection by design',
            'Article 30': 'Records of processing',
            'Article 32': 'Security of processing'
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
    
    def generate_report(
        self,
        tenant_id: Optional[str],
        request: ComplianceReportRequest,
        created_by: Optional[str] = None
    ) -> ComplianceReport:
        """Generate compliance report"""
        
        report = ComplianceReport(
            tenant_id=tenant_id,
            name=request.name,
            standard=request.standard.value,
            report_type=request.report_type,
            period_start=request.period_start,
            period_end=request.period_end,
            status='generating',
            created_by=created_by
        )
        
        self.db.add(report)
        self.db.commit()
        
        # Generate findings
        findings = self._generate_findings(
            tenant_id,
            request.standard.value,
            request.period_start,
            request.period_end
        )
        
        report.findings = findings
        report.summary = self._generate_summary(findings)
        report.status = 'completed'
        report.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        return report
    
    def _generate_findings(
        self,
        tenant_id: Optional[str],
        standard: str,
        period_start: datetime,
        period_end: datetime
    ) -> List[Dict[str, Any]]:
        """Generate compliance findings"""
        
        findings = []
        
        controls = self.COMPLIANCE_CONTROLS.get(ComplianceStandard(standard), {})
        
        for control_id, control_name in controls.items():
            # Query relevant audit logs
            logs = self.db.query(EnterpriseAuditLog).filter(
                EnterpriseAuditLog.tenant_id == tenant_id,
                EnterpriseAuditLog.created_at >= period_start,
                EnterpriseAuditLog.created_at <= period_end,
                EnterpriseAuditLog.compliance_tags.contains([standard])
            ).all()
            
            # Analyze compliance
            finding = self._analyze_control(control_id, control_name, logs)
            findings.append(finding)
        
        return findings
    
    def _analyze_control(
        self,
        control_id: str,
        control_name: str,
        logs: List[EnterpriseAuditLog]
    ) -> Dict[str, Any]:
        """Analyze compliance for a specific control"""
        
        # Count relevant events
        event_count = len(logs)
        
        # Check for violations
        violations = [log for log in logs if log.severity in ['error', 'critical']]
        
        # Determine status
        if not violations:
            status = 'compliant'
        elif len(violations) < 5:
            status = 'partial'
        else:
            status = 'non_compliant'
        
        return {
            'control_id': control_id,
            'control_name': control_name,
            'status': status,
            'event_count': event_count,
            'violation_count': len(violations),
            'violations': [
                {
                    'id': str(v.id),
                    'event_type': v.event_type,
                    'severity': v.severity,
                    'created_at': v.created_at.isoformat()
                }
                for v in violations[:10]
            ]
        }
    
    def _generate_summary(self, findings: List[Dict]) -> Dict[str, Any]:
        """Generate report summary"""
        
        total_controls = len(findings)
        compliant = sum(1 for f in findings if f['status'] == 'compliant')
        partial = sum(1 for f in findings if f['status'] == 'partial')
        non_compliant = sum(1 for f in findings if f['status'] == 'non_compliant')
        
        total_violations = sum(f['violation_count'] for f in findings)
        
        return {
            'total_controls': total_controls,
            'compliant': compliant,
            'partial': partial,
            'non_compliant': non_compliant,
            'compliance_rate': (compliant / total_controls * 100) if total_controls > 0 else 0,
            'total_violations': total_violations
        }
    
    def get_dashboard_stats(
        self,
        tenant_id: str,
        days: int = 30
    ) -> ComplianceDashboardStats:
        """Get compliance dashboard statistics"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total events
        total_events = self.db.query(func.count(EnterpriseAuditLog.id)).filter(
            EnterpriseAuditLog.tenant_id == tenant_id,
            EnterpriseAuditLog.created_at >= since
        ).scalar()
        
        # Events by category
        category_counts = self.db.query(
            EnterpriseAuditLog.event_category,
            func.count(EnterpriseAuditLog.id)
        ).filter(
            EnterpriseAuditLog.tenant_id == tenant_id,
            EnterpriseAuditLog.created_at >= since
        ).group_by(EnterpriseAuditLog.event_category).all()
        
        events_by_category = {cat: count for cat, count in category_counts}
        
        # Events by severity
        severity_counts = self.db.query(
            EnterpriseAuditLog.severity,
            func.count(EnterpriseAuditLog.id)
        ).filter(
            EnterpriseAuditLog.tenant_id == tenant_id,
            EnterpriseAuditLog.created_at >= since
        ).group_by(EnterpriseAuditLog.severity).all()
        
        events_by_severity = {sev: count for sev, count in severity_counts}
        
        # Recent security events
        security_events = self.audit_service.get_security_events(tenant_id, 7)
        
        recent_security = [
            {
                'id': str(e.id),
                'event_type': e.event_type,
                'severity': e.severity,
                'description': e.description,
                'created_at': e.created_at.isoformat()
            }
            for e in security_events[:10]
        ]
        
        # Compliance status
        compliance_status = self._get_compliance_status(tenant_id)
        
        return ComplianceDashboardStats(
            total_events=total_events,
            events_by_category=events_by_category,
            events_by_severity=events_by_severity,
            recent_security_events=recent_security,
            compliance_status=compliance_status
        )
    
    def _get_compliance_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get compliance status for all standards"""
        
        status = {}
        
        for standard in ComplianceStandard:
            # Get latest report
            latest_report = self.db.query(ComplianceReport).filter(
                ComplianceReport.tenant_id == tenant_id,
                ComplianceReport.standard == standard.value,
                ComplianceReport.status == 'completed'
            ).order_by(ComplianceReport.completed_at.desc()).first()
            
            if latest_report:
                status[standard.value] = {
                    'last_report': latest_report.completed_at.isoformat(),
                    'compliance_rate': latest_report.summary.get('compliance_rate', 0),
                    'violations': latest_report.summary.get('total_violations', 0)
                }
            else:
                status[standard.value] = {
                    'last_report': None,
                    'compliance_rate': None,
                    'violations': None
                }
        
        return status


class DataRetentionService:
    """Service for data retention management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def apply_retention_policies(self):
        """Apply all retention policies"""
        
        policies = self.db.query(DataRetentionPolicy).filter(
            DataRetentionPolicy.is_active == True
        ).all()
        
        for policy in policies:
            self._apply_policy(policy)
    
    def _apply_policy(self, policy: DataRetentionPolicy):
        """Apply a single retention policy"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        if policy.data_type == 'audit_logs':
            # Archive or delete old audit logs
            old_logs = self.db.query(EnterpriseAuditLog).filter(
                EnterpriseAuditLog.tenant_id == policy.tenant_id,
                EnterpriseAuditLog.created_at < cutoff_date
            ).all()
            
            if policy.archive_after_days:
                # Archive logs
                self._archive_logs(old_logs)
            else:
                # Delete logs
                for log in old_logs:
                    self.db.delete(log)
        
        self.db.commit()
    
    def _archive_logs(self, logs: List[EnterpriseAuditLog]):
        """Archive audit logs"""
        
        # In production, move to cold storage
        # For now, just mark as archived
        for log in logs:
            log.compliance_tags.append('archived')


# Export
__all__ = [
    'AuditEventType',
    'ComplianceStandard',
    'EnterpriseAuditLog',
    'ComplianceReport',
    'DataRetentionPolicy',
    'EnterpriseAuditLogCreateRequest',
    'EnterpriseAuditLogQuery',
    'ComplianceReportRequest',
    'ComplianceDashboardStats',
    'AuditService',
    'ComplianceService',
    'DataRetentionService'
]
