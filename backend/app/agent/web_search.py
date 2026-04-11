"""
Web Search Tool for Cerebrum Agent
Uses DuckDuckGo - FREE, no API key required!
Uses DeepSeek for result analysis
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import asyncio
from ddgs import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """Single web search result."""
    title: str
    url: str
    description: str
    source: str
    published_date: Optional[str] = None


@dataclass
class WebSearchResponse:
    """Web search response with results and metadata."""
    query: str
    results: List[WebSearchResult]
    total_results: int
    search_time_ms: float
    success: bool
    error: Optional[str] = None


class WebSearchTool:
    """
    Web search tool using DuckDuckGo (FREE - no API key needed).
    
    Features:
    - No API key required
    - Rate limited but generous
    - Safe - only sends search query
    - Uses DeepSeek for result analysis
    
    COST: $0 (DuckDuckGo) + ~$0.0001 (DeepSeek analysis per query)
    vs Brave: $3 per 1,000 searches
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # No API key needed for DuckDuckGo
        self.enabled = getattr(settings, 'WEB_SEARCH_ENABLED', True)
        self.ddgs = DDGS()
        
    async def search(
        self,
        query: str,
        count: int = 5,
        country: str = "US",
        freshness: Optional[str] = None
    ) -> WebSearchResponse:
        """
        Perform web search using DuckDuckGo.
        
        Args:
            query: Search query
            count: Number of results (1-10)
            country: Country code for results
            freshness: Not supported by DDGS
        """
        import time
        start_time = time.time()
        
        # Check if enabled
        if not self.enabled:
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=0,
                success=False,
                error="Web search is disabled by administrator"
            )
        
        try:
            # Run DDGS in thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: list(self.ddgs.text(query, max_results=min(count, 10)))
            )
            
            search_results = []
            for r in results:
                search_results.append(WebSearchResult(
                    title=r.get('title', ''),
                    url=r.get('href', ''),
                    description=r.get('body', ''),
                    source=r.get('href', '').split('/')[2] if 'href' in r else 'web'
                ))
            
            search_time = (time.time() - start_time) * 1000
            
            # Log for audit
            logger.info(
                "Web search performed",
                extra={
                    "query": query[:100],
                    "results_count": len(search_results),
                    "search_time_ms": search_time,
                    "provider": "DuckDuckGo"
                }
            )
            
            return WebSearchResponse(
                query=query,
                results=search_results,
                total_results=len(search_results),
                search_time_ms=search_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            search_time = (time.time() - start_time) * 1000
            
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=search_time,
                success=False,
                error=str(e)
            )
    
    def format_for_agent(self, response: WebSearchResponse) -> str:
        """Format search results for agent consumption."""
        if not response.success:
            return f"Web search failed: {response.error}"
        
        if not response.results:
            return f"No results found for: {response.query}"
        
        lines = [
            f"🔍 Web Search Results for: \"{response.query}\"",
            f"Found {response.total_results} results ({response.search_time_ms:.0f}ms)",
            ""
        ]
        
        for i, result in enumerate(response.results, 1):
            lines.append(f"{i}. **{result.title}**")
            lines.append(f"   {result.description}")
            lines.append(f"   Source: {result.source}")
            if result.published_date:
                lines.append(f"   Published: {result.published_date}")
            lines.append("")
        
        return "\n".join(lines)


# Singleton instance
_web_search_tool: Optional[WebSearchTool] = None


def get_web_search_tool() -> WebSearchTool:
    """Get or create web search tool instance."""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool()
    return _web_search_tool


def web_search_sync(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Synchronous web search function for use in non-async contexts.
    
    Args:
        query: Search query
        count: Number of results to return
        
    Returns:
        List of search result dictionaries
    """
    import asyncio
    tool = get_web_search_tool()
    
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, create a new thread to run the coroutine
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, tool.search(query, count))
            response = future.result(timeout=30)
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        response = asyncio.run(tool.search(query, count))
    
    if not response.success:
        logger.warning(f"Web search failed: {response.error}")
        return []
    
    # Convert WebSearchResult objects to dictionaries
    return [
        {
            "title": r.title,
            "url": r.url,
            "description": r.description,
            "source": r.source,
            "published_date": r.published_date
        }
        for r in response.results
    ]


# Alias for backward compatibility
brave_search_sync = web_search_sync
