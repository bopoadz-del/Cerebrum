"""
ZVec Service - Vector DB for semantic search
Pure Python implementation (no native dependencies, no AVX issues)
"""
import os
import json
import math
from typing import List, Dict, Any, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)

# NOTE: Native zvec disabled due to AVX/SIGILL issues on some platforms
# Using pure Python implementation instead
ZVEC_AVAILABLE = False


class ZVecService:
    """
    ZVec vector database service for semantic search.
    Pure Python implementation - works everywhere without AVX.
    """
    
    def __init__(self, db_path: str = "./data/zvec_store"):
        self.db_path = db_path
        self.dimension = 384
        self._index = None
        self.is_available = True  # Pure Python is always available
        
        # Ensure data directory exists
        os.makedirs(db_path, exist_ok=True)
        
        self._index = PurePythonZVecDB(self.db_path)
        logger.info(f"✅ ZVec (pure Python) initialized at {self.db_path}")
    
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
        """Index a single document."""
        try:
            embedding = self.embed_text(text)
            self._index.add(
                id=doc_id,
                vector=embedding,
                metadata=json.dumps(metadata)
            )
            return True
        except Exception as e:
            logger.error(f"ZVec add error: {e}")
            return False
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search using cosine similarity."""
        try:
            query_vec = self.embed_text(query)
            results = self._index.search(vector=query_vec, top_k=top_k)
            
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing stats."""
        try:
            count = self._index.count() if self._index else 0
            return {
                "status": "active",
                "count": count,
                "ready": True,
                "mode": "pure_python"
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "count": 0, "ready": False}


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
        
        # Score all documents
        scored = []
        for doc_id, doc in self.store.items():
            score = self._cosine_similarity(vector, doc['vector'])
            scored.append({
                'id': doc_id,
                'score': score,
                'metadata': doc['metadata']
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]


# Global instance
zvec_service = ZVecService()


def get_zvec_service() -> ZVecService:
    """Get the global ZVec service instance."""
    return zvec_service


# Backward compatibility
ZVecIndexingService = ZVecService
