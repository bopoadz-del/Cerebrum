"""
Data Warehouse Schema
Star schema design with facts and dimensions
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ColumnType(Enum):
    """Column data types"""
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    DATE = 'date'
    TIMESTAMP = 'timestamp'
    DECIMAL = 'decimal'


@dataclass
class Column:
    """Table column definition"""
    name: str
    column_type: ColumnType
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    description: str = ''


@dataclass
class Table:
    """Table definition"""
    name: str
    columns: List[Column]
    description: str = ''
    partition_column: Optional[str] = None
    cluster_columns: List[str] = field(default_factory=list)


class DataWarehouseSchema:
    """Data warehouse schema definitions"""
    
    # Dimension Tables
    DIM_DATE = Table(
        name='dim_date',
        description='Date dimension',
        columns=[
            Column('date_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('full_date', ColumnType.DATE, nullable=False),
            Column('day_of_week', ColumnType.INTEGER),
            Column('day_name', ColumnType.STRING),
            Column('day_of_month', ColumnType.INTEGER),
            Column('day_of_year', ColumnType.INTEGER),
            Column('week_of_year', ColumnType.INTEGER),
            Column('month_number', ColumnType.INTEGER),
            Column('month_name', ColumnType.STRING),
            Column('quarter', ColumnType.INTEGER),
            Column('year', ColumnType.INTEGER),
            Column('fiscal_quarter', ColumnType.INTEGER),
            Column('is_weekend', ColumnType.BOOLEAN),
            Column('is_holiday', ColumnType.BOOLEAN),
        ]
    )
    
    DIM_USER = Table(
        name='dim_user',
        description='User dimension',
        columns=[
            Column('user_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('user_id', ColumnType.STRING, nullable=False),
            Column('email', ColumnType.STRING),
            Column('first_name', ColumnType.STRING),
            Column('last_name', ColumnType.STRING),
            Column('role', ColumnType.STRING),
            Column('department', ColumnType.STRING),
            Column('tenant_id', ColumnType.STRING),
            Column('created_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('is_active', ColumnType.BOOLEAN),
            Column('valid_from', ColumnType.TIMESTAMP),
            Column('valid_to', ColumnType.TIMESTAMP),
            Column('is_current', ColumnType.BOOLEAN),
        ]
    )
    
    DIM_TENANT = Table(
        name='dim_tenant',
        description='Tenant/Organization dimension',
        columns=[
            Column('tenant_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('tenant_id', ColumnType.STRING, nullable=False),
            Column('tenant_name', ColumnType.STRING),
            Column('plan', ColumnType.STRING),
            Column('industry', ColumnType.STRING),
            Column('company_size', ColumnType.STRING),
            Column('country', ColumnType.STRING),
            Column('created_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('valid_from', ColumnType.TIMESTAMP),
            Column('valid_to', ColumnType.TIMESTAMP),
            Column('is_current', ColumnType.BOOLEAN),
        ]
    )
    
    DIM_PROJECT = Table(
        name='dim_project',
        description='Project dimension',
        columns=[
            Column('project_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('project_id', ColumnType.STRING, nullable=False),
            Column('project_name', ColumnType.STRING),
            Column('project_type', ColumnType.STRING),
            Column('project_status', ColumnType.STRING),
            Column('tenant_key', ColumnType.INTEGER, foreign_key='dim_tenant.tenant_key'),
            Column('owner_user_key', ColumnType.INTEGER, foreign_key='dim_user.user_key'),
            Column('start_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('end_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('budget_amount', ColumnType.DECIMAL),
            Column('valid_from', ColumnType.TIMESTAMP),
            Column('valid_to', ColumnType.TIMESTAMP),
            Column('is_current', ColumnType.BOOLEAN),
        ]
    )
    
    DIM_TASK = Table(
        name='dim_task',
        description='Task dimension',
        columns=[
            Column('task_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('task_id', ColumnType.STRING, nullable=False),
            Column('task_name', ColumnType.STRING),
            Column('task_type', ColumnType.STRING),
            Column('priority', ColumnType.STRING),
            Column('project_key', ColumnType.INTEGER, foreign_key='dim_project.project_key'),
            Column('assignee_user_key', ColumnType.INTEGER, foreign_key='dim_user.user_key'),
            Column('created_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('due_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('valid_from', ColumnType.TIMESTAMP),
            Column('valid_to', ColumnType.TIMESTAMP),
            Column('is_current', ColumnType.BOOLEAN),
        ]
    )
    
    # Fact Tables
    FACT_USER_ACTIVITY = Table(
        name='fact_user_activity',
        description='User activity fact table',
        partition_column='date_key',
        cluster_columns=['tenant_key', 'user_key'],
        columns=[
            Column('activity_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('date_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_date.date_key'),
            Column('user_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_user.user_key'),
            Column('tenant_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_tenant.tenant_key'),
            Column('session_count', ColumnType.INTEGER),
            Column('page_views', ColumnType.INTEGER),
            Column('api_calls', ColumnType.INTEGER),
            Column('session_duration_minutes', ColumnType.FLOAT),
            Column('features_used', ColumnType.INTEGER),
            Column('documents_created', ColumnType.INTEGER),
            Column('documents_viewed', ColumnType.INTEGER),
        ]
    )
    
    FACT_PROJECT_METRICS = Table(
        name='fact_project_metrics',
        description='Project metrics fact table',
        partition_column='date_key',
        cluster_columns=['tenant_key', 'project_key'],
        columns=[
            Column('metric_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('date_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_date.date_key'),
            Column('project_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_project.project_key'),
            Column('tenant_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_tenant.tenant_key'),
            Column('total_tasks', ColumnType.INTEGER),
            Column('completed_tasks', ColumnType.INTEGER),
            Column('open_tasks', ColumnType.INTEGER),
            Column('overdue_tasks', ColumnType.INTEGER),
            Column('completion_percentage', ColumnType.FLOAT),
            Column('budget_used', ColumnType.DECIMAL),
            Column('budget_remaining', ColumnType.DECIMAL),
            Column('actual_cost', ColumnType.DECIMAL),
            Column('team_size', ColumnType.INTEGER),
        ]
    )
    
    FACT_TASK_COMPLETION = Table(
        name='fact_task_completion',
        description='Task completion fact table',
        partition_column='completion_date_key',
        cluster_columns=['tenant_key', 'project_key'],
        columns=[
            Column('completion_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('task_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_task.task_key'),
            Column('project_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_project.project_key'),
            Column('tenant_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_tenant.tenant_key'),
            Column('assignee_user_key', ColumnType.INTEGER, foreign_key='dim_user.user_key'),
            Column('created_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('due_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('completion_date_key', ColumnType.INTEGER, foreign_key='dim_date.date_key'),
            Column('planned_duration_days', ColumnType.INTEGER),
            Column('actual_duration_days', ColumnType.INTEGER),
            Column('is_on_time', ColumnType.BOOLEAN),
            Column('delay_days', ColumnType.INTEGER),
        ]
    )
    
    FACT_BILLING = Table(
        name='fact_billing',
        description='Billing and revenue fact table',
        partition_column='date_key',
        cluster_columns=['tenant_key'],
        columns=[
            Column('billing_key', ColumnType.INTEGER, nullable=False, primary_key=True),
            Column('date_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_date.date_key'),
            Column('tenant_key', ColumnType.INTEGER, nullable=False, foreign_key='dim_tenant.tenant_key'),
            Column('mrr_amount', ColumnType.DECIMAL),
            Column('arr_amount', ColumnType.DECIMAL),
            Column('new_subscriptions', ColumnType.INTEGER),
            Column('churned_subscriptions', ColumnType.INTEGER),
            Column('upgrades', ColumnType.INTEGER),
            Column('downgrades', ColumnType.INTEGER),
            Column('user_count', ColumnType.INTEGER),
            Column('project_count', ColumnType.INTEGER),
            Column('storage_gb', ColumnType.FLOAT),
        ]
    )
    
    @classmethod
    def get_all_tables(cls) -> List[Table]:
        """Get all schema tables"""
        return [
            cls.DIM_DATE,
            cls.DIM_USER,
            cls.DIM_TENANT,
            cls.DIM_PROJECT,
            cls.DIM_TASK,
            cls.FACT_USER_ACTIVITY,
            cls.FACT_PROJECT_METRICS,
            cls.FACT_TASK_COMPLETION,
            cls.FACT_BILLING,
        ]
    
    @classmethod
    def get_table(cls, name: str) -> Optional[Table]:
        """Get table by name"""
        for table in cls.get_all_tables():
            if table.name == name:
                return table
        return None
    
    @classmethod
    def generate_ddl(cls, table: Table, dialect: str = 'bigquery') -> str:
        """Generate DDL for table"""
        columns_ddl = []
        
        for col in table.columns:
            # Map column types
            type_mapping = {
                'bigquery': {
                    ColumnType.STRING: 'STRING',
                    ColumnType.INTEGER: 'INT64',
                    ColumnType.FLOAT: 'FLOAT64',
                    ColumnType.BOOLEAN: 'BOOL',
                    ColumnType.DATE: 'DATE',
                    ColumnType.TIMESTAMP: 'TIMESTAMP',
                    ColumnType.DECIMAL: 'NUMERIC',
                },
                'postgresql': {
                    ColumnType.STRING: 'VARCHAR(255)',
                    ColumnType.INTEGER: 'INTEGER',
                    ColumnType.FLOAT: 'DOUBLE PRECISION',
                    ColumnType.BOOLEAN: 'BOOLEAN',
                    ColumnType.DATE: 'DATE',
                    ColumnType.TIMESTAMP: 'TIMESTAMP',
                    ColumnType.DECIMAL: 'DECIMAL(18,2)',
                }
            }
            
            sql_type = type_mapping.get(dialect, type_mapping['postgresql']).get(col.column_type, 'TEXT')
            
            nullable = 'NULL' if col.nullable else 'NOT NULL'
            pk = 'PRIMARY KEY' if col.primary_key else ''
            
            columns_ddl.append(f"    {col.name} {sql_type} {nullable} {pk}")
        
        ddl = f"CREATE TABLE {table.name} (\n"
        ddl += ',\n'.join(columns_ddl)
        ddl += "\n)"
        
        # Add partitioning for BigQuery
        if dialect == 'bigquery' and table.partition_column:
            ddl += f"\nPARTITION BY {table.partition_column}"
        
        return ddl
