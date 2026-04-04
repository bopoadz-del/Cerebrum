"""
Privileged Access Management (PAM)
Enterprise privileged account security
"""
import os
import secrets
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import asyncio

logger = logging.getLogger(__name__)


class PrivilegeLevel(Enum):
    """Privilege levels"""
    STANDARD = "standard"
    ELEVATED = "elevated"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    ROOT = "root"


class SessionStatus(Enum):
    """Privileged session status"""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class ApprovalStatus(Enum):
    """Approval request status"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class PrivilegedAccount:
    """Privileged account definition"""
    account_id: str
    account_name: str
    privilege_level: PrivilegeLevel
    owner_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_rotated_at: Optional[datetime] = None
    password_expiry_days: int = 90
    mfa_required: bool = True
    session_recording_required: bool = True
    approval_required: bool = True
    max_session_duration_minutes: int = 60
    allowed_time_windows: List[tuple] = field(default_factory=list)
    allowed_source_ips: List[str] = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivilegedSession:
    """Privileged access session"""
    session_id: str
    account_id: str
    user_id: str
    status: SessionStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approval_time: Optional[datetime] = None
    source_ip: Optional[str] = None
    mfa_verified: bool = False
    commands_executed: List[Dict] = field(default_factory=list)
    recordings: List[str] = field(default_factory=list)
    justification: str = ""
    ticket_reference: Optional[str] = None


@dataclass
class ApprovalRequest:
    """Approval request for privileged access"""
    request_id: str
    account_id: str
    requester_id: str
    status: ApprovalStatus
    requested_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    denial_reason: Optional[str] = None
    justification: str = ""
    emergency_access: bool = False
    ticket_reference: Optional[str] = None


class PasswordVault:
    """Secure password vault for privileged accounts"""
    
    def __init__(self):
        self._passwords: Dict[str, Dict] = {}
        self._encryption_key = os.environ.get('VAULT_ENCRYPTION_KEY', secrets.token_hex(32))
        self._access_log: List[Dict] = []
    
    def _encrypt(self, plaintext: str) -> str:
        """Encrypt password"""
        # In production, use proper encryption (e.g., AES-256-GCM)
        from cryptography.fernet import Fernet
        key = hashlib.sha256(self._encryption_key.encode()).digest()[:32]
        f = Fernet(hashlib.sha256(key).hexdigest()[:32].encode())
        return f.encrypt(plaintext.encode()).decode()
    
    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt password"""
        from cryptography.fernet import Fernet
        key = hashlib.sha256(self._encryption_key.encode()).digest()[:32]
        f = Fernet(hashlib.sha256(key).hexdigest()[:32].encode())
        return f.decrypt(ciphertext.encode()).decode()
    
    def store_password(self, account_id: str, password: str,
                       rotated_by: str = None):
        """Store password in vault"""
        encrypted = self._encrypt(password)
        
        self._passwords[account_id] = {
            'password': encrypted,
            'stored_at': datetime.utcnow().isoformat(),
            'rotated_by': rotated_by,
            'version': self._passwords.get(account_id, {}).get('version', 0) + 1
        }
        
        logger.info(f"Password stored for account: {account_id}")
    
    def retrieve_password(self, account_id: str, 
                          requester_id: str,
                          session_id: str = None) -> Optional[str]:
        """Retrieve password from vault"""
        entry = self._passwords.get(account_id)
        if not entry:
            return None
        
        # Log access
        self._access_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'account_id': account_id,
            'requester_id': requester_id,
            'session_id': session_id,
            'action': 'retrieve'
        })
        
        return self._decrypt(entry['password'])
    
    def rotate_password(self, account_id: str, 
                        rotated_by: str) -> str:
        """Rotate password for account"""
        # Generate new password
        new_password = self._generate_password()
        
        # Store new password
        self.store_password(account_id, new_password, rotated_by)
        
        # Log rotation
        logger.info(f"Password rotated for account: {account_id} by {rotated_by}")
        
        return new_password
    
    def _generate_password(self, length: int = 32) -> str:
        """Generate strong password"""
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            
            # Ensure password meets complexity requirements
            if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
                return password


class PrivilegedSessionManager:
    """Manages privileged access sessions"""
    
    def __init__(self, vault: PasswordVault = None):
        self.vault = vault or PasswordVault()
        self._accounts: Dict[str, PrivilegedAccount] = {}
        self._sessions: Dict[str, PrivilegedSession] = {}
        self._approval_requests: Dict[str, ApprovalRequest] = {}
        self._session_recordings: Dict[str, List] = {}
        self._command_logs: Dict[str, List] = {}
    
    def register_account(self, account: PrivilegedAccount):
        """Register a privileged account"""
        self._accounts[account.account_id] = account
        
        # Generate initial password
        initial_password = self.vault._generate_password()
        self.vault.store_password(account.account_id, initial_password, 'system')
        
        logger.info(f"Registered privileged account: {account.account_name}")
    
    async def request_session(self, account_id: str,
                              user_id: str,
                              justification: str,
                              ticket_reference: str = None,
                              emergency: bool = False) -> str:
        """Request privileged session"""
        account = self._accounts.get(account_id)
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        
        if not account.is_active:
            raise ValueError(f"Account is not active: {account_id}")
        
        # Create approval request if required
        if account.approval_required and not emergency:
            request_id = await self._create_approval_request(
                account_id, user_id, justification, ticket_reference, emergency
            )
            
            session = PrivilegedSession(
                session_id=f"SES-{secrets.token_hex(8)}",
                account_id=account_id,
                user_id=user_id,
                status=SessionStatus.PENDING_APPROVAL,
                justification=justification,
                ticket_reference=ticket_reference
            )
            
            self._sessions[session.session_id] = session
            
            return session.session_id
        
        # Create approved session
        session = await self._create_session(
            account_id, user_id, justification, ticket_reference
        )
        
        return session.session_id
    
    async def _create_approval_request(self, account_id: str,
                                       requester_id: str,
                                       justification: str,
                                       ticket_reference: str,
                                       emergency: bool) -> str:
        """Create approval request"""
        request_id = f"APR-{secrets.token_hex(8)}"
        
        request = ApprovalRequest(
            request_id=request_id,
            account_id=account_id,
            requester_id=requester_id,
            status=ApprovalStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            justification=justification,
            emergency_access=emergency,
            ticket_reference=ticket_reference
        )
        
        self._approval_requests[request_id] = request
        
        # Notify approvers
        await self._notify_approvers(request)
        
        logger.info(f"Approval request created: {request_id}")
        
        return request_id
    
    async def _create_session(self, account_id: str,
                              user_id: str,
                              justification: str,
                              ticket_reference: str) -> PrivilegedSession:
        """Create privileged session"""
        session_id = f"SES-{secrets.token_hex(8)}"
        
        session = PrivilegedSession(
            session_id=session_id,
            account_id=account_id,
            user_id=user_id,
            status=SessionStatus.APPROVED,
            justification=justification,
            ticket_reference=ticket_reference
        )
        
        self._sessions[session_id] = session
        
        return session
    
    async def approve_request(self, request_id: str, 
                              approver_id: str) -> str:
        """Approve access request"""
        request = self._approval_requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request is not pending: {request_id}")
        
        request.status = ApprovalStatus.APPROVED
        request.approved_by = approver_id
        request.approved_at = datetime.utcnow()
        
        # Find and activate session
        for session in self._sessions.values():
            if session.user_id == request.requester_id and \
               session.account_id == request.account_id and \
               session.status == SessionStatus.PENDING_APPROVAL:
                session.status = SessionStatus.APPROVED
                session.approved_by = approver_id
                session.approval_time = datetime.utcnow()
                break
        
        logger.info(f"Request approved: {request_id} by {approver_id}")
        
        return request_id
    
    async def start_session(self, session_id: str,
                            user_ip: str,
                            mfa_code: str = None) -> Dict:
        """Start privileged session"""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if session.status != SessionStatus.APPROVED:
            raise ValueError(f"Session not approved: {session_id}")
        
        account = self._accounts.get(session.account_id)
        
        # Verify MFA if required
        if account.mfa_required:
            if not mfa_code or not await self._verify_mfa(session.user_id, mfa_code):
                raise ValueError("MFA verification failed")
            session.mfa_verified = True
        
        # Check time window restrictions
        if account.allowed_time_windows:
            if not self._check_time_window(account.allowed_time_windows):
                raise ValueError("Access not allowed at this time")
        
        # Check IP restrictions
        if account.allowed_source_ips:
            if user_ip not in account.allowed_source_ips:
                raise ValueError("Access not allowed from this IP")
        
        # Activate session
        session.status = SessionStatus.ACTIVE
        session.started_at = datetime.utcnow()
        session.source_ip = user_ip
        
        # Retrieve credentials
        credentials = self.vault.retrieve_password(
            session.account_id, session.user_id, session_id
        )
        
        # Start session recording if required
        if account.session_recording_required:
            self._session_recordings[session_id] = []
        
        logger.info(f"Session started: {session_id}")
        
        return {
            'session_id': session_id,
            'credentials': credentials,
            'max_duration_minutes': account.max_session_duration_minutes,
            'recording_enabled': account.session_recording_required
        }
    
    async def _verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code"""
        # This would integrate with MFA provider
        return True
    
    def _check_time_window(self, time_windows: List[tuple]) -> bool:
        """Check if current time is within allowed windows"""
        now = datetime.utcnow()
        current_time = now.hour * 60 + now.minute
        
        for start, end in time_windows:
            start_minutes = start[0] * 60 + start[1]
            end_minutes = end[0] * 60 + end[1]
            
            if start_minutes <= current_time <= end_minutes:
                return True
        
        return False
    
    async def terminate_session(self, session_id: str,
                                reason: str = None):
        """Terminate privileged session"""
        session = self._sessions.get(session_id)
        if not session:
            return
        
        session.status = SessionStatus.TERMINATED
        session.ended_at = datetime.utcnow()
        
        # Rotate password
        account = self._accounts.get(session.account_id)
        if account:
            self.vault.rotate_password(session.account_id, 'session_termination')
        
        logger.info(f"Session terminated: {session_id}, reason: {reason}")
    
    def log_command(self, session_id: str, command: str,
                    output: str = None):
        """Log command executed in session"""
        if session_id not in self._command_logs:
            self._command_logs[session_id] = []
        
        self._command_logs[session_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'command': command,
            'output': output[:1000] if output else None  # Truncate output
        })
    
    def get_session_audit_log(self, session_id: str) -> Dict:
        """Get complete audit log for session"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        return {
            'session_id': session_id,
            'account_id': session.account_id,
            'user_id': session.user_id,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            'commands': self._command_logs.get(session_id, []),
            'recordings': session.recordings
        }


class BreakGlassAccess:
    """Emergency break-glass access"""
    
    def __init__(self, session_manager: PrivilegedSessionManager):
        self.session_manager = session_manager
        self._emergency_codes: Dict[str, str] = {}
        self._access_log: List[Dict] = []
    
    def generate_emergency_code(self, account_id: str) -> str:
        """Generate emergency access code"""
        code = secrets.token_urlsafe(16)
        self._emergency_codes[account_id] = code
        return code
    
    async def use_emergency_code(self, account_id: str,
                                  code: str,
                                  user_id: str,
                                  justification: str) -> str:
        """Use emergency code for immediate access"""
        stored_code = self._emergency_codes.get(account_id)
        if not stored_code or stored_code != code:
            raise ValueError("Invalid emergency code")
        
        # Consume code
        del self._emergency_codes[account_id]
        
        # Create emergency session
        session_id = await self.session_manager.request_session(
            account_id=account_id,
            user_id=user_id,
            justification=f"EMERGENCY: {justification}",
            emergency=True
        )
        
        # Log emergency access
        self._access_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'account_id': account_id,
            'user_id': user_id,
            'justification': justification,
            'session_id': session_id
        })
        
        # Notify security team
        await self._notify_security_team(account_id, user_id, justification)
        
        logger.warning(f"Emergency access used: {account_id} by {user_id}")
        
        return session_id
    
    async def _notify_security_team(self, account_id: str, 
                                    user_id: str, justification: str):
        """Notify security team of emergency access"""
        # This would integrate with notification system
        pass


# Global instances
password_vault = PasswordVault()
session_manager = PrivilegedSessionManager(password_vault)
break_glass = BreakGlassAccess(session_manager)