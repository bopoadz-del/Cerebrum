"""
Capability CRUD Operations

Database operations for capability lifecycle management.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from .models import CapabilityDB, Capability, CapabilityCreate, CapabilityUpdate, CapabilityStatus
from .dependencies import DependencyResolver
import logging

logger = logging.getLogger(__name__)


class CapabilityCRUD:
    """CRUD operations for capabilities."""
    
    def __init__(self, db: Session):
        self.db = db
        self.dependency_resolver = DependencyResolver()
    
    # ============ CREATE ============
    
    def create(self, data: CapabilityCreate, code_content: Optional[str] = None) -> CapabilityDB:
        """Create a new capability."""
        capability_id = str(uuid.uuid4())
        
        db_capability = CapabilityDB(
            id=capability_id,
            name=data.name,
            version=data.version,
            status=CapabilityStatus.DRAFT,
            capability_type=data.capability_type,
            description=data.description,
            author=data.author,
            dependencies=data.dependencies,
            required_packages=data.required_packages,
            api_contract=data.api_contract,
            schema_definition=data.schema_definition,
            code_content=code_content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(db_capability)
        self.db.commit()
        self.db.refresh(db_capability)
        
        logger.info(f"Created capability {data.name} v{data.version} (ID: {capability_id})")
        return db_capability
    
    # ============ READ ============
    
    def get_by_id(self, capability_id: str) -> Optional[CapabilityDB]:
        """Get capability by ID."""
        return self.db.query(CapabilityDB).filter(CapabilityDB.id == capability_id).first()
    
    def get_by_name(self, name: str) -> List[CapabilityDB]:
        """Get all versions of a capability by name."""
        return self.db.query(CapabilityDB).filter(CapabilityDB.name == name).all()
    
    def get_latest_by_name(self, name: str) -> Optional[CapabilityDB]:
        """Get the latest version of a capability by name."""
        return self.db.query(CapabilityDB)\
            .filter(CapabilityDB.name == name)\
            .order_by(desc(CapabilityDB.created_at))\
            .first()
    
    def list_capabilities(
        self,
        status: Optional[CapabilityStatus] = None,
        capability_type: Optional[str] = None,
        author: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CapabilityDB]:
        """List capabilities with optional filters."""
        query = self.db.query(CapabilityDB)
        
        if status:
            query = query.filter(CapabilityDB.status == status)
        if capability_type:
            query = query.filter(CapabilityDB.capability_type == capability_type)
        if author:
            query = query.filter(CapabilityDB.author == author)
        
        return query.order_by(desc(CapabilityDB.created_at)).offset(skip).limit(limit).all()
    
    def get_deployed_capabilities(self) -> List[CapabilityDB]:
        """Get all deployed capabilities."""
        return self.db.query(CapabilityDB)\
            .filter(CapabilityDB.status == CapabilityStatus.DEPLOYED)\
            .all()
    
    # ============ UPDATE ============
    
    def update(self, capability_id: str, data: CapabilityUpdate) -> Optional[CapabilityDB]:
        """Update a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_capability, field, value)
        
        db_capability.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_capability)
        
        logger.info(f"Updated capability {capability_id}")
        return db_capability
    
    def update_status(self, capability_id: str, status: CapabilityStatus) -> Optional[CapabilityDB]:
        """Update capability status."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return None
        
        db_capability.status = status
        db_capability.updated_at = datetime.utcnow()
        
        if status == CapabilityStatus.DEPLOYED:
            db_capability.deployed_at = datetime.utcnow()
            db_capability.deployment_count += 1
        
        self.db.commit()
        self.db.refresh(db_capability)
        
        logger.info(f"Updated capability {capability_id} status to {status}")
        return db_capability
    
    def update_validation_results(
        self, 
        capability_id: str, 
        validation_results: Dict[str, Any],
        security_scan: Dict[str, Any],
        test_results: Dict[str, Any]
    ) -> Optional[CapabilityDB]:
        """Update validation results."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return None
        
        db_capability.validation_results = validation_results
        db_capability.security_scan_results = security_scan
        db_capability.test_results = test_results
        db_capability.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_capability)
        return db_capability
    
    def record_error(self, capability_id: str, error_trace: str) -> Optional[CapabilityDB]:
        """Record an error for a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return None
        
        db_capability.error_count += 1
        db_capability.last_error_at = datetime.utcnow()
        db_capability.last_error_trace = error_trace
        db_capability.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_capability)
        
        logger.warning(f"Recorded error for capability {capability_id}")
        return db_capability
    
    def set_rollback_point(self, capability_id: str, previous_version_id: str):
        """Set rollback point for a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return None
        
        db_capability.previous_version_id = previous_version_id
        db_capability.rollback_available = 1
        db_capability.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_capability)
        return db_capability
    
    # ============ DELETE ============
    
    def delete(self, capability_id: str) -> bool:
        """Delete a capability (soft delete by marking deprecated)."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return False
        
        # Soft delete - mark as deprecated
        db_capability.status = CapabilityStatus.DEPRECATED
        db_capability.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Deprecated capability {capability_id}")
        return True
    
    def hard_delete(self, capability_id: str) -> bool:
        """Permanently delete a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return False
        
        self.db.delete(db_capability)
        self.db.commit()
        
        logger.info(f"Hard deleted capability {capability_id}")
        return True
    
    # ============ DEPENDENCY OPERATIONS ============
    
    def get_dependencies(self, capability_id: str) -> List[CapabilityDB]:
        """Get all dependencies for a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability or not db_capability.dependencies:
            return []
        
        return self.db.query(CapabilityDB)\
            .filter(CapabilityDB.id.in_(db_capability.dependencies))\
            .all()
    
    def get_dependents(self, capability_id: str) -> List[CapabilityDB]:
        """Get all capabilities that depend on this one."""
        return self.db.query(CapabilityDB)\
            .filter(CapabilityDB.dependencies.contains([capability_id]))\
            .all()
    
    def resolve_dependencies(self, capability_id: str) -> Dict[str, Any]:
        """Resolve dependencies for a capability."""
        db_capability = self.get_by_id(capability_id)
        if not db_capability:
            return {"error": "Capability not found"}
        
        # Register all capabilities in resolver
        all_caps = self.db.query(CapabilityDB).all()
        for cap in all_caps:
            deps = {}
            for dep_id in cap.dependencies:
                dep_cap = self.get_by_id(dep_id)
                if dep_cap:
                    constraint = cap.dependency_constraints.get(dep_id, "*")
                    deps[dep_id] = constraint
            
            self.dependency_resolver.register_capability(
                cap.id, cap.version, deps
            )
        
        resolved, unresolved, circular = self.dependency_resolver.resolve(capability_id)
        
        return {
            "capability_id": capability_id,
            "resolved_order": resolved,
            "unresolved": unresolved,
            "circular_dependencies": circular,
            "install_order": resolved  # Topological order
        }
    
    # ============ STATISTICS ============
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get capability statistics."""
        total = self.db.query(CapabilityDB).count()
        
        by_status = {}
        for status in CapabilityStatus:
            count = self.db.query(CapabilityDB).filter(CapabilityDB.status == status).count()
            by_status[status.value] = count
        
        by_type = {}
        from .models import CapabilityType
        for cap_type in CapabilityType:
            count = self.db.query(CapabilityDB).filter(CapabilityDB.capability_type == cap_type).count()
            by_type[cap_type.value] = count
        
        total_deployments = self.db.query(CapabilityDB).with_entities(
            CapabilityDB.deployment_count
        ).all()
        total_deployments = sum(d[0] for d in total_deployments)
        
        total_errors = self.db.query(CapabilityDB).with_entities(
            CapabilityDB.error_count
        ).all()
        total_errors = sum(e[0] for e in total_errors)
        
        return {
            "total_capabilities": total,
            "by_status": by_status,
            "by_type": by_type,
            "total_deployments": total_deployments,
            "total_errors": total_errors
        }
