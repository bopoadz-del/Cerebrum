"""
GraphQL Module - GraphQL Endpoint and Bulk Export API
Item 300: GraphQL endpoint and bulk export API
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
import uuid
import json
import io

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
import graphene
from graphene import ObjectType, String, Int, Float, Boolean, List as GraphQLList, Field as GraphQLField
from graphene_sqlalchemy import SQLAlchemyObjectType
from graphql.execution.executors.asyncio import AsyncioExecutor
import asyncio


# GraphQL Schema Definitions

class ProjectType(SQLAlchemyObjectType):
    """GraphQL type for Project"""
    class Meta:
        model = Project
        interfaces = (graphene.relay.Node, )


class TaskType(SQLAlchemyObjectType):
    """GraphQL type for Task"""
    class Meta:
        model = Task
        interfaces = (graphene.relay.Node, )


class UserType(SQLAlchemyObjectType):
    """GraphQL type for User"""
    class Meta:
        model = User
        interfaces = (graphene.relay.Node, )
        exclude_fields = ('password_hash',)


class DocumentType(SQLAlchemyObjectType):
    """GraphQL type for Document"""
    class Meta:
        model = Document
        interfaces = (graphene.relay.Node, )


class Query(ObjectType):
    """GraphQL Query"""
    
    # Single item queries
    project = graphene.relay.Node.Field(ProjectType)
    task = graphene.relay.Node.Field(TaskType)
    user = graphene.relay.Node.Field(UserType)
    document = graphene.relay.Node.Field(DocumentType)
    
    # List queries
    projects = GraphQLList(ProjectType,
        tenant_id=String(required=True),
        status=String(),
        limit=Int(default_value=100),
        offset=Int(default_value=0)
    )
    
    tasks = GraphQLList(TaskType,
        project_id=String(),
        assignee_id=String(),
        status=String(),
        limit=Int(default_value=100),
        offset=Int(default_value=0)
    )
    
    users = GraphQLList(UserType,
        tenant_id=String(required=True),
        role=String(),
        is_active=Boolean(),
        limit=Int(default_value=100),
        offset=Int(default_value=0)
    )
    
    documents = GraphQLList(DocumentType,
        project_id=String(),
        document_type=String(),
        limit=Int(default_value=100),
        offset=Int(default_value=0)
    )
    
    # Aggregation queries
    project_stats = GraphQLField(graphene.types.generic.GenericScalar,
        tenant_id=String(required=True)
    )
    
    user_activity = GraphQLList(graphene.types.generic.GenericScalar,
        tenant_id=String(required=True),
        days=Int(default_value=30)
    )
    
    async def resolve_projects(self, info, tenant_id, status=None, limit=100, offset=0):
        """Resolve projects query"""
        query = Project.get_query(info)
        query = query.filter(Project.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Project.status == status)
        
        return query.offset(offset).limit(limit).all()
    
    async def resolve_tasks(self, info, project_id=None, assignee_id=None, status=None, limit=100, offset=0):
        """Resolve tasks query"""
        query = Task.get_query(info)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        
        if status:
            query = query.filter(Task.status == status)
        
        return query.offset(offset).limit(limit).all()
    
    async def resolve_users(self, info, tenant_id, role=None, is_active=None, limit=100, offset=0):
        """Resolve users query"""
        query = User.get_query(info)
        query = query.filter(User.tenant_id == tenant_id)
        
        if role:
            query = query.filter(User.role == role)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(offset).limit(limit).all()
    
    async def resolve_documents(self, info, project_id=None, document_type=None, limit=100, offset=0):
        """Resolve documents query"""
        query = Document.get_query(info)
        
        if project_id:
            query = query.filter(Document.project_id == project_id)
        
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        return query.offset(offset).limit(limit).all()
    
    async def resolve_project_stats(self, info, tenant_id):
        """Resolve project statistics"""
        db = info.context['session']
        
        total = db.query(Project).filter(Project.tenant_id == tenant_id).count()
        active = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status == 'active'
        ).count()
        completed = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status == 'completed'
        ).count()
        
        return {
            'total': total,
            'active': active,
            'completed': completed
        }


class CreateProjectMutation(graphene.Mutation):
    """Create project mutation"""
    class Arguments:
        name = String(required=True)
        description = String()
        tenant_id = String(required=True)
        status = String()
    
    project = GraphQLField(lambda: ProjectType)
    success = Boolean()
    error = String()
    
    async def mutate(self, info, name, tenant_id, description=None, status='planning'):
        """Create project"""
        db = info.context['session']
        
        try:
            project = Project(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                name=name,
                description=description,
                status=status
            )
            
            db.add(project)
            db.commit()
            db.refresh(project)
            
            return CreateProjectMutation(project=project, success=True)
        
        except Exception as e:
            return CreateProjectMutation(success=False, error=str(e))


class UpdateTaskMutation(graphene.Mutation):
    """Update task mutation"""
    class Arguments:
        task_id = String(required=True)
        status = String()
        assignee_id = String()
        progress_percentage = Int()
    
    task = GraphQLField(lambda: TaskType)
    success = Boolean()
    error = String()
    
    async def mutate(self, info, task_id, status=None, assignee_id=None, progress_percentage=None):
        """Update task"""
        db = info.context['session']
        
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            return UpdateTaskMutation(success=False, error="Task not found")
        
        if status:
            task.status = status
        
        if assignee_id:
            task.assignee_id = assignee_id
        
        if progress_percentage is not None:
            task.progress_percentage = progress_percentage
        
        db.commit()
        db.refresh(task)
        
        return UpdateTaskMutation(task=task, success=True)


class Mutation(ObjectType):
    """GraphQL Mutations"""
    create_project = CreateProjectMutation.Field()
    update_task = UpdateTaskMutation.Field()


# Create schema
schema = graphene.Schema(query=Query, mutation=Mutation)


# Database Models for Export

class BulkExportJob(Base):
    """Bulk export job tracking"""
    __tablename__ = 'bulk_export_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Export details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Query
    entity_type = Column(String(50), nullable=False)  # projects, tasks, users, documents
    filters = Column(JSONB, default=dict)
    fields = Column(JSONB, default=list)
    
    # Format
    format = Column(String(20), default='json')  # json, csv, xlsx
    
    # Status
    status = Column(String(50), default='pending')
    progress_percentage = Column(Integer, default=0)
    
    # Results
    total_records = Column(Integer, nullable=True)
    exported_records = Column(Integer, default=0)
    
    # Output
    output_url = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class GraphQLQueryLog(Base):
    """GraphQL query logging"""
    __tablename__ = 'graphql_query_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Query details
    query = Column(Text, nullable=False)
    variables = Column(JSONB, nullable=True)
    operation_name = Column(String(255), nullable=True)
    
    # Performance
    execution_time_ms = Column(Integer, nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateExportJobRequest(BaseModel):
    """Create export job request"""
    name: str
    description: Optional[str] = None
    entity_type: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    fields: List[str] = Field(default_factory=list)
    format: str = 'json'
    expires_days: int = 7


class GraphQLRequest(BaseModel):
    """GraphQL request"""
    query: str
    variables: Optional[Dict[str, Any]] = None
    operation_name: Optional[str] = None


# Service Classes

class GraphQLService:
    """Service for GraphQL operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def execute_query(
        self,
        request: GraphQLRequest,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL query"""
        
        start_time = datetime.utcnow()
        
        # Execute query
        result = await schema.execute_async(
            request.query,
            variables=request.variables,
            operation_name=request.operation_name,
            context={'session': self.db, 'tenant_id': tenant_id, 'user_id': user_id},
            executor=AsyncioExecutor()
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log query
        self._log_query(
            tenant_id=tenant_id,
            user_id=user_id,
            query=request.query,
            variables=request.variables,
            operation_name=request.operation_name,
            execution_time_ms=int(execution_time),
            success=not result.errors,
            error_message=str(result.errors[0]) if result.errors else None
        )
        
        # Format response
        response = {
            'data': result.data
        }
        
        if result.errors:
            response['errors'] = [
                {'message': str(error)} for error in result.errors
            ]
        
        return response
    
    def _log_query(
        self,
        tenant_id: Optional[str],
        user_id: Optional[str],
        query: str,
        variables: Optional[Dict],
        operation_name: Optional[str],
        execution_time_ms: int,
        success: bool,
        error_message: Optional[str]
    ):
        """Log GraphQL query"""
        
        log = GraphQLQueryLog(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query[:10000],  # Limit size
            variables=variables,
            operation_name=operation_name,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )
        
        self.db.add(log)
        self.db.commit()


class BulkExportService:
    """Service for bulk data export"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_export_job(
        self,
        tenant_id: str,
        request: CreateExportJobRequest,
        created_by: Optional[str] = None
    ) -> BulkExportJob:
        """Create export job"""
        
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
        
        job = BulkExportJob(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            entity_type=request.entity_type,
            filters=request.filters,
            fields=request.fields,
            format=request.format,
            expires_at=expires_at,
            created_by=created_by
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def get_export_job(self, job_id: str) -> Optional[BulkExportJob]:
        """Get export job"""
        return self.db.query(BulkExportJob).filter(
            BulkExportJob.id == job_id
        ).first()
    
    async def execute_export(self, job_id: str):
        """Execute export job"""
        
        job = self.get_export_job(job_id)
        if not job:
            raise HTTPException(404, "Export job not found")
        
        job.status = 'processing'
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            # Query data
            data = await self._query_data(job)
            job.total_records = len(data)
            
            # Export to file
            if job.format == 'json':
                output = self._export_json(data, job.fields)
            elif job.format == 'csv':
                output = self._export_csv(data, job.fields)
            else:
                raise ValueError(f"Unsupported format: {job.format}")
            
            # Upload to storage
            output_url = await self._upload_output(job, output)
            
            job.output_url = output_url
            job.exported_records = len(data)
            job.file_size_bytes = len(output)
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
        
        self.db.commit()
    
    async def _query_data(self, job: BulkExportJob) -> List[Dict[str, Any]]:
        """Query data for export"""
        
        entity_type = job.entity_type
        filters = job.filters or {}
        
        if entity_type == 'projects':
            query = self.db.query(Project).filter(Project.tenant_id == job.tenant_id)
            
            if 'status' in filters:
                query = query.filter(Project.status == filters['status'])
            
            records = query.all()
            return [self._project_to_dict(p) for p in records]
        
        elif entity_type == 'tasks':
            query = self.db.query(Task).filter(Task.tenant_id == job.tenant_id)
            
            if 'project_id' in filters:
                query = query.filter(Task.project_id == filters['project_id'])
            
            if 'status' in filters:
                query = query.filter(Task.status == filters['status'])
            
            records = query.all()
            return [self._task_to_dict(t) for t in records]
        
        elif entity_type == 'users':
            query = self.db.query(User).filter(User.tenant_id == job.tenant_id)
            records = query.all()
            return [self._user_to_dict(u) for u in records]
        
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
    
    def _project_to_dict(self, project: Project) -> Dict[str, Any]:
        """Convert project to dict"""
        return {
            'id': str(project.id),
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'created_at': project.created_at.isoformat() if project.created_at else None
        }
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert task to dict"""
        return {
            'id': str(task.id),
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'assignee_id': str(task.assignee_id) if task.assignee_id else None,
            'due_date': task.due_date.isoformat() if task.due_date else None
        }
    
    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """Convert user to dict"""
        return {
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active
        }
    
    def _export_json(self, data: List[Dict], fields: List[str]) -> bytes:
        """Export data as JSON"""
        
        # Filter fields if specified
        if fields:
            data = [
                {k: v for k, v in item.items() if k in fields}
                for item in data
            ]
        
        return json.dumps(data, indent=2, default=str).encode('utf-8')
    
    def _export_csv(self, data: List[Dict], fields: List[str]) -> bytes:
        """Export data as CSV"""
        
        import csv
        
        output = io.StringIO()
        
        if data:
            # Use specified fields or all fields
            fieldnames = fields or list(data[0].keys())
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                row = {k: str(v) for k, v in item.items() if k in fieldnames}
                writer.writerow(row)
        
        return output.getvalue().encode('utf-8')
    
    async def _upload_output(self, job: BulkExportJob, data: bytes) -> str:
        """Upload export output to storage"""
        
        # In production, upload to S3
        # For now, return placeholder URL
        return f"s3://exports/{job.tenant_id}/{job.id}/export.{job.format}"


# Export
__all__ = [
    'ProjectType',
    'TaskType',
    'UserType',
    'DocumentType',
    'Query',
    'Mutation',
    'schema',
    'BulkExportJob',
    'GraphQLQueryLog',
    'CreateExportJobRequest',
    'GraphQLRequest',
    'GraphQLService',
    'BulkExportService'
]
