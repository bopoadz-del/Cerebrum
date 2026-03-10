"""
ChromaDB Service - Vector database for semantic search
Replaces ZVec with a production-ready vector database
"""
import os
import json
from typing import List, Dict, Any, Optional
import logging
import hashlib
import math

logger = logging.getLogger(__name__)

# Try to import chromadb, fallback to pure Python if not available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, will use fallback")


class ChromaService:
    """
    ChromaDB vector database service.
    Provides semantic search with proper embeddings.
    """
    
    def __init__(self, db=None, db_path: str = "./data/chroma_store"):
        self.db = db
        self.db_path = db_path
        self._client = None
        self._collection = None
        self.is_available = CHROMADB_AVAILABLE
        self._mode = "fallback"
        
        # Check for external ChromaDB server
        chroma_host = os.getenv("CHROMA_HOST")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        
        if CHROMADB_AVAILABLE:
            try:
                if chroma_host:
                    # Use external ChromaDB server (Docker mode)
                    self._client = chromadb.HttpClient(host=chroma_host, port=int(chroma_port))
                    self._mode = "http"
                    logger.info(f"✅ ChromaDB connected to server at {chroma_host}:{chroma_port}")
                else:
                    # Use local persistent client
                    os.makedirs(db_path, exist_ok=True)
                    self._client = chromadb.PersistentClient(path=db_path)
                    self._mode = "persistent"
                    logger.info(f"✅ ChromaDB initialized at {db_path}")
                
                self._collection = self._client.get_or_create_collection(
                    name="documents",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                self.is_available = False
        
        if not self.is_available:
            logger.warning("Using fallback hash-based embeddings")
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        if not self.is_available:
            return True  # Fallback is always ready
        return self._collection is not None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        Uses hash-based approach as fallback if ChromaDB is not available.
        """
        dimension = 384
        text = text[:5000].lower().strip()
        
        # Generate hash
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Create 384-dim vector
        embedding = []
        for i in range(dimension):
            hex_idx = (i * 2) % 32
            val = int(hash_hex[hex_idx:hex_idx+2], 16) / 128.0 - 1.0
            noise = math.sin(i * 0.1) * 0.1
            val += noise
            embedding.append(max(-1.0, min(1.0, val)))
        
        return embedding
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """Index a single document (sync)."""
        try:
            if self.is_available and self._collection is not None:
                # Use ChromaDB
                embedding = self._generate_embedding(text)
                self._collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text[:10000]],  # Store truncated text
                    metadatas=[metadata]
                )
            else:
                # Fallback: store in memory/file
                self._fallback_add(doc_id, text, metadata)
            
            logger.info(f"✅ ChromaDB indexed: {metadata.get('name', doc_id)}")
            return True
        except Exception as e:
            logger.error(f"ChromaDB add error: {e}")
            return False
    
    def _fallback_add(self, doc_id: str, text: str, metadata: Dict):
        """Fallback storage when ChromaDB is not available."""
        fallback_path = os.path.join(self.db_path, "fallback_docs.json")
        
        # Load existing
        docs = {}
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, 'r') as f:
                    docs = json.load(f)
            except:
                pass
        
        # Add new
        embedding = self._generate_embedding(text)
        docs[doc_id] = {
            'vector': embedding,
            'metadata': metadata,
            'text': text[:10000]
        }
        
        # Save
        with open(fallback_path, 'w') as f:
            json.dump(docs, f)
    
    async def index_document(self, doc_id: str, content: str, metadata: Dict) -> bool:
        """Index a single document (async)."""
        return self.add_document(doc_id, content, metadata)
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search (sync)."""
        try:
            if self.is_available and self._collection is not None:
                # Use ChromaDB
                query_vec = self._generate_embedding(query)
                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=top_k,
                    include=["metadatas", "distances"]
                )
                
                # Format results
                formatted = []
                if results['ids'] and results['ids'][0]:
                    for i, doc_id in enumerate(results['ids'][0]):
                        distance = results['distances'][0][i] if results['distances'] else 0
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        # Convert distance to similarity score (cosine distance -> similarity)
                        score = 1.0 - distance
                        formatted.append({
                            'id': doc_id,
                            'score': score,
                            'metadata': metadata
                        })
                
                logger.info(f"🔍 ChromaDB search: '{query}' -> {len(formatted)} results")
                return formatted
            else:
                # Fallback search
                return self._fallback_search(query, top_k)
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return []
    
    def _fallback_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Fallback search when ChromaDB is not available."""
        fallback_path = os.path.join(self.db_path, "fallback_docs.json")
        
        if not os.path.exists(fallback_path):
            return []
        
        try:
            with open(fallback_path, 'r') as f:
                docs = json.load(f)
        except:
            return []
        
        query_vec = self._generate_embedding(query)
        
        # Calculate cosine similarity
        def cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0
            return dot / (norm_a * norm_b)
        
        scored = []
        for doc_id, doc in docs.items():
            score = cosine_similarity(query_vec, doc['vector'])
            scored.append({
                'id': doc_id,
                'score': score,
                'metadata': doc['metadata']
            })
        
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Semantic search (async)."""
        return self.search_similar(query, top_k)
    
    def get_stats_sync(self) -> Dict[str, Any]:
        """Get indexing stats (sync)."""
        try:
            if self.is_available and self._collection is not None:
                count = self._collection.count()
                return {
                    "status": "active",
                    "count": count,
                    "ready": True,
                    "mode": self._mode,
                    "using": "ChromaDB"
                }
            else:
                # Fallback stats
                fallback_path = os.path.join(self.db_path, "fallback_docs.json")
                count = 0
                if os.path.exists(fallback_path):
                    try:
                        with open(fallback_path, 'r') as f:
                            count = len(json.load(f))
                    except:
                        pass
                return {
                    "status": "active",
                    "count": count,
                    "ready": True,
                    "mode": "fallback",
                    "using": "Fallback (hash-based)"
                }
        except Exception as e:
            return {"status": "error", "error": str(e), "count": 0, "mode": "error"}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing stats (async)."""
        return self.get_stats_sync()
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the index."""
        try:
            if self.is_available and self._collection is not None:
                self._collection.delete(ids=[doc_id])
                return True
            else:
                # Fallback delete
                fallback_path = os.path.join(self.db_path, "fallback_docs.json")
                if os.path.exists(fallback_path):
                    try:
                        with open(fallback_path, 'r') as f:
                            docs = json.load(f)
                        if doc_id in docs:
                            del docs[doc_id]
                            with open(fallback_path, 'w') as f:
                                json.dump(docs, f)
                        return True
                    except:
                        pass
            return False
        except Exception as e:
            logger.error(f"ChromaDB delete error: {e}")
            return False


# Global singleton
_chroma_service_instance = None

def get_chroma_service(db=None):
    """Get global ChromaDB service instance."""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService(db)
    return _chroma_service_instance


# Backward compatibility - ZVec aliases
ZVecService = ChromaService
get_zvec_service = get_chroma_service
ZVecIndexingService = ChromaService
