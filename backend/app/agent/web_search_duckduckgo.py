"""
Web Search Tool using DuckDuckGo - FREE, no API key required
Uses DeepSeek for result analysis
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import asyncio
from duckduckgo_search import DDGS

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
    - Rate limited but generous (unofficial API)
    - Safe - only sends search query
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # No API key needed for DuckDuckGo
        self.enabled = True
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


# Singleton instance
_web_search_tool: Optional[WebSearchTool] = None


def get_web_search_tool() -> WebSearchTool:
    """Get or create web search tool instance."""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool()
    return _web_search_tool


async def web_search(query: str, count: int = 5) -> WebSearchResponse:
    """Convenience function for web search."""
    tool = get_web_search_tool()
    return await tool.search(query, count=count)
