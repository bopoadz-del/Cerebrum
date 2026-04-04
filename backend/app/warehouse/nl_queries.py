"""
Natural Language to SQL
GPT-4 powered natural language query interface
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

import httpx
import openai

from app.core.config import settings
from app.warehouse.schema import DataWarehouseSchema

logger = logging.getLogger(__name__)


@dataclass
class NLQueryResult:
    """Natural language query result"""
    query: str
    sql: str
    results: List[Dict[str, Any]]
    execution_time_ms: float
    row_count: int
    explanation: str
    suggested_queries: List[str] = field(default_factory=list)


@dataclass
class QueryIntent:
    """Parsed query intent"""
    intent_type: str  # aggregation, comparison, trend, list
    metrics: List[str]
    dimensions: List[str]
    filters: List[Dict[str, Any]]
    time_range: Optional[str]
    sort_by: Optional[str]
    limit: Optional[int]


class NLQueryEngine:
    """Natural language to SQL query engine"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.schema = DataWarehouseSchema()
        self.query_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def _get_schema_context(self) -> str:
        """Get schema context for GPT"""
        tables = self.schema.get_all_tables()
        
        context = "Database Schema:\n\n"
        
        for table in tables:
            context += f"Table: {table.name}\n"
            context += f"Description: {table.description}\n"
            context += "Columns:\n"
            
            for col in table.columns:
                pk = " (PRIMARY KEY)" if col.primary_key else ""
                fk = f" (FOREIGN KEY -> {col.foreign_key})" if col.foreign_key else ""
                context += f"  - {col.name}: {col.column_type.value}{pk}{fk}\n"
            
            context += "\n"
        
        return context
    
    def _get_sample_queries(self) -> str:
        """Get sample queries for context"""
        return """
Sample Queries:

Q: "Show me total revenue by month for the last year"
SQL: SELECT DATE_TRUNC('month', date) as month, SUM(mrr_amount) as revenue 
     FROM fact_billing 
     WHERE date >= DATE_SUB(CURRENT_DATE, INTERVAL 1 YEAR)
     GROUP BY month 
     ORDER BY month

Q: "What are the top 10 customers by project count?"
SQL: SELECT t.tenant_name, COUNT(p.project_key) as project_count
     FROM dim_tenant t
     JOIN dim_project p ON t.tenant_key = p.tenant_key
     GROUP BY t.tenant_name
     ORDER BY project_count DESC
     LIMIT 10

Q: "Show me user activity trend for the last 30 days"
SQL: SELECT date_key, SUM(session_count) as sessions, SUM(page_views) as page_views
     FROM fact_user_activity
     WHERE date_key >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
     GROUP BY date_key
     ORDER BY date_key
"""
    
    async def parse_query(self, natural_language: str) -> QueryIntent:
        """Parse natural language query to intent"""
        # Use GPT to parse intent
        prompt = f"""
Parse the following natural language query into structured intent.

Query: "{natural_language}"

Extract and return JSON with:
- intent_type: aggregation, comparison, trend, list, or count
- metrics: list of metrics being requested
- dimensions: list of grouping dimensions
- filters: list of filter conditions
- time_range: time period mentioned
- sort_by: sorting preference
- limit: result limit

Return only valid JSON."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a query parsing assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            
            return QueryIntent(
                intent_type=parsed.get('intent_type', 'list'),
                metrics=parsed.get('metrics', []),
                dimensions=parsed.get('dimensions', []),
                filters=parsed.get('filters', []),
                time_range=parsed.get('time_range'),
                sort_by=parsed.get('sort_by'),
                limit=parsed.get('limit')
            )
        
        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            return QueryIntent(
                intent_type='list',
                metrics=[],
                dimensions=[],
                filters=[],
                time_range=None,
                sort_by=None,
                limit=None
            )
    
    async def generate_sql(self, natural_language: str) -> str:
        """Generate SQL from natural language"""
        schema_context = self._get_schema_context()
        sample_queries = self._get_sample_queries()
        
        prompt = f"""{schema_context}

{sample_queries}

Convert the following natural language query to SQL:
"{natural_language}"

Requirements:
- Use only the tables and columns defined in the schema
- Use proper JOINs when combining tables
- Add appropriate WHERE clauses for filtering
- Use aggregation functions (SUM, COUNT, AVG) when needed
- Add ORDER BY for sorted results
- Use LIMIT when appropriate
- Return only the SQL query, no explanation

SQL:"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate valid, optimized SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up SQL
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            return sql
        
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return ""
    
    async def execute_query(self, sql: str) -> Tuple[List[Dict[str, Any]], float, int]:
        """Execute SQL query and return results"""
        import time
        from google.cloud import bigquery
        
        start_time = time.time()
        
        try:
            client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            
            query_job = client.query(sql)
            results = query_job.result()
            
            rows = [dict(row) for row in results]
            
            execution_time = (time.time() - start_time) * 1000
            
            return rows, execution_time, len(rows)
        
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return [], 0, 0
    
    async def generate_explanation(self, natural_language: str, sql: str) -> str:
        """Generate explanation of the query"""
        prompt = f"""
Explain this SQL query in simple terms:

Original Question: "{natural_language}"

SQL Query:
{sql}

Provide a brief, clear explanation of what this query does."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You explain SQL queries in simple terms."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return ""
    
    async def suggest_queries(self, context: str = None) -> List[str]:
        """Suggest related queries"""
        suggestions = [
            "Show me revenue by customer segment",
            "What are the top 10 most active users?",
            "Show me project completion rates by month",
            "Compare user activity this month vs last month",
            "What is the average project duration?",
            "Show me customer churn by industry"
        ]
        
        return suggestions[:6]
    
    async def query(self, natural_language: str) -> NLQueryResult:
        """Execute natural language query"""
        logger.info(f"Processing NL query: {natural_language}")
        
        # Generate SQL
        sql = await self.generate_sql(natural_language)
        
        if not sql:
            return NLQueryResult(
                query=natural_language,
                sql="",
                results=[],
                execution_time_ms=0,
                row_count=0,
                explanation="Could not generate SQL query",
                suggested_queries=[]
            )
        
        # Execute query
        results, execution_time, row_count = await self.execute_query(sql)
        
        # Generate explanation
        explanation = await self.generate_explanation(natural_language, sql)
        
        # Suggest related queries
        suggestions = await self.suggest_queries()
        
        # Store in history
        self.query_history.append({
            'query': natural_language,
            'sql': sql,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return NLQueryResult(
            query=natural_language,
            sql=sql,
            results=results,
            execution_time_ms=execution_time,
            row_count=row_count,
            explanation=explanation,
            suggested_queries=suggestions
        )
    
    def validate_sql(self, sql: str) -> Tuple[bool, str]:
        """Validate generated SQL"""
        # Check for basic SQL injection patterns
        dangerous_patterns = [
            r';\s*DROP\s+',
            r';\s*DELETE\s+',
            r';\s*UPDATE\s+.*\s+SET\s+',
            r'UNION\s+SELECT',
            r'--',
            r'/\*',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"Potentially dangerous pattern detected: {pattern}"
        
        # Check for required clauses
        if not re.search(r'\bSELECT\b', sql, re.IGNORECASE):
            return False, "Query must contain SELECT"
        
        if not re.search(r'\bFROM\b', sql, re.IGNORECASE):
            return False, "Query must contain FROM"
        
        return True, "Valid SQL"


# Global NL query engine
nl_query_engine = NLQueryEngine()
