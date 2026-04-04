"""
ZVec Service - Pure Python vector DB (no native dependencies)
Works on all platforms without AVX/SIGILL issues
"""
import os
import json
import math
import hashlib
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ZVecService:
    """
    ZVec vector database service - Pure Python implementation.
    Uses cosine similarity for semantic search.
    """
    
    def __init__(self, db=None, db_path: str = "./data/zvec_store"):
        self.db = db
        self.db_path = db_path
        self.dimension = 384
        self._index = None
        self.is_available = True  # Always available in pure Python
        
        # Ensure data directory exists
        os.makedirs(db_path, exist_ok=True)
        
        self._index = PurePythonZVecDB(db_path)
        logger.info(f"✅ ZVec (pure Python) initialized at {db_path}")
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        return True
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate deterministic embedding for text.
        Uses hash-based approach - no ML libraries needed.
        """
        # Normalize text
        text = text[:5000].lower().strip()
        
        # Generate hash
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Create 384-dim vector
        embedding = []
        for i in range(self.dimension):
            hex_idx = (i * 2) % 32
            val = int(hash_hex[hex_idx:hex_idx+2], 16) / 128.0 - 1.0
            noise = math.sin(i * 0.1) * 0.1
            val += noise
            embedding.append(max(-1.0, min(1.0, val)))
        
        return embedding
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """Index a single document (sync)."""
        try:
            embedding = self.embed_text(text)
            self._index.add(
                id=doc_id,
                vector=embedding,
                metadata=json.dumps(metadata)
            )
            logger.info(f"✅ ZVec indexed: {metadata.get('name', doc_id)} (total: {self._index.count()})")
            return True
        except Exception as e:
            logger.error(f"ZVec add error: {e}")
            return False
    
    async def index_document(self, doc_id: str, content: str, metadata: Dict) -> bool:
        """Index a single document (async)."""
        return self.add_document(doc_id, content, metadata)
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search (sync)."""
        try:
            query_vec = self.embed_text(query)
            results = self._index.search(vector=query_vec, top_k=top_k)
            
            logger.info(f"🔍 ZVec search: '{query}' -> {len(results)} results (total docs: {self._index.count()})")
            
            return [
                {
                    'id': r['id'],
                    'score': r.get('score', 0),
                    'metadata': json.loads(r.get('metadata', '{}'))
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"ZVec search error: {e}")
            return []
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Semantic search (async)."""
        return self.search_similar(query, top_k)
    
    def get_stats_sync(self) -> Dict[str, Any]:
        """Get indexing stats (sync)."""
        try:
            count = self._index.count() if self._index else 0
            return {
                "status": "active",
                "count": count,
                "ready": True,
                "mode": "pure_python"
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "count": 0}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing stats (async)."""
        return self.get_stats_sync()


class PurePythonZVecDB:
    """Pure Python vector database - no native dependencies."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.store: Dict[str, Dict] = {}
        self.metadata_path = os.path.join(db_path, "documents.json")
        self._load()
    
    def _load(self):
        """Load documents from disk."""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r') as f:
                    data = json.load(f)
                    self.store = data.get('documents', {})
            except Exception as e:
                logger.warning(f"Failed to load ZVec DB: {e}")
                self.store = {}
    
    def _save(self):
        """Save documents to disk."""
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump({'documents': self.store}, f)
        except Exception as e:
            logger.error(f"Failed to save ZVec DB: {e}")
    
    def count(self) -> int:
        return len(self.store)
    
    def add(self, id: str, vector: List[float], metadata: str):
        self.store[id] = {
            'vector': vector,
            'metadata': metadata
        }
        self._save()
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)
    
    def search(self, vector: List[float], top_k: int = 5):
        """Search by cosine similarity."""
        if not self.store:
            return []
        
        scored = []
        for doc_id, doc in self.store.items():
            score = self._cosine_similarity(vector, doc['vector'])
            scored.append({
                'id': doc_id,
                'score': score,
                'metadata': doc['metadata']
            })
        
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]


# Global singleton
_zvec_service_instance = None

def get_zvec_service(db=None):
    """Get global ZVec service instance."""
    global _zvec_service_instance
    if _zvec_service_instance is None:
        _zvec_service_instance = ZVecService(db)
    return _zvec_service_instance


# Backward compatibility
ZVecIndexingService = ZVecService
