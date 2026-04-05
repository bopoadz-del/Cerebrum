# ChromaDB Low-Memory Configuration for Render (2GB Plan)

This document describes the optimized configuration for running ChromaDB with sentence-transformers on Render's 2GB RAM instances.

## Quick Start

Add these environment variables to your Render service:

```bash
# Essential Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
LAZY_LOAD_MODEL=true
USE_ML_EMBEDDINGS=true

# Memory Thresholds (MB)
MEMORY_WARNING_MB=1400
MEMORY_CRITICAL_MB=1700

# Batch Processing
MAX_BATCH_SIZE=16
EMBEDDING_BATCH_SIZE=8

# ChromaDB HNSW Settings (lower = less memory)
HNSW_M=8
HNSW_EF_CONSTRUCTION=64
HNSW_EF_SEARCH=32

# SQLite Memory Settings
SQLITE_CACHE_SIZE=-65536
SQLITE_PAGE_SIZE=4096
```

## Environment Variables Reference

### Embedding Model Selection

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | `paraphrase-MiniLM-L3-v2`, `all-MiniLM-L6-v2`, `all-MiniLM-L12-v2` | Model size vs quality tradeoff |
| `LAZY_LOAD_MODEL` | `true` | `true`, `false` | Only load model when first needed |
| `USE_ML_EMBEDDINGS` | `true` | `true`, `false` | Enable/disable ML embeddings |
| `USE_INT8_QUANTIZATION` | `false` | `true`, `false` | Reduce embedding storage by 75% |

**Model Comparison:**

| Model | Size | Dimension | Quality | Speed | Memory |
|-------|------|-----------|---------|-------|--------|
| `paraphrase-MiniLM-L3-v2` | 17MB | 384 | Good | Fastest | Lowest |
| `all-MiniLM-L6-v2` | 22MB | 384 | Better | Fast | Low |
| `all-MiniLM-L12-v2` | 33MB | 384 | Best | Medium | Medium |

**Recommendation:** Use `paraphrase-MiniLM-L3-v2` if you're tight on memory, or `all-MiniLM-L6-v2` for the best balance.

### Memory Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_WARNING_MB` | `1500` | RSS memory threshold for warnings |
| `MEMORY_CRITICAL_MB` | `1800` | RSS memory threshold for emergency actions |

When critical memory is reached:
1. Emergency garbage collection is triggered
2. ML embeddings fall back to hash-based
3. New documents are rejected until memory frees up

### Batch Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_BATCH_SIZE` | `32` | Max documents per ChromaDB batch insert |
| `EMBEDDING_BATCH_SIZE` | `16` | Max texts per embedding model batch |

Lower these if you experience memory spikes during bulk indexing.

### ChromaDB HNSW Settings

| Variable | Default | Standard | Description |
|----------|---------|----------|-------------|
| `HNSW_M` | `8` | `16` | Connections per layer (lower = less memory) |
| `HNSW_EF_CONSTRUCTION` | `64` | `100` | Search depth during index build |
| `HNSW_EF_SEARCH` | `32` | `10` | Search depth during query (higher = better recall) |

**Memory Impact:**
- Lower `HNSW_M` reduces memory by ~40% for the HNSW graph
- Lower `EF_CONSTRUCTION` reduces peak memory during indexing

### SQLite Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_CACHE_SIZE` | `-32768` | Page cache size in KB (negative = KB) |
| `SQLITE_PAGE_SIZE` | `4096` | Database page size in bytes |
| `SQLITE_TEMP_STORE` | `memory` | Where to store temporary tables |

### Optional Features

| Variable | Default | Description |
|----------|---------|-------------|
| `DISABLE_CHROMADB` | `false` | Completely disable ChromaDB (use file fallback) |
| `AUTO_UNLOAD_MODEL` | `false` | Unload embedding model after each use |
| `TRANSFORMERS_CACHE` | `/app/models` | Where to cache downloaded models |

## Render.yaml Configuration

Update your `render.yaml` with the optimized environment variables:

```yaml
services:
  - type: web
    name: cerebrum-api
    runtime: docker
    envVars:
      # ... other env vars ...
      
      # Embedding Model (smaller = less memory)
      - key: EMBEDDING_MODEL
        value: "all-MiniLM-L6-v2"
      
      # Memory Management
      - key: LAZY_LOAD_MODEL
        value: "true"
      - key: MEMORY_WARNING_MB
        value: "1400"
      - key: MEMORY_CRITICAL_MB
        value: "1700"
      
      # Batch Processing (lower = less memory)
      - key: MAX_BATCH_SIZE
        value: "16"
      - key: EMBEDDING_BATCH_SIZE
        value: "8"
      
      # ChromaDB HNSW (lower = less memory)
      - key: HNSW_M
        value: "8"
      - key: HNSW_EF_CONSTRUCTION
        value: "64"
      - key: HNSW_EF_SEARCH
        value: "32"
      
      # SQLite Memory
      - key: SQLITE_CACHE_SIZE
        value: "-65536"
      - key: SQLITE_PAGE_SIZE
        value: "4096"
      
      # Model Cache
      - key: TRANSFORMERS_CACHE
        value: "/data/models"
      - key: CHROMA_DB_PATH
        value: "/data/chromadb"
```

## Memory Monitoring API

The optimized service exposes memory stats via the health endpoint:

```python
# Get service stats
stats = chroma_service.get_stats_sync()
print(stats["memory"])
# {
#   "status": "normal",
#   "stats": {
#     "rss_mb": 850.5,
#     "vms_mb": 1200.0,
#     "percent": 45.2,
#     "available_mb": 950.0,
#     "timestamp": "2024-01-15T10:30:00"
#   },
#   "peak_mb": 920.0,
#   "actions": []
# }
```

## Troubleshooting

### Issue: Memory spikes during indexing

**Solutions:**
1. Reduce `MAX_BATCH_SIZE` to 8 or 4
2. Reduce `EMBEDDING_BATCH_SIZE` to 4
3. Use `paraphrase-MiniLM-L3-v2` instead of `all-MiniLM-L6-v2`

### Issue: Search quality degraded after lowering HNSW_M

**Solutions:**
1. Increase `HNSW_EF_SEARCH` to 64 or 128 (uses more CPU, not memory)
2. Consider using `all-MiniLM-L12-v2` for better embeddings

### Issue: Model loading is slow

**Solutions:**
1. Ensure `TRANSFORMERS_CACHE` points to persistent disk (`/data/models`)
2. The first load downloads the model (~22MB), subsequent loads are instant

### Issue: "Critical memory" warnings

**Solutions:**
1. Lower `MEMORY_WARNING_MB` and `MEMORY_CRITICAL_MB` thresholds
2. Enable `AUTO_UNLOAD_MODEL=true` (slower searches, but frees memory)
3. Reduce concurrent requests

## Performance Expectations (2GB RAM)

| Operation | Expected Performance |
|-----------|---------------------|
| Model Load | 2-5 seconds (first time) |
| Single Embedding | 10-50ms |
| Batch of 16 | 100-300ms |
| Search (1000 docs) | 20-50ms |
| Bulk Index (100 docs) | 5-15 seconds |
| Memory at Idle | 600-900MB |
| Memory at Peak | 1200-1600MB |

## Migration from Original Service

1. **Backup your data:**
   ```bash
   # Download from Render disk
   tar czf chromadb-backup.tar.gz /data/chromadb
   ```

2. **Update the service file:**
   ```bash
   cp chroma_service_optimized.py chroma_service.py
   ```

3. **Add psutil to requirements:**
   ```bash
   echo "psutil>=5.9.0" >> requirements.txt
   ```

4. **Deploy and monitor:**
   - Watch logs for memory status messages
   - Adjust thresholds based on actual usage

## Fallback Behavior

If memory becomes critical or ML model fails to load:

1. **Hash-based embeddings** are used automatically
2. **Semantic search** degrades to keyword-like matching
3. **All documents remain searchable**

To reindex with ML embeddings later:

```python
# After memory pressure is resolved
chroma_service.reindex_all(documents)
```
