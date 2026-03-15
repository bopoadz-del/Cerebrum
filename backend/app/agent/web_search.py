"""
Web Search Tool for Cerebrum Agent
Uses Brave Search API - safe, no file data leakage
"""

import os
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


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
    Web search tool for agent.
    
    SAFETY NOTES:
    - Only sends SEARCH QUERY to Brave API
    - NEVER sends file contents or conversation data
    - All searches logged for audit
    - Can be disabled via WEB_SEARCH_ENABLED=false
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.enabled = os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true"
        
    async def search(
        self,
        query: str,
        count: int = 5,
        country: str = "US",
        freshness: Optional[str] = None
    ) -> WebSearchResponse:
        """
        Perform web search.
        
        Args:
            query: Search query (ONLY this goes to web)
            count: Number of results (1-20)
            country: Country code for results
            freshness: 'pd' (24h), 'pw' (week), 'pm' (month), 'py' (year)
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
        
        # Check API key
        if not self.api_key:
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=0,
                success=False,
                error="Web search not configured (missing BRAVE_API_KEY)"
            )
        
        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": min(count, 20),
                "country": country,
                "search_lang": "en"
            }
            
            if freshness:
                params["freshness"] = freshness
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    BRAVE_API_URL,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            # Parse results
            results = []
            web_results = data.get("web", {}).get("results", [])
            
            for item in web_results[:count]:
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    source=item.get("meta", {}).get("domain", ""),
                    published_date=item.get("age")
                ))
            
            search_time = (time.time() - start_time) * 1000
            
            # Log for audit
            logger.info(
                "Web search performed",
                extra={
                    "query": query[:100],  # Truncate for logs
                    "results_count": len(results),
                    "search_time_ms": search_time
                }
            )
            
            return WebSearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
                success=True
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Web search HTTP error: {e}")
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error=f"Search API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return WebSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error=f"Unexpected error: {str(e)}"
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
