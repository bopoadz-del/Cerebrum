"""
ZVec Service - Real vector DB for semantic search
"""
import uuid
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

class ZVecService:
    """ZVec vector database service for semantic search."""
    
    def __init__(self, db=None):
        self.db = db
        self._client = None
        self._index = None
        self.is_available = False
        self._init_zvec()
    
    def _init_zvec(self):
        """Initialize real ZVec client."""
        try:
            import zvec
            # Create data directory
            data_dir = os.getenv("ZVEC_DATA_DIR", "/app/data/zvec")
            os.makedirs(data_dir, exist_ok=True)
            
            # Initialize client
            self._client = zvec.Client(data_dir)
            
            # Get or create index for documents
            self._index = self._client.get_or_create_index(
                name="documents",
                dimension=384,
                metric="cosine"
            )
            
            logger.info("✅ ZVec initialized successfully")
            self.is_available = True
            
        except ImportError as e:
            logger.warning(f"ZVec import failed: {e}")
            self.is_available = False
        except Exception as e:
            logger.error(f"ZVec init failed: {e}")
            self.is_available = False
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self.is_available
    
    async def index_document(self, doc_id: str, content: str, metadata: Dict) -> bool:
        """Index a single document."""
        if not self.is_available:
            logger.debug("ZVec not available, skipping indexing")
            return False
        
        try:
            # Generate embedding
            embedding = self._generate_embedding(content)
            
            # Store in ZVec
            self._index.upsert(
                id=doc_id,
                vector=embedding,
                metadata=metadata
            )
            logger.info(f"✅ Indexed: {metadata.get('name', doc_id)}")
            return True
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return False
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Semantic search."""
        if not self.is_available:
            return []
        
        try:
            query_vec = self._generate_embedding(query)
            results = self._index.search(vector=query_vec, top_k=top_k)
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Synchronous semantic search (for backward compat)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.search(query, top_k))
        except:
            return []
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """Synchronous add document (for backward compat)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.index_document(doc_id, text, metadata))
        except:
            return False
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Use hash-based deterministic embedding for now
        # In production, use sentence-transformers
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val % 1000) / 1000.0 for _ in range(384)]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing stats."""
        if not self.is_available:
            return {"status": "offline", "total_vectors": 0}
        
        try:
            stats = self._index.stats()
            return {
                "status": "active",
                "total_vectors": stats.get("total_vectors", 0),
                "dimension": 384
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_stats_sync(self) -> Dict[str, Any]:
        """Synchronous get stats (for backward compat)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_stats())
        except:
            return {"status": "error", "count": 0}


# Global singleton instance
_zvec_service_instance = None

def get_zvec_service(db=None):
    """Get global ZVec service instance."""
    global _zvec_service_instance
    if _zvec_service_instance is None:
        _zvec_service_instance = ZVecService(db)
    return _zvec_service_instance


# Backward compatibility
ZVecIndexingService = ZVecService
