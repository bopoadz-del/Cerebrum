"""
ChromaDB Service - Vector database with ML embeddings (Optimized for 2GB RAM)

Uses sentence-transformers for real semantic embeddings (384-dim).
Falls back to hash-based embeddings if ML model unavailable.

OPTIMIZATIONS FOR LOW MEMORY:
- Memory monitoring with alerts
- Smaller embedding model options (paraphrase-MiniLM-L3-v2)
- INT8 quantization support
- Lazy model loading
- Batch size limits
- ChromaDB HNSW tuning for low memory
- SQLite pragmas for memory efficiency
"""
import os
import json
import time
import gc
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import hashlib
import math
import warnings

logger = logging.getLogger(__name__)

# =============================================================================
# MEMORY MONITORING
# =============================================================================

@dataclass
class MemoryStats:
    """Memory usage statistics."""
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage of total
    available_mb: float  # Available memory
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryMonitor:
    """Monitor memory usage and trigger alerts."""
    
    def __init__(self, warning_threshold_mb: float = 1500, critical_threshold_mb: float = 1800):
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        self.peak_rss_mb = 0.0
        self._has_psutil = False
        
        try:
            import psutil
            self._psutil = psutil
            self._process = psutil.Process()
            self._has_psutil = True
            logger.info(
                f"✅ Memory monitor active (warn: {warning_threshold_mb}MB, "
                f"critical: {critical_threshold_mb}MB)"
            )
        except ImportError:
            logger.warning("psutil not available - memory monitoring disabled")
    
    def get_stats(self) -> Optional[MemoryStats]:
        """Get current memory stats."""
        if not self._has_psutil:
            return None
        
        try:
            mem_info = self._process.memory_info()
            system_mem = self._psutil.virtual_memory()
            
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)
            
            self.peak_rss_mb = max(self.peak_rss_mb, rss_mb)
            
            return MemoryStats(
                rss_mb=round(rss_mb, 2),
                vms_mb=round(vms_mb, 2),
                percent=round(system_mem.percent, 1),
                available_mb=round(system_mem.available / (1024 * 1024), 2),
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.warning(f"Memory stats error: {e}")
            return None
    
    def check_thresholds(self) -> Dict[str, Any]:
        """Check memory against thresholds and return status."""
        stats = self.get_stats()
        if not stats:
            return {"status": "unknown", "stats": None}
        
        status = "normal"
        actions = []
        
        if stats.rss_mb > self.critical_threshold_mb:
            status = "critical"
            actions.append("trigger_emergency_gc")
            actions.append("disable_ml_embeddings")
        elif stats.rss_mb > self.warning_threshold_mb:
            status = "warning"
            actions.append("suggest_gc")
        
        return {
            "status": status,
            "stats": stats.to_dict(),
            "peak_mb": round(self.peak_rss_mb, 2),
            "actions": actions
        }
    
    def emergency_gc(self) -> Dict[str, Any]:
        """Perform emergency garbage collection."""
        before = self.get_stats()
        gc.collect()
        
        # Force torch cache clear if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            # Also clear CPU cache if using torch
            torch.cpu.empty_cache() if hasattr(torch.cpu, 'empty_cache') else None
        except ImportError:
            pass
        
        after = self.get_stats()
        
        return {
            "freed_mb": round(before.rss_mb - after.rss_mb, 2) if before and after else 0,
            "before": before.to_dict() if before else None,
            "after": after.to_dict() if after else None
        }


# Global memory monitor instance
_memory_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor() -> Optional[MemoryMonitor]:
    """Get or create global memory monitor."""
    global _memory_monitor
    if _memory_monitor is None:
        warning = float(os.getenv("MEMORY_WARNING_MB", "1500"))
        critical = float(os.getenv("MEMORY_CRITICAL_MB", "1800"))
        _memory_monitor = MemoryMonitor(warning, critical)
    return _memory_monitor


# =============================================================================
# CONFIGURATION
# =============================================================================

# Check if ChromaDB should be disabled (for low-memory environments)
DISABLE_CHROMADB = os.getenv("DISABLE_CHROMADB", "false").lower() == "true"

# Embedding model selection (smaller = less memory)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# Options:
# - "all-MiniLM-L6-v2" (22MB, 384-dim) - DEFAULT, good balance
# - "paraphrase-MiniLM-L3-v2" (17MB, 384-dim) - SMALLER, slightly less accurate
# - "all-MiniLM-L12-v2" (33MB, 384-dim) - BETTER quality, more memory

# Quantization settings
USE_INT8_QUANTIZATION = os.getenv("USE_INT8_QUANTIZATION", "false").lower() == "true"
QUANTIZATION_BATCH_SIZE = int(os.getenv("QUANTIZATION_BATCH_SIZE", "100"))

# Lazy loading - don't load model until first use
LAZY_LOAD_MODEL = os.getenv("LAZY_LOAD_MODEL", "true").lower() == "true"

# Batch processing limits
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "32"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))

# ChromaDB HNSW settings for low memory
HNSW_M = int(os.getenv("HNSW_M", "8"))  # Default 16, lower = less memory
HNSW_EF_CONSTRUCTION = int(os.getenv("HNSW_EF_CONSTRUCTION", "64"))  # Default 100
HNSW_EF_SEARCH = int(os.getenv("HNSW_EF_SEARCH", "32"))  # Default 10, higher = better recall

# SQLite pragmas for low memory
SQLITE_CACHE_SIZE = int(os.getenv("SQLITE_CACHE_SIZE", "-32768"))  # Negative = KB, default -2000 pages
SQLITE_PAGE_SIZE = int(os.getenv("SQLITE_PAGE_SIZE", "4096"))
SQLITE_TEMP_STORE = os.getenv("SQLITE_TEMP_STORE", "memory")

# Try to import ML libraries (LAZY LOADING - only import when needed)
try:
    if DISABLE_CHROMADB:
        raise ImportError("ChromaDB disabled via environment variable")
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available")

# LAZY LOADING: Don't import sentence_transformers at module level
# This saves 400MB+ of memory when USE_ML_EMBEDDINGS=false
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None

def _ensure_sentence_transformers():
    """Lazy import sentence_transformers only when needed."""
    global SENTENCE_TRANSFORMERS_AVAILABLE, SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as ST
            SentenceTransformer = ST
            SENTENCE_TRANSFORMERS_AVAILABLE = True
            logger.info("sentence-transformers loaded (lazy)")
        except ImportError:
            SENTENCE_TRANSFORMERS_AVAILABLE = False
            logger.warning("sentence-transformers not available, using hash fallback")
    return SENTENCE_TRANSFORMERS_AVAILABLE


# =============================================================================
# EMBEDDING MODEL
# =============================================================================

class QuantizedEmbedding:
    """INT8 quantized embedding storage."""
    
    def __init__(self, values: List[int], scale: float, zero_point: int, original_dim: int):
        self.values = values  # List of int8 values
        self.scale = scale
        self.zero_point = zero_point
        self.original_dim = original_dim
    
    @staticmethod
    def quantize_float32(float_values: List[float]) -> "QuantizedEmbedding":
        """Convert float32 embeddings to INT8."""
        # Find min/max for calibration
        min_val = min(float_values)
        max_val = max(float_values)
        
        # Compute scale and zero point
        scale = (max_val - min_val) / 255.0 if max_val != min_val else 1.0
        zero_point = int(-min_val / scale) if scale != 0 else 0
        zero_point = max(0, min(255, zero_point))  # Clamp to uint8 range
        
        # Quantize
        quantized = []
        for v in float_values:
            q = int(round(v / scale + zero_point))
            q = max(0, min(255, q))  # Clamp
            quantized.append(q)
        
        return QuantizedEmbedding(quantized, scale, zero_point, len(float_values))
    
    def dequantize(self) -> List[float]:
        """Convert back to float32."""
        return [(v - self.zero_point) * self.scale for v in self.values]
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        import struct
        header = struct.pack('<fii', self.scale, self.zero_point, self.original_dim)
        values_bytes = bytes(self.values)
        return header + values_bytes
    
    @staticmethod
    def from_bytes(data: bytes) -> "QuantizedEmbedding":
        """Deserialize from bytes."""
        import struct
        scale, zero_point, original_dim = struct.unpack('<fii', data[:12])
        values = list(data[12:])
        return QuantizedEmbedding(values, scale, zero_point, original_dim)


class EmbeddingModel:
    """
    Wrapper for sentence-transformers model with fallback and quantization.
    Optimized for low-memory environments.
    """
    
    # Model configs: (name, size_mb, dimension)
    MODEL_CONFIGS = {
        "paraphrase-MiniLM-L3-v2": {"size_mb": 17, "dim": 384, "speed": "fastest"},
        "all-MiniLM-L6-v2": {"size_mb": 22, "dim": 384, "speed": "fast"},
        "all-MiniLM-L12-v2": {"size_mb": 33, "dim": 384, "speed": "medium"},
    }
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or EMBEDDING_MODEL
        self._model = None
        self._dimension = self.MODEL_CONFIGS.get(self.model_name, {}).get("dim", 384)
        self._using_ml = False
        self._lazy_loaded = False
        self._use_quantization = USE_INT8_QUANTIZATION
        self._quantization_cache: Dict[str, QuantizedEmbedding] = {}
        
        # Memory monitoring
        self._mem_monitor = get_memory_monitor()
        
        if not LAZY_LOAD_MODEL:
            self._load_model()
        else:
            logger.info(f"⏳ Lazy loading enabled for {self.model_name}")
    
    def _check_memory_before_load(self) -> bool:
        """Check if there's enough memory to load the model."""
        if not self._mem_monitor:
            return True
        
        status = self._mem_monitor.check_thresholds()
        if status["status"] == "critical":
            logger.warning("⚠️ Critical memory - refusing to load ML model")
            return False
        return True
    
    def _load_model(self):
        """Load the sentence transformer model (LAZY LOADING)."""
        if self._lazy_loaded:
            return
        
        # LAZY LOADING: Check if ML embeddings are enabled BEFORE importing
        use_ml = os.getenv("USE_ML_EMBEDDINGS", "true").lower() == "true"
        if not use_ml:
            logger.info("ML embeddings disabled via USE_ML_EMBEDDINGS - using hash fallback")
            return
        
        # LAZY LOADING: Import sentence_transformers only when needed
        if not _ensure_sentence_transformers():
            logger.info("Using hash-based embeddings (deterministic, not semantic)")
            return
        
        # Check memory before loading
        if not self._check_memory_before_load():
            logger.warning("Using hash-based embeddings due to memory constraints")
            return
        
        try:
            cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/models")
            
            # Log memory before
            before = self._mem_monitor.get_stats() if self._mem_monitor else None
            logger.info(f"Loading embedding model: {self.model_name} (cache: {cache_dir})")
            
            load_start = time.time()
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir,
                device="cpu"
            )
            load_time = time.time() - load_start
            
            self._using_ml = True
            self._lazy_loaded = True
            
            # Log memory after
            after = self._mem_monitor.get_stats() if self._mem_monitor else None
            mem_increase = after.rss_mb - before.rss_mb if before and after else 0
            
            model_config = self.MODEL_CONFIGS.get(self.model_name, {})
            logger.info(f"✅ ML embeddings ready: {self.model_name} ({self._dimension}d, "
                       f"load_time={load_time:.2f}s, mem_increase={mem_increase:.1f}MB)")
            
            # Warn if model size doesn't match config
            expected_size = model_config.get("size_mb", 0)
            if expected_size and mem_increase > expected_size * 3:  # 3x multiplier for overhead
                logger.warning(f"⚠️ Model using more memory than expected ({mem_increase:.1f}MB vs {expected_size}MB)")
            
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            self._model = None
    
    @property
    def is_using_ml(self) -> bool:
        return self._using_ml
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def _ensure_loaded(self):
        """Ensure model is loaded (for lazy loading)."""
        if LAZY_LOAD_MODEL and not self._lazy_loaded and self._model is None:
            self._load_model()
    
    def encode(self, text: str) -> List[float]:
        """Generate embedding - ML first, hash fallback."""
        self._ensure_loaded()
        
        if self._using_ml and self._model:
            try:
                # Check memory before encoding
                if self._mem_monitor:
                    status = self._mem_monitor.check_thresholds()
                    if status["status"] == "critical":
                        logger.warning("Critical memory during encoding - using hash fallback")
                        return self._hash_embedding(text)
                
                # Truncate long texts (model has 256 token limit roughly)
                text = text[:5000]
                
                embedding = self._model.encode(
                    text, 
                    convert_to_list=True, 
                    show_progress_bar=False,
                    batch_size=1  # Force batch size 1 for single queries
                )
                
                # Optionally quantize
                if self._use_quantization:
                    quantized = QuantizedEmbedding.quantize_float32(list(embedding))
                    return quantized.dequantize()
                
                return list(embedding)
            except Exception as e:
                logger.warning(f"ML encoding failed, using hash: {e}")
        
        # Hash-based fallback (deterministic, not semantic)
        return self._hash_embedding(text)
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch encode with memory-aware batching."""
        self._ensure_loaded()
        
        if not self._using_ml or not self._model:
            return [self._hash_embedding(t) for t in texts]
        
        results = []
        total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
        
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i:i + EMBEDDING_BATCH_SIZE]
            batch_num = i // EMBEDDING_BATCH_SIZE + 1
            
            # Check memory before each batch
            if self._mem_monitor:
                status = self._mem_monitor.check_thresholds()
                if status["status"] == "critical":
                    logger.warning(f"Critical memory at batch {batch_num}/{total_batches} - switching to hash")
                    results.extend([self._hash_embedding(t) for t in batch])
                    continue
            
            try:
                # Truncate texts
                batch = [t[:5000] for t in batch]
                embeddings = self._model.encode(
                    batch,
                    convert_to_list=True,
                    show_progress_bar=False,
                    batch_size=len(batch)
                )
                results.extend([list(e) for e in embeddings])
                
                # Periodic GC for large batches
                if batch_num % 5 == 0:
                    gc.collect()
                    
            except Exception as e:
                logger.warning(f"Batch encoding failed for batch {batch_num}: {e}")
                results.extend([self._hash_embedding(t) for t in batch])
        
        return results
    
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
        mem_stats = self._mem_monitor.get_stats() if self._mem_monitor else None
        
        return {
            "model_name": self.model_name if self._using_ml else "hash_fallback",
            "dimension": self._dimension,
            "using_ml": self._using_ml,
            "lazy_loaded": self._lazy_loaded,
            "quantization_enabled": self._use_quantization,
            "available": SENTENCE_TRANSFORMERS_AVAILABLE and self._model is not None,
            "memory": mem_stats.to_dict() if mem_stats else None,
            "model_config": self.MODEL_CONFIGS.get(self.model_name, {})
        }
    
    def unload(self):
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._using_ml = False
            self._lazy_loaded = False
            gc.collect()
            
            # Clear torch cache
            try:
                import torch
                torch.cpu.empty_cache() if hasattr(torch.cpu, 'empty_cache') else None
            except ImportError:
                pass
            
            logger.info("Embedding model unloaded to free memory")


# =============================================================================
# CHROMADB SERVICE
# =============================================================================

class ChromaService:
    """
    ChromaDB vector database service with ML embeddings.
    Optimized for 2GB RAM environments.
    """
    
    def __init__(self, db=None, db_path: str = None):
        self.db = db
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "/data/chroma_store")
        self._client = None
        self._collection = None
        self.is_available = CHROMADB_AVAILABLE
        self._mode = "fallback"
        
        # Initialize memory monitor
        self._mem_monitor = get_memory_monitor()
        
        # Initialize embedding model (lazy by default)
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
                    # Use local persistent client with low-memory settings
                    os.makedirs(self.db_path, exist_ok=True)
                    
                    # Configure ChromaDB for low memory
                    settings = self._get_low_memory_settings()
                    
                    self._client = chromadb.PersistentClient(
                        path=self.db_path,
                        settings=settings
                    )
                    self._mode = "persistent"
                    logger.info(f"✅ ChromaDB local (low-memory mode): {self.db_path}")
                
                # Get or create collection with optimized HNSW settings
                self._collection = self._client.get_or_create_collection(
                    name="documents",
                    metadata={
                        "hnsw:space": "cosine",
                        "hnsw:M": str(HNSW_M),
                        "hnsw:construction_ef": str(HNSW_EF_CONSTRUCTION),
                        "hnsw:search_ef": str(HNSW_EF_SEARCH),
                    }
                )
                
                count = self._collection.count()
                logger.info(f"✅ Collection ready: documents ({count} items, HNSW M={HNSW_M})")
                
                # Log memory status
                if self._mem_monitor:
                    mem_status = self._mem_monitor.check_thresholds()
                    logger.info(f"Memory status: {mem_status['status']} ({mem_status['stats']['rss_mb']}MB)")
                
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                self.is_available = False
        
        if not self.is_available:
            logger.warning("Using fallback file-based storage")
    
    def _get_low_memory_settings(self) -> "Settings":
        """Get ChromaDB settings optimized for low memory."""
        from chromadb.config import Settings
        
        # SQLite pragmas for memory efficiency
        sqlite_pragmas = {
            "cache_size": SQLITE_CACHE_SIZE,  # Negative = KB
            "page_size": SQLITE_PAGE_SIZE,
            "temp_store": SQLITE_TEMP_STORE,
            "synchronous": "NORMAL",  # Less fsync for speed
            "journal_mode": "WAL",  # Write-ahead logging
            "mmap_size": 0,  # Disable memory-mapped I/O
        }
        
        return Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            sqlite_pragmas=sqlite_pragmas,
        )
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        if not self.is_available:
            return True  # Fallback is always ready
        return self._collection is not None
    
    def get_embedding_model_info(self) -> Dict[str, Any]:
        """Get embedding model status."""
        return self._embedder.get_model_info()
    
    def get_memory_stats(self) -> Optional[Dict[str, Any]]:
        """Get current memory statistics."""
        if not self._mem_monitor:
            return None
        return self._mem_monitor.check_thresholds()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using ML model or hash fallback."""
        return self._embedder.encode(text)
    
    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings."""
        return self._embedder.encode_batch(texts)
    
    def add_document(self, doc_id: str, text: str, metadata: Dict) -> bool:
        """Index a single document."""
        try:
            # Check memory before processing
            if self._mem_monitor:
                status = self._mem_monitor.check_thresholds()
                if status["status"] == "critical":
                    logger.error("Critical memory - cannot add document")
                    return False
            
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
    
    def add_documents_batch(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add multiple documents with memory-aware batching."""
        if not docs:
            return {"status": "success", "success_count": 0, "error_count": 0}
        
        # Check memory
        if self._mem_monitor:
            status = self._mem_monitor.check_thresholds()
            if status["status"] == "critical":
                logger.error("Critical memory - cannot batch add documents")
                return {"status": "error", "message": "Critical memory", "success_count": 0, "error_count": len(docs)}
        
        success_count = 0
        error_count = 0
        
        # Process in batches
        total_batches = (len(docs) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        
        for batch_idx in range(0, len(docs), MAX_BATCH_SIZE):
            batch = docs[batch_idx:batch_idx + MAX_BATCH_SIZE]
            batch_num = batch_idx // MAX_BATCH_SIZE + 1
            
            try:
                # Extract data
                ids = [d.get('id') for d in batch]
                texts = [d.get('text', '') for d in batch]
                metadatas = [d.get('metadata', {}) for d in batch]
                
                # Skip empty IDs
                valid_items = [(i, t, m) for i, t, m in zip(ids, texts, metadatas) if i]
                if not valid_items:
                    continue
                
                ids, texts, metadatas = zip(*valid_items)
                
                # Generate embeddings in batches
                embeddings = self._generate_embeddings_batch(list(texts))
                
                if self.is_available and self._collection is not None:
                    self._collection.add(
                        ids=list(ids),
                        embeddings=embeddings,
                        documents=[t[:10000] for t in texts],
                        metadatas=list(metadatas)
                    )
                else:
                    for doc_id, text, embedding, meta in zip(ids, texts, embeddings, metadatas):
                        self._fallback_add(doc_id, text, embedding, meta)
                
                success_count += len(valid_items)
                logger.info(f"Batch {batch_num}/{total_batches}: added {len(valid_items)} docs")
                
                # Periodic GC for large batches
                if batch_num % 2 == 0:
                    gc.collect()
                    
            except Exception as e:
                logger.error(f"Batch {batch_num} error: {e}")
                error_count += len(batch)
        
        return {
            "status": "success",
            "success_count": success_count,
            "error_count": error_count,
            "total": len(docs)
        }
    
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
                # Adjust top_k if it exceeds ef_search for better recall
                ef_search = max(HNSW_EF_SEARCH, top_k * 2)
                
                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=min(top_k, 100),  # Cap at 100
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
                
                logger.info(f"🔍 Search: '{query[:50]}...' → {len(formatted)} results (ml={self._embedder.is_using_ml})")
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
        """Get indexing stats with memory info."""
        try:
            embedding_info = self.get_embedding_model_info()
            memory_info = self.get_memory_stats()
            
            if self.is_available and self._collection is not None:
                count = self._collection.count()
                return {
                    "status": "active",
                    "count": count,
                    "ready": True,
                    "mode": self._mode,
                    "using_chromadb": True,
                    "embedding": embedding_info,
                    "memory": memory_info,
                    "hnsw_config": {
                        "M": HNSW_M,
                        "ef_construction": HNSW_EF_CONSTRUCTION,
                        "ef_search": HNSW_EF_SEARCH,
                    }
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
                    "embedding": embedding_info,
                    "memory": memory_info
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "count": 0,
                "mode": "error",
                "embedding": self.get_embedding_model_info(),
                "memory": self.get_memory_stats()
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
        
        # Check memory before reindexing
        if self._mem_monitor:
            status = self._mem_monitor.check_thresholds()
            if status["status"] in ["warning", "critical"]:
                logger.warning(f"Memory status {status['status']} - reindexing may be slow")
        
        return self.add_documents_batch(documents)
    
    def optimize_for_memory(self) -> Dict[str, Any]:
        """Run memory optimization procedures."""
        results = {
            "gc_performed": False,
            "model_unloaded": False,
            "memory_before": None,
            "memory_after": None,
        }
        
        if self._mem_monitor:
            results["memory_before"] = self._mem_monitor.get_stats()
        
        # Run GC
        gc.collect()
        results["gc_performed"] = True
        
        # Optionally unload model
        if os.getenv("AUTO_UNLOAD_MODEL", "false").lower() == "true":
            self._embedder.unload()
            results["model_unloaded"] = True
        
        # Clear torch cache
        try:
            import torch
            torch.cpu.empty_cache() if hasattr(torch.cpu, 'empty_cache') else None
        except ImportError:
            pass
        
        if self._mem_monitor:
            results["memory_after"] = self._mem_monitor.get_stats()
        
        return results
    
    def unload_model(self):
        """Unload embedding model to free memory."""
        self._embedder.unload()


# =============================================================================
# GLOBAL SINGLETON
# =============================================================================

_chroma_service_instance = None

def get_chroma_service(db=None):
    """Get global ChromaDB service instance."""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService(db)
    return _chroma_service_instance


def reset_chroma_service():
    """Reset the global instance (useful for testing)."""
    global _chroma_service_instance
    _chroma_service_instance = None


# Backward compatibility
ZVecService = ChromaService
get_zvec_service = get_chroma_service
ZVecIndexingService = ChromaService
