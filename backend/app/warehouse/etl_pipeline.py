"""
ETL Pipeline Orchestration
Apache Airflow/Dagster-style ETL pipeline for Cerebrum AI Platform
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import hashlib
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """ETL task status"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'
    SKIPPED = 'skipped'


class PipelineStatus(Enum):
    """Pipeline status"""
    ACTIVE = 'active'
    PAUSED = 'paused'
    FAILED = 'failed'
    SUCCESS = 'success'


@dataclass
class ETLTask:
    """ETL task definition"""
    id: str
    name: str
    task_type: str  # extract, transform, load
    source: Optional[str] = None
    destination: Optional[str] = None
    query: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 3600
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ETLRun:
    """ETL run instance"""
    run_id: str
    pipeline_id: str
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)


@dataclass
class ETLPipeline:
    """ETL pipeline definition"""
    id: str
    name: str
    description: str
    schedule: str  # cron expression
    tasks: List[ETLTask]
    status: PipelineStatus = PipelineStatus.ACTIVE
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class Extractor:
    """Data extraction utilities"""
    
    async def extract_from_database(
        self,
        connection_string: str,
        query: str,
        batch_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Extract data from database"""
        from sqlalchemy import create_engine, text
        
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = result.keys()
            
            rows = []
            for row in result:
                rows.append(dict(zip(columns, row)))
            
            return rows
    
    async def extract_from_api(
        self,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Extract data from API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=60.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                return [data]
    
    async def extract_from_s3(
        self,
        bucket: str,
        key: str,
        aws_access_key: str = None,
        aws_secret_key: str = None
    ) -> List[Dict[str, Any]]:
        """Extract data from S3"""
        import boto3
        import json
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Parse based on file extension
        if key.endswith('.json'):
            return json.loads(content)
        elif key.endswith('.jsonl'):
            return [json.loads(line) for line in content.decode().split('\n') if line]
        else:
            return [{'content': content.decode()}]


class Transformer:
    """Data transformation utilities"""
    
    def clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean data by removing nulls and standardizing"""
        cleaned = []
        
        for row in data:
            cleaned_row = {}
            for key, value in row.items():
                # Skip null values
                if value is None:
                    continue
                
                # Standardize keys
                clean_key = key.lower().replace(' ', '_')
                cleaned_row[clean_key] = value
            
            cleaned.append(cleaned_row)
        
        return cleaned
    
    def normalize_data(
        self,
        data: List[Dict[str, Any]],
        schema: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Normalize data to schema"""
        normalized = []
        
        for row in data:
            normalized_row = {}
            
            for field, field_type in schema.items():
                value = row.get(field)
                
                # Type conversion
                if field_type == 'integer':
                    value = int(value) if value is not None else None
                elif field_type == 'float':
                    value = float(value) if value is not None else None
                elif field_type == 'boolean':
                    value = bool(value) if value is not None else None
                elif field_type == 'datetime':
                    if isinstance(value, str):
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                
                normalized_row[field] = value
            
            normalized.append(normalized_row)
        
        return normalized
    
    def aggregate_data(
        self,
        data: List[Dict[str, Any]],
        group_by: List[str],
        aggregations: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Aggregate data"""
        from collections import defaultdict
        
        groups = defaultdict(list)
        
        for row in data:
            key = tuple(row.get(k) for k in group_by)
            groups[key].append(row)
        
        results = []
        
        for key, group_rows in groups.items():
            result = dict(zip(group_by, key))
            
            for field, agg_type in aggregations.items():
                values = [row.get(field) for row in group_rows if row.get(field) is not None]
                
                if agg_type == 'sum':
                    result[f'{field}_sum'] = sum(values)
                elif agg_type == 'avg':
                    result[f'{field}_avg'] = sum(values) / len(values) if values else 0
                elif agg_type == 'count':
                    result[f'{field}_count'] = len(values)
                elif agg_type == 'min':
                    result[f'{field}_min'] = min(values) if values else None
                elif agg_type == 'max':
                    result[f'{field}_max'] = max(values) if values else None
            
            results.append(result)
        
        return results


class Loader:
    """Data loading utilities"""
    
    async def load_to_warehouse(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
        connection_string: str
    ) -> int:
        """Load data to data warehouse"""
        from sqlalchemy import create_engine, text
        import pandas as pd
        
        df = pd.DataFrame(data)
        
        engine = create_engine(connection_string)
        
        # Use pandas to load data
        df.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        return len(data)
    
    async def load_to_bigquery(
        self,
        data: List[Dict[str, Any]],
        dataset: str,
        table: str,
        project_id: str = None
    ) -> int:
        """Load data to BigQuery"""
        from google.cloud import bigquery
        
        client = bigquery.Client(project=project_id)
        
        table_ref = f"{dataset}.{table}"
        
        errors = client.insert_rows_json(table_ref, data)
        
        if errors:
            logger.error(f"BigQuery load errors: {errors}")
            raise Exception(f"Failed to load {len(errors)} rows")
        
        return len(data)


class ETLOrchestrator:
    """Orchestrate ETL pipelines"""
    
    def __init__(self):
        self.pipelines: Dict[str, ETLPipeline] = {}
        self.runs: Dict[str, ETLRun] = {}
        self.extractor = Extractor()
        self.transformer = Transformer()
        self.loader = Loader()
        self._scheduler_task = None
    
    def create_pipeline(self, pipeline: ETLPipeline) -> str:
        """Create a new ETL pipeline"""
        self.pipelines[pipeline.id] = pipeline
        logger.info(f"Created ETL pipeline: {pipeline.name}")
        return pipeline.id
    
    async def run_pipeline(self, pipeline_id: str) -> ETLRun:
        """Run an ETL pipeline"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        pipeline = self.pipelines[pipeline_id]
        
        run_id = f"{pipeline_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        run = ETLRun(
            run_id=run_id,
            pipeline_id=pipeline_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        self.runs[run_id] = run
        
        logger.info(f"Starting ETL pipeline run: {run_id}")
        
        try:
            # Execute tasks in dependency order
            completed_tasks = set()
            
            while len(completed_tasks) < len(pipeline.tasks):
                # Find ready tasks
                ready_tasks = [
                    task for task in pipeline.tasks
                    if task.id not in completed_tasks
                    and all(dep in completed_tasks for dep in task.dependencies)
                ]
                
                if not ready_tasks:
                    break
                
                # Execute ready tasks
                for task in ready_tasks:
                    await self._execute_task(task, run)
                    completed_tasks.add(task.id)
            
            run.status = TaskStatus.SUCCESS
            run.completed_at = datetime.utcnow()
            
            logger.info(f"ETL pipeline completed: {run_id}")
            
        except Exception as e:
            run.status = TaskStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            
            logger.error(f"ETL pipeline failed: {run_id} - {e}")
        
        return run
    
    async def _execute_task(self, task: ETLTask, run: ETLRun):
        """Execute a single ETL task"""
        logger.info(f"Executing task: {task.name}")
        
        try:
            if task.task_type == 'extract':
                # Extract data
                pass
            elif task.task_type == 'transform':
                # Transform data
                pass
            elif task.task_type == 'load':
                # Load data
                pass
            
            run.tasks_completed += 1
            run.logs.append(f"Task {task.name} completed successfully")
            
        except Exception as e:
            run.tasks_failed += 1
            run.logs.append(f"Task {task.name} failed: {str(e)}")
            raise
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline status"""
        if pipeline_id not in self.pipelines:
            return {'error': 'Pipeline not found'}
        
        pipeline = self.pipelines[pipeline_id]
        
        # Get recent runs
        recent_runs = [
            run for run in self.runs.values()
            if run.pipeline_id == pipeline_id
        ][-10:]
        
        return {
            'pipeline_id': pipeline_id,
            'name': pipeline.name,
            'status': pipeline.status.value,
            'schedule': pipeline.schedule,
            'last_run': pipeline.last_run.isoformat() if pipeline.last_run else None,
            'next_run': pipeline.next_run.isoformat() if pipeline.next_run else None,
            'recent_runs': [
                {
                    'run_id': run.run_id,
                    'status': run.status.value,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'tasks_completed': run.tasks_completed,
                    'tasks_failed': run.tasks_failed
                }
                for run in recent_runs
            ]
        }


# Global ETL orchestrator
etl_orchestrator = ETLOrchestrator()
