"""
Web Search Endpoints for Agent
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agent.web_search import get_web_search_tool, WebSearchResponse

router = APIRouter(prefix="/web-search", tags=["web-search"])


class WebSearchRequest(BaseModel):
    query: str
    count: int = 5
    country: str = "US"
    freshness: Optional[str] = None  # pd, pw, pm, py


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    description: str
    source: str
    published_date: Optional[str] = None


class WebSearchResponseModel(BaseModel):
    query: str
    results: list[WebSearchResultItem]
    total_results: int
    search_time_ms: float
    success: bool
    error: Optional[str] = None


@router.post("/search", response_model=WebSearchResponseModel)
async def web_search(request: WebSearchRequest):
    """
    Perform web search.
    
    Only the search query is sent to Brave Search API.
    No file contents or conversation data is transmitted.
    """
    tool = get_web_search_tool()
    
    result = await tool.search(
        query=request.query,
        count=request.count,
        country=request.country,
        freshness=request.freshness
    )
    
    return WebSearchResponseModel(
        query=result.query,
        results=[
            WebSearchResultItem(
                title=r.title,
                url=r.url,
                description=r.description,
                source=r.source,
                published_date=r.published_date
            )
            for r in result.results
        ],
        total_results=result.total_results,
        search_time_ms=result.search_time_ms,
        success=result.success,
        error=result.error
    )


@router.get("/status")
async def web_search_status():
    """Check if web search is enabled and configured."""
    import os
    return {
        "enabled": os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true",
        "configured": bool(os.getenv("BRAVE_API_KEY")),
        "provider": "Brave Search"
    }
