"""
ZVec Service - Offline Semantic Search for Google Drive Files

Provides vector-based semantic search using sentence-transformers for embeddings
and a local vector store (ZVec-compatible interface) for offline search capability.
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional, Any
from pathlib import Path

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed")

# Try to import zvec (custom/local package)
try:
    import zvec
    ZVEC_AVAILABLE = True
except ImportError:
    ZVEC_AVAILABLE = False


class MockZVecDB:
    """
    Fallback vector database using NumPy for cosine similarity.
    Compatible with ZVec interface for development without the actual package.
    """
    
    def __init__(self, dimension: int = 384, path: str = "./data/zvec_store"):
        self.dimension = dimension
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.store: Dict[str, Dict] = {}
        self.vectors: Optional[np.ndarray] = None
        self.ids: List[str] = []
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load existing vectors from disk."""
        data_file = self.path / "vectors.json"
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        self.store[item['id']] = item
                self._rebuild_index()
            except Exception as e:
                print(f"Error loading ZVec data: {e}")
    
    def _save_to_disk(self):
        """Save vectors to disk."""
        data_file = self.path / "vectors.json"
        try:
            with open(data_file, 'w') as f:
                json.dump(list(self.store.values()), f)
        except Exception as e:
            print(f"Error saving ZVec data: {e}")
    
    def _rebuild_index(self):
        """Rebuild the vector index for fast search."""
        if not self.store:
            self.vectors = None
            self.ids = []
            return
        
        self.ids = list(self.store.keys())
        self.vectors = np.array([self.store[id]['vector'] for id in self.ids])
    
    def add(self, id: str, vector: List[float], metadata: str):
        """Add a vector to the store."""
        self.store[id] = {
            'id': id,
            'vector': vector,
            'metadata': metadata
        }
        self._rebuild_index()
        self._save_to_disk()
    
    def search(self, vector: List[float], top_k: int = 5) -> List[Dict]:
        """Search for similar vectors using cosine similarity."""
        if self.vectors is None or len(self.store) == 0:
            return []
        
        query_vec = np.array(vector)
        
        # Normalize vectors for cosine similarity
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        vectors_norm = self.vectors / (np.linalg.norm(self.vectors, axis=1, keepdims=True) + 1e-8)
        
        # Compute cosine similarity
        similarities = np.dot(vectors_norm, query_norm)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            doc_id = self.ids[idx]
            results.append({
                'id': doc_id,
                'score': float(similarities[idx]),
                'metadata': self.store[doc_id]['metadata']
            })
        
        return results
    
    def get_all(self) -> List[Dict]:
        """Get all documents."""
        return list(self.store.values())
    
    def delete(self, id: str) -> bool:
        """Delete a document by ID."""
        if id in self.store:
            del self.store[id]
            self._rebuild_index()
            self._save_to_disk()
            return True
        return False
    
    def clear(self):
        """Clear all documents."""
        self.store = {}
        self.vectors = None
        self.ids = []
        self._save_to_disk()


class ZVecService:
    """
    Service for semantic search using vector embeddings.
    Works offline - no cloud vector DB needed.
    """
    
    def __init__(self, db_path: str = "./data/zvec_store"):
        self.db_path = db_path
        self.dimension = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
        
        # Initialize embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.embedding_model = None
            print("Warning: No embedding model available")
        
        # Initialize vector database
        if ZVEC_AVAILABLE:
            try:
                self.db = zvec.ZVecDB(dimension=self.dimension, path=db_path)
                print("Using ZVec database")
            except Exception as e:
                print(f"ZVec init failed, using mock: {e}")
                self.db = MockZVecDB(dimension=self.dimension, path=db_path)
        else:
            self.db = MockZVecDB(dimension=self.dimension, path=db_path)
            print("Using mock ZVec database (NumPy-based)")
        
        os.makedirs(db_path, exist_ok=True)
    
    def is_ready(self) -> bool:
        """Check if the service is ready to use."""
        return self.embedding_model is not None
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text using sentence-transformers."""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not available")
        
        # Truncate very long text (model has max input length)
        max_chars = 10000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        return self.embedding_model.encode(text, show_progress_bar=False)
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """
        Add document to vector store.
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Additional document metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                print("ZVec service not ready")
                return False
            
            embedding = self.embed_text(text)
            metadata_json = json.dumps(metadata, default=str)
            
            self.db.add(
                id=doc_id,
                vector=embedding.tolist(),
                metadata=metadata_json
            )
            return True
        except Exception as e:
            print(f"ZVec add error: {e}")
            return False
    
    def search_similar(
        self, 
        query: str, 
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Semantic search across indexed documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of matching documents with scores
        """
        try:
            if not self.is_ready():
                print("ZVec service not ready")
                return []
            
            query_vec = self.embed_text(query)
            results = self.db.search(
                vector=query_vec.tolist(),
                top_k=top_k
            )
            
            # Parse results
            output = []
            for r in results:
                if r['score'] < score_threshold:
                    continue
                    
                try:
                    meta = json.loads(r.get('metadata', '{}'))
                except:
                    meta = {}
                
                output.append({
                    'id': r['id'],
                    'score': r['score'],
                    'metadata': meta
                })
            
            return output
        except Exception as e:
            print(f"ZVec search error: {e}")
            return []
    
    def search_by_metadata(
        self, 
        project: Optional[str] = None, 
        doc_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter search by metadata fields.
        
        Args:
            project: Filter by project name
            doc_type: Filter by document type
            user_id: Filter by user ID
        
        Returns:
            List of matching documents
        """
        try:
            all_docs = self.db.get_all() if hasattr(self.db, 'get_all') else []
            results = []
            
            for doc in all_docs:
                try:
                    meta = json.loads(doc.get('metadata', '{}'))
                except:
                    continue
                
                # Apply filters
                if project and meta.get('project') != project:
                    continue
                if doc_type and meta.get('type') != doc_type:
                    continue
                if user_id and meta.get('user_id') != user_id:
                    continue
                
                results.append({
                    'id': doc['id'],
                    'metadata': meta
                })
            
            return results
        except Exception as e:
            print(f"Metadata search error: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        try:
            if hasattr(self.db, 'delete'):
                return self.db.delete(doc_id)
            return False
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            all_docs = self.db.get_all() if hasattr(self.db, 'get_all') else []
            return {
                'total_documents': len(all_docs),
                'dimension': self.dimension,
                'using_mock': isinstance(self.db, MockZVecDB),
                'embedding_model_ready': self.is_ready()
            }
        except Exception as e:
            return {'error': str(e)}


# Global instance (lazy-loaded)
_zvec_service: Optional[ZVecService] = None

def get_zvec_service() -> ZVecService:
    """Get or create the global ZVec service instance."""
    global _zvec_service
    if _zvec_service is None:
        _zvec_service = ZVecService()
    return _zvec_service
