import os
import json
from typing import List, Dict, Optional

# Try to import numpy, provide fallback if not available (SIGILL protection)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None  # type: ignore

try:
    import zvec
    ZVEC_AVAILABLE = True
except ImportError:
    ZVEC_AVAILABLE = False
    print("ZVec not installed, using mock")


class ZVecService:
    def __init__(self, db_path: str = "./data/zvec_store"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Lazy load - don't load model at startup (saves RAM)
        self._model = None
        self.dimension = 384
        
        if ZVEC_AVAILABLE and NUMPY_AVAILABLE:
            self.db = zvec.ZVecDB(dimension=self.dimension, path=db_path)
        else:
            self.db = MockZVecDB()
    
    def is_ready(self) -> bool:
        """Check if service is ready (has working ML stack)."""
        return ZVEC_AVAILABLE and NUMPY_AVAILABLE
    
    @property
    def model(self):
        """Lazy load - only when first search/index happens"""
        if self._model is None:
            if not NUMPY_AVAILABLE:
                raise RuntimeError("NumPy not available (SIGILL protection)")
            print("Loading embedding model... (one-time)")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                raise RuntimeError("sentence-transformers not installed")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text. Returns list of floats."""
        if not NUMPY_AVAILABLE:
            # Return random embedding as fallback
            import random
            return [random.uniform(-0.1, 0.1) for _ in range(self.dimension)]
        # Truncate to save memory
        return self.model.encode(text[:5000]).tolist()  # type: ignore
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        try:
            embedding = self.embed_text(text)
            self.db.add(
                id=doc_id,
                vector=embedding,
                metadata=json.dumps(metadata)
            )
            return True
        except Exception as e:
            print(f"ZVec add error: {e}")
            return False
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        try:
            query_vec = self.embed_text(query)
            results = self.db.search(
                vector=query_vec,
                top_k=top_k
            )
            return [
                {
                    'id': r['id'],
                    'score': r.get('score', 0),
                    'metadata': json.loads(r.get('metadata', '{}'))
                }
                for r in results
            ]
        except Exception as e:
            print(f"ZVec search error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        if hasattr(self.db, 'store'):
            return {"count": len(self.db.store), "ready": self.is_ready()}
        return {"count": 0, "ready": self.is_ready()}


class MockZVecDB:
    def __init__(self):
        self.store = {}
    
    def add(self, id: str, vector: List[float], metadata: str):
        self.store[id] = {'vector': vector, 'metadata': metadata}
    
    def search(self, vector: List[float], top_k: int = 5):
        import random
        return [
            {
                'id': k,
                'score': random.uniform(0.7, 0.95),
                'metadata': v['metadata']
            }
            for k, v in list(self.store.items())[:top_k]
        ]


# Global instance - lightweight at startup
zvec_service = ZVecService()


def get_zvec_service() -> ZVecService:
    """Get the global ZVec service instance."""
    return zvec_service
