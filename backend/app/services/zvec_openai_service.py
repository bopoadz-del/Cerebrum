"""
ZVec Service using OpenAI API for embeddings - Works on Render without AVX
"""
import os
import json
from typing import List, Dict, Optional


class ZVecOpenAIService:
    """ZVec service using OpenAI API for embeddings - no local ML needed."""
    
    def __init__(self, db_path: str = "./data/zvec_store"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        self.dimension = 1536  # OpenAI text-embedding-3-small
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Simple JSON file storage
        self.store_path = os.path.join(db_path, "documents.json")
        self.store = self._load_store()
    
    def _load_store(self) -> Dict:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_store(self):
        with open(self.store_path, 'w') as f:
            json.dump(self.store, f)
    
    def is_ready(self) -> bool:
        return bool(self.api_key)
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        import httpx
        
        if not self.api_key:
            # Fallback to mock
            import random
            return [random.uniform(-0.1, 0.1) for _ in range(self.dimension)]
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "input": text[:8000],  # OpenAI limit
                    "model": "text-embedding-3-small"
                },
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    
    async def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        try:
            embedding = await self.embed_text(text)
            self.store[doc_id] = {
                "vector": embedding,
                "metadata": metadata,
                "text_preview": text[:500]
            }
            self._save_store()
            return True
        except Exception as e:
            print(f"ZVec OpenAI add error: {e}")
            return False
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)
    
    async def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        try:
            query_vec = await self.embed_text(query)
            
            # Score all documents
            scored = []
            for doc_id, doc in self.store.items():
                score = self._cosine_similarity(query_vec, doc["vector"])
                scored.append({
                    "id": doc_id,
                    "score": score,
                    "metadata": doc["metadata"]
                })
            
            # Sort by score descending
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]
            
        except Exception as e:
            print(f"ZVec OpenAI search error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        return {
            "count": len(self.store),
            "ready": self.is_ready(),
            "mode": "openai" if self.api_key else "mock"
        }


# Global instance
_zvec_service = None

def get_zvec_service():
    global _zvec_service
    if _zvec_service is None:
        # Try OpenAI first, fall back to local
        if os.getenv("OPENAI_API_KEY"):
            _zvec_service = ZVecOpenAIService()
        else:
            # Fall back to existing service
            from app.services.zvec_service import ZVecService
            _zvec_service = ZVecService()
    return _zvec_service
