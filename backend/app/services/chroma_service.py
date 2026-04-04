"""
ChromaDB Service - Vector database with ML embeddings

Uses sentence-transformers for real semantic embeddings (384-dim).
Falls back to hash-based embeddings if ML model unavailable.
"""
import os
import json
from typing import List, Dict, Any, Optional
import logging
import hashlib
import math

logger = logging.getLogger(__name__)

# Check if ChromaDB should be disabled (for low-memory environments - default OFF for 2GB plan)
DISABLE_CHROMADB = os.getenv("DISABLE_CHROMADB", "false").lower() == "true"

# Try to import ML libraries
try:
    if DISABLE_CHROMADB:
        raise ImportError("ChromaDB disabled via environment variable")
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, using hash fallback")


class EmbeddingModel:
    """
    Wrapper for sentence-transformers model with fallback.
    Uses all-MiniLM-L6-v2 (22MB, 384-dim, fast inference).
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384
        self._using_ml = False
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Check if we should use ML embeddings
                use_ml = os.getenv("USE_ML_EMBEDDINGS", "true").lower() == "true"
                if use_ml:
                    cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/models")
                    logger.info(f"Loading embedding model: {model_name}")
                    self._model = SentenceTransformer(
                        model_name,
                        cache_folder=cache_dir,
                        device="cpu"
                    )
                    self._using_ml = True
                    logger.info(f"✅ ML embeddings ready: {model_name} ({self._dimension}d)")
                else:
                    logger.info("ML embeddings disabled via USE_ML_EMBEDDINGS")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
                self._model = None
        
        if not self._using_ml:
            logger.info("Using hash-based embeddings (deterministic, not semantic)")
    
    @property
    def is_using_ml(self) -> bool:
        return self._using_ml
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def encode(self, text: str) -> List[float]:
        """Generate embedding - ML first, hash fallback."""
        if self._using_ml and self._model:
            try:
                # Truncate long texts (model has 256 token limit roughly)
                text = text[:5000]
                embedding = self._model.encode(text, convert_to_list=True, show_progress_bar=False)
                return list(embedding)
            except Exception as e:
                logger.warning(f"ML encoding failed, using hash: {e}")
        
        # Hash-based fallback (deterministic, not semantic)
        return self._hash_embedding(text)
    
    def _hash_embedding(self, text: str) -> List[float]:
        """Generate deterministic hash-based embedding."""
        text = text[:5000].lower().strip()
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        embedding = []
        for i in range(self._dimension):
            hex_idx = (i * 2) % 32
            val = int(hash_hex[hex_idx:hex_idx+2], 16) / 128.0 - 1.0
            noise = math.sin(i * 0.1) * 0.1
            val += noise
            embedding.append(max(-1.0, min(1.0, val)))
        
        return embedding
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model status info."""
        return {
            "model_name": self.model_name if self._using_ml else "hash_fallback",
            "dimension": self._dimension,
            "using_ml": self._using_ml,
            "available": SENTENCE_TRANSFORMERS_AVAILABLE and self._model is not None
        }


class ChromaService:
    """
    ChromaDB vector database service with ML embeddings.
    """
    
    def __init__(self, db=None, db_path: str = None):
        self.db = db
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "/data/chroma_store")
        self._client = None
        self._collection = None
        self.is_available = CHROMADB_AVAILABLE
        self._mode = "fallback"
        
        # Initialize embedding model
        self._embedder = EmbeddingModel()
        
        # Check for external ChromaDB server
        chroma_host = os.getenv("CHROMA_HOST")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        
        if CHROMADB_AVAILABLE:
            try:
                if chroma_host:
                    # Use external ChromaDB server
                    self._client = chromadb.HttpClient(host=chroma_host, port=int(chroma_port))
                    self._mode = "http"
                    logger.info(f"✅ ChromaDB HTTP: {chroma_host}:{chroma_port}")
                else:
                    # Use local persistent client
                    os.makedirs(self.db_path, exist_ok=True)
                    self._client = chromadb.PersistentClient(path=self.db_path)
                    self._mode = "persistent"
                    logger.info(f"✅ ChromaDB local: {self.db_path}")
                
                # Get or create collection with cosine distance
                self._collection = self._client.get_or_create_collection(
                    name="documents",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"✅ Collection ready: documents ({self._collection.count()} items)")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                self.is_available = False
        
        if not self.is_available:
            logger.warning("Using fallback file-based storage")
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        if not self.is_available:
            return True  # Fallback is always ready
        return self._collection is not None
    
    def get_embedding_model_info(self) -> Dict[str, Any]:
        """Get embedding model status."""
        return self._embedder.get_model_info()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using ML model or hash fallback."""
        return self._embedder.encode(text)
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """Index a single document."""
        try:
            embedding = self._generate_embedding(text)
            
            if self.is_available and self._collection is not None:
                self._collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text[:10000]],
                    metadatas=[metadata]
                )
            else:
                self._fallback_add(doc_id, text, embedding, metadata)
            
            logger.info(f"✅ Indexed: {metadata.get('name', doc_id)} (ml={self._embedder.is_using_ml})")
            return True
        except Exception as e:
            logger.error(f"Add document error: {e}")
            return False
    
    def _fallback_add(self, doc_id: str, text: str, embedding: List[float], metadata: Dict):
        """Fallback file-based storage."""
        fallback_path = os.path.join(self.db_path, "fallback_docs.json")
        
        docs = {}
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, 'r') as f:
                    docs = json.load(f)
            except:
                pass
        
        docs[doc_id] = {
            'vector': embedding,
            'metadata': metadata,
            'text': text[:10000]
        }
        
        with open(fallback_path, 'w') as f:
            json.dump(docs, f)
    
    async def index_document(self, doc_id: str, content: str, metadata: Dict) -> bool:
        """Index a single document (async)."""
        return self.add_document(doc_id, content, metadata)
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search using embeddings."""
        try:
            query_vec = self._generate_embedding(query)
            
            if self.is_available and self._collection is not None:
                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=top_k,
                    include=["metadatas", "distances", "documents"]
                )
                
                formatted = []
                if results['ids'] and results['ids'][0]:
                    for i, doc_id in enumerate(results['ids'][0]):
                        distance = results['distances'][0][i] if results['distances'] else 0
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        document = results['documents'][0][i] if results['documents'] else None
                        
                        score = 1.0 - distance  # Cosine distance to similarity
                        formatted.append({
                            'id': doc_id,
                            'score': max(0.0, min(1.0, score)),
                            'metadata': metadata,
                            'content_preview': document[:200] if document else None
                        })
                
                logger.info(f"🔍 Search: '{query}' → {len(formatted)} results (ml={self._embedder.is_using_ml})")
                return formatted
            else:
                return self._fallback_search(query_vec, top_k)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _fallback_search(self, query_vec: List[float], top_k: int = 5) -> List[Dict]:
        """Fallback search in file storage."""
        fallback_path = os.path.join(self.db_path, "fallback_docs.json")
        
        if not os.path.exists(fallback_path):
            return []
        
        try:
            with open(fallback_path, 'r') as f:
                docs = json.load(f)
        except:
            return []
        
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
                'metadata': doc['metadata'],
                'content_preview': doc['text'][:200] if doc.get('text') else None
            })
        
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]
    
    async def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Async semantic search."""
        return self.search_similar(query, top_k)
    
    def get_stats_sync(self) -> Dict[str, Any]:
        """Get indexing stats."""
        try:
            embedding_info = self.get_embedding_model_info()
            
            if self.is_available and self._collection is not None:
                count = self._collection.count()
                return {
                    "status": "active",
                    "count": count,
                    "ready": True,
                    "mode": self._mode,
                    "using_chromadb": True,
                    "embedding": embedding_info
                }
            else:
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
                    "using_chromadb": False,
                    "embedding": embedding_info
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "count": 0,
                "mode": "error",
                "embedding": self.get_embedding_model_info()
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Async stats."""
        return self.get_stats_sync()
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        try:
            if self.is_available and self._collection is not None:
                self._collection.delete(ids=[doc_id])
                return True
            else:
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
            logger.error(f"Delete error: {e}")
            return False
    
    def reindex_all(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk reindex documents with current embedding model.
        Use this when switching from hash to ML embeddings.
        """
        if not self.is_available or self._collection is None:
            return {"status": "error", "message": "ChromaDB not available"}
        
        success_count = 0
        error_count = 0
        
        for doc in documents:
            try:
                doc_id = doc.get('id')
                text = doc.get('text', '')
                metadata = doc.get('metadata', {})
                
                if doc_id and text:
                    if self.add_document(doc_id, text, metadata):
                        success_count += 1
                    else:
                        error_count += 1
            except Exception as e:
                logger.error(f"Reindex error for {doc.get('id')}: {e}")
                error_count += 1
        
        return {
            "status": "success",
            "success_count": success_count,
            "error_count": error_count,
            "embedding_model": self._embedder.get_model_info()
        }


# Global singleton
_chroma_service_instance = None

def get_chroma_service(db=None):
    """Get global ChromaDB service instance."""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService(db)
    return _chroma_service_instance


# Backward compatibility
ZVecService = ChromaService
get_zvec_service = get_chroma_service
ZVecIndexingService = ChromaService
