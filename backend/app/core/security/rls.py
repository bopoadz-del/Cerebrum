"""
PostgreSQL Row-Level Security (RLS) with Tenant Isolation Policies
Implements multi-tenant data isolation at the database level.
"""
from typing import Optional, List, Dict, Any
from contextvars import ContextVar
from sqlalchemy import text, event
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)

# Context variable for current tenant ID
tenant_id_ctx: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
user_roles_ctx: ContextVar[List[str]] = ContextVar('user_roles', default=[])


class RLSPolicyManager:
    """Manages PostgreSQL Row-Level Security policies for multi-tenant isolation."""
    
    # Standard RLS policies
    POLICIES = {
        'tenant_isolation': """
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant')::UUID)
        """,
        'tenant_insert': """
            CREATE POLICY {table}_tenant_insert ON {table}
            FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant')::UUID)
        """,
        'tenant_update': """
            CREATE POLICY {table}_tenant_update ON {table}
            FOR UPDATE USING (tenant_id = current_setting('app.current_tenant')::UUID)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::UUID)
        """,
        'tenant_delete': """
            CREATE POLICY {table}_tenant_delete ON {table}
            FOR DELETE USING (tenant_id = current_setting('app.current_tenant')::UUID)
        """,
        'admin_bypass': """
            CREATE POLICY {table}_admin_bypass ON {table}
            USING (current_setting('app.current_roles')::text[] && ARRAY['admin', 'superadmin'])
        """,
        'owner_access': """
            CREATE POLICY {table}_owner_access ON {table}
            USING (
                tenant_id = current_setting('app.current_tenant')::UUID
                AND (created_by = current_setting('app.current_user')::UUID 
                     OR current_setting('app.current_roles')::text[] && ARRAY['admin'])
            )
        """,
        'public_read': """
            CREATE POLICY {table}_public_read ON {table}
            FOR SELECT USING (is_public = true)
        """,
        'shared_tenant': """
            CREATE POLICY {table}_shared_tenant ON {table}
            USING (
                tenant_id = current_setting('app.current_tenant')::UUID
                OR tenant_id = ANY(
                    SELECT shared_tenant_id FROM {table}_shares 
                    WHERE source_tenant_id = current_setting('app.current_tenant')::UUID
                )
            )
        """
    }
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def set_tenant_context(self, session: Session, tenant_id: Optional[str] = None,
                          user_id: Optional[str] = None, roles: Optional[List[str]] = None):
        """Set tenant context for RLS policies in the current session."""
        tenant = tenant_id or tenant_id_ctx.get()
        user = user_id or user_id_ctx.get()
        user_roles = roles or user_roles_ctx.get()
        
        if tenant:
            session.execute(text("SET LOCAL app.current_tenant = :tenant"), {'tenant': tenant})
        if user:
            session.execute(text("SET LOCAL app.current_user = :user"), {'user': user})
        if user_roles:
            session.execute(text("SET LOCAL app.current_roles = :roles"), {'roles': user_roles})
    
    def enable_rls(self, table_name: str, session: Session):
        """Enable RLS on a table."""
        session.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        session.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
        logger.info(f"RLS enabled on table: {table_name}")
    
    def disable_rls(self, table_name: str, session: Session):
        """Disable RLS on a table (use with caution)."""
        session.execute(text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
        logger.warning(f"RLS disabled on table: {table_name}")
    
    def create_policy(self, table_name: str, policy_name: str, session: Session,
                     custom_policy: Optional[str] = None):
        """Create an RLS policy on a table."""
        policy_sql = custom_policy or self.POLICIES.get(policy_name, '').format(table=table_name)
        if not policy_sql:
            raise ValueError(f"Unknown policy: {policy_name}")
        
        # Drop existing policy if exists
        session.execute(text(f"""
            DROP POLICY IF EXISTS {table_name}_{policy_name} ON {table_name}
        """))
        
        # Create new policy
        session.execute(text(policy_sql))
        logger.info(f"Created RLS policy {policy_name} on {table_name}")
    
    def drop_policy(self, table_name: str, policy_name: str, session: Session):
        """Drop an RLS policy from a table."""
        session.execute(text(f"""
            DROP POLICY IF EXISTS {table_name}_{policy_name} ON {table_name}
        """))
        logger.info(f"Dropped RLS policy {policy_name} from {table_name}")
    
    def setup_standard_policies(self, table_name: str, session: Session,
                                policies: Optional[List[str]] = None):
        """Setup standard RLS policies for a tenant-isolated table."""
        self.enable_rls(table_name, session)
        
        default_policies = ['tenant_isolation', 'tenant_insert', 'tenant_update', 'tenant_delete']
        for policy in (policies or default_policies):
            self.create_policy(table_name, policy, session)
    
    def bypass_rls(self, session: Session):
        """Bypass RLS for administrative operations (use with extreme caution)."""
        session.execute(text("SET LOCAL row_security = off"))
        logger.warning("RLS bypassed for current session")
    
    def get_policies(self, table_name: Optional[str] = None, session: Session = None) -> List[Dict]:
        """Get all RLS policies, optionally filtered by table."""
        query = """
            SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
            FROM pg_policies
            WHERE 1=1
        """
        params = {}
        if table_name:
            query += " AND tablename = :table"
            params['table'] = table_name
        
        result = session.execute(text(query), params)
        return [dict(row._mapping) for row in result]


class TenantContext:
    """Context manager for tenant isolation."""
    
    def __init__(self, tenant_id: str, user_id: Optional[str] = None,
                 roles: Optional[List[str]] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.roles = roles or []
        self._tenant_token = None
        self._user_token = None
        self._roles_token = None
    
    def __enter__(self):
        self._tenant_token = tenant_id_ctx.set(self.tenant_id)
        if self.user_id:
            self._user_token = user_id_ctx.set(self.user_id)
        if self.roles:
            self._roles_token = user_roles_ctx.set(self.roles)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        tenant_id_ctx.reset(self._tenant_token)
        if self._user_token:
            user_id_ctx.reset(self._user_token)
        if self._roles_token:
            user_roles_ctx.reset(self._roles_token)


def get_current_tenant() -> Optional[str]:
    """Get current tenant ID from context."""
    return tenant_id_ctx.get()


def get_current_user() -> Optional[str]:
    """Get current user ID from context."""
    return user_id_ctx.get()


def get_current_roles() -> List[str]:
    """Get current user roles from context."""
    return user_roles_ctx.get()


# SQLAlchemy event listeners for automatic tenant context setting
@event.listens_for(Session, 'after_begin')
def set_rls_context(session, transaction, connection):
    """Automatically set RLS context when a session begins."""
    tenant_id = tenant_id_ctx.get()
    user_id = user_id_ctx.get()
    roles = user_roles_ctx.get()
    
    if tenant_id:
        connection.execute(text("SET LOCAL app.current_tenant = :tenant"), {'tenant': tenant_id})
    if user_id:
        connection.execute(text("SET LOCAL app.current_user = :user"), {'user': user_id})
    if roles:
        connection.execute(text("SET LOCAL app.current_roles = :roles"), {'roles': roles})
