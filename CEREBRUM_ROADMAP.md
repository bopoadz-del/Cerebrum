# CEREBRUM ROADMAP - Local Implementation (No NVIDIA Hardware)

**Goal:** Build air-gapped-ready software now, deploy to NVIDIA hardware later.

---

## Phase 1: Local LLM Integration (Week 1-2) ✅ COMPLETE

### 1.1 Install Local Inference Engine
**Status:** ✅ Complete  
**Commits:** `8be1ff8`, `439029a`

**What's Running on Render:**
- ✅ Ollama installed in Dockerfile
- ✅ `gemma3:270m` (200MB) - default, fastest  
- ✅ `qwen2.5:0.5b` (400MB) - backup, better quality
- ✅ Auto-starts with FastAPI

**Render Resources:**
- Storage: ~600MB for both models
- RAM: ~300-500MB when active
- Fits within Starter tier (2GB RAM, 5GB disk)

**Local Development:**
- `llama3.2:1b` (1.3GB) - better quality for dev
- `llama3.2:3b` (2.0GB) - best quality (local only)

---

### 1.2 Replace Rule-Based Chat
**Status:** ✅ Complete  
**Commit:** `8be1ff8`

**Smart Routing Logic:**
```
Simple queries (hello, /cost) → Rule-based (fast)
Complex queries (why, how, explain) → Local LLM (smart)
```

**Acceptance:** "Tell me about concrete costs" → uses LLM. "/cost concrete" → uses rules.

---

## Phase 2: Semantic Search (Week 2-3) ✅ COMPLETE (Already Implemented)

### 2.1 Vector Database Setup
**Status:** ✅ Complete  
**Files:** `backend/app/services/chroma_service.py`

**What's Already Working:**
- ✅ ChromaDB persistent client (local storage)
- ✅ ML embeddings: `all-MiniLM-L6-v2` (22MB, 384-dim)
- ✅ Hash-based fallback (if ML model unavailable)
- ✅ File-based fallback storage
- ✅ Cosine similarity search

**Storage:** Embeddings stored in `/data/chroma_store` (~50MB per 1000 documents)

---

### 2.2 Document Embedding Pipeline
**Status:** ✅ Complete  
**Files:** `backend/app/api/v1/endpoints/documents.py`

**What's Already Working:**
- ✅ Auto-index on document upload (chat and Drive)
- ✅ Text extraction from PDFs/images
- ✅ Metadata extraction (filename, mime_type, source)
- ✅ ChromaDB indexing with embeddings

**How it works:**
1. User uploads document → `/documents/upload/chat`
2. Text extracted via OCR (if image/PDF)
3. ChromaDB generates embedding → stores vector + metadata
4. Document is now searchable by meaning

---

### 2.3 Semantic Search API
**Status:** ✅ Complete  
**Endpoint:** `GET /api/v1/documents/search`

**What's Already Working:**
- ✅ Natural language queries
- ✅ Semantic similarity ranking
- ✅ User-scoped results (only your docs)
- ✅ Source filtering (google_drive, chat_upload)

**Example Usage:**
```bash
# Search for documents about concrete costs
curl "https://cerebrum-api.onrender.com/api/v1/documents/search?query=concrete%20costs&top_k=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Returns ranked results by relevance
{
  "query": "concrete costs",
  "results": [
    {
      "id": "drive_abc123",
      "score": 0.89,
      "name": "Q2_Concrete_Invoice.pdf",
      "content_preview": "Invoice for 500 cubic yards...",
      "source": "google_drive"
    }
  ]
}
```

**Additional Endpoints:**
- `GET /documents/chroma/stats` - Index statistics
- `POST /documents/chroma/reindex` - Reindex with ML embeddings
- `POST /documents/chroma/hydrate` - Sync files with index

**Result:** Documents are searchable by meaning, not just keywords.

---

## Phase 3: Document Intelligence (Week 3-4)

### 3.1 Document Classification
**Status:** 🟡 Partial  
**What:** Auto-classify documents by type

**Current:** Basic rule-based classification exists
**Target:** ML-powered classification (local model)

**Tasks:**
- [ ] Train/fine-tune local classifier
- [ ] Categories: invoice, safety_report, blueprint, RFI, submittal
- [ ] Extract document on upload
- [ ] Store classification in database
- [ ] Show document type in UI

**Acceptance:** Upload invoice → classified as "invoice" automatically.

---

### 3.2 Information Extraction
**Status:** 🟡 Partial  
**What:** Extract key fields from documents

**Current:** Rule-based extraction exists
**Target:** Local LLM extraction

**Tasks:**
- [ ] Define extraction schemas per document type
- [ ] Use local LLM for structured extraction
- [ ] Extract: vendor, amount, date, project_code, etc.
- [ ] Store extracted fields in database
- [ ] Make searchable by extracted fields

**Acceptance:** Invoice → extracted vendor name, total amount, due date.

---

### 3.3 OCR for Images/Scans
**Status:** 🟡 Partial  
**What:** Read text from photos and scanned documents

**Current:** Tesseract OCR installed
**Target:** Enhanced with local vision models

**Tasks:**
- [ ] Verify Tesseract works (already installed in Dockerfile)
- [ ] Pre-process images (deskew, enhance)
- [ ] Extract text from uploaded images
- [ ] Feed OCR output to extraction pipeline
- [ ] Handle handwritten notes (defer to Phase 6 with better hardware)

**Acceptance:** Photo of invoice → extract text → extract fields.

---

## Phase 4: Autonomous Agent (Week 4-5)

### 4.1 Task Planning Engine
**Status:** 🟡 Partial  
**Files:** `backend/app/agent/enhanced_core.py`  
**What:** Break natural language tasks into executable steps

**Current:** Basic planning exists
**Target:** Enhanced with local LLM

**Tasks:**
- [ ] Improve task decomposition logic
- [ ] Define available tools for agent
- [ ] Create planning prompt for local LLM
- [ ] Generate step-by-step plan
- [ ] Store plan for execution tracking

**Acceptance:** "Analyze safety trends" → plan with steps: fetch reports, extract dates, count by month, trend analysis.

---

### 4.2 Tool Execution Framework
**Status:** 🟡 Partial  
**What:** Agent can actually execute planned steps

**Current:** Tool system exists
**Target:** Full execution with local LLM

**Tasks:**
- [ ] Document available tools to agent
- [ ] Tool selection logic
- [ ] Parameter extraction from context
- [ ] Step-by-step execution with state
- [ ] Error handling and retry logic

**Acceptance:** Agent executes full plan and returns result with explanation.

---

### 4.3 Self-Coding (Sandboxed)
**Status:** 🟡 Partial  
**What:** Generate and safely execute code for new document types

**Current:** Code gen exists, needs sandbox
**Target:** Full self-coding

**Tasks:**
- [ ] Docker-based sandbox for code execution
- [ ] Code generation for new parsers
- [ ] Safety checks (no network, no file system escape)
- [ ] Test generated code in sandbox
- [ ] Auto-deploy if tests pass
- [ ] Rollback if failures detected

**Acceptance:** New invoice format → generate parser → test → deploy → process documents.

---

## Phase 5: Air-Gap Preparation (Week 5-6)

### 5.1 Offline-First Architecture
**Status:** Not started  
**What:** Ensure everything works without internet

**Storage Strategy:**
- **Cloud (Render):** Use smaller models (gemma3:270m, qwen2.5:0.5b)
- **Local/Edge:** Use larger models (3B-70B params) with full storage
- **Model cache:** Download once, reuse across restarts

**Tasks:**
- [ ] Audit all external API calls
- [ ] Make external calls optional with graceful fallback
- [ ] Bundle all models/assets locally
- [ ] Ensure no CDN dependencies in frontend
- [ ] Test with network disabled

**Acceptance:** Disconnect internet → system continues operating normally.

---

### 5.2 Local-Only Deployment Package
**Status:** Not started  
**What:** Create deployable package for on-premise installation

**Tasks:**
- [ ] Docker Compose for full stack
- [ ] Single-command installation script
- [ ] Pre-downloaded models bundled or cached
- [ ] Model size detection (auto-select based on hardware)
- [ ] Configuration for local network only
- [ ] Documentation for IT deployment

**Acceptance:** New server → run install script → Cerebrum ready in 30 minutes.

---

### 5.3 Data Migration Path
**Status:** Not started  
**What:** Migrate from cloud (Render) to local

**Tasks:**
- [ ] Export all data from Render PostgreSQL
- [ ] Export document embeddings from ChromaDB
- [ ] Create import script for local deployment
- [ ] Verify data integrity after migration
- [ ] Document rollback procedure

**Acceptance:** Cloud data → local server → everything works.

---

## Phase 6: Hardware Integration Prep (Week 6-8)

### 6.1 Jetson Deployment Scripts
**Status:** Not started  
**What:** Scripts to deploy Cerebrum to NVIDIA Jetson

**Tasks:**
- [ ] Jetson Orin Nano setup script
- [ ] Jetson Nano (Eyes) setup script
- [ ] Cross-compilation for ARM64
- [ ] Model optimization for Jetson (TensorRT)
- [ ] Network configuration for local mesh

**Acceptance:** Run script on Jetson → Cerebrum deployed and running.

---

### 6.2 Safety Detection (The Eyes)
**Status:** Not started  
**What:** YOLO-based safety monitoring

**Tasks:**
- [ ] YOLOv8 model for PPE detection
- [ ] Hardhat detection
- [ ] Safety vest detection
- [ ] Restricted zone intrusion
- [ ] Event logging with photo + timestamp
- [ ] Sync to Brain when network available

**Acceptance:** Camera sees no hardhat → logs event with photo.

---

### 6.3 Multi-Device Orchestration
**Status:** Not started  
**What:** Brain coordinates multiple Eyes

**Tasks:**
- [ ] Device discovery protocol
- [ ] Heartbeat monitoring
- [ ] Centralized configuration
- [ ] Firmware update mechanism
- [ ] Failover handling

**Acceptance:** 10 Eyes + 1 Brain → all coordinated, sync when online.

---

## Current Status Tracker

| Phase | Component | Status | Priority |
|-------|-----------|--------|----------|
| **1** | Local LLM Engine | ✅ Complete | P0 |
| **1** | Smart Chat Routing | ✅ Complete | P0 |
| **2** | ChromaDB Vector DB | ✅ Complete | P1 |
| **2** | Document Embeddings | ✅ Complete | P1 |
| **2** | Semantic Search API | ✅ Complete | P1 |
| 3.1 | Doc Classification | 🟡 Partial | P2 |
| 3.2 | Info Extraction | 🟡 Partial | P2 |
| 3.3 | OCR | 🟡 Partial | P2 |
| 4.1 | Task Planning | 🟡 Partial | P1 |
| 4.2 | Tool Execution | 🟡 Partial | P1 |
| 4.3 | Self-Coding | 🟡 Partial | P2 |
| 5.1 | Offline-First | 🔴 Not started | P1 |
| 5.2 | Local Deploy Package | 🔴 Not started | P2 |
| 5.3 | Data Migration | 🔴 Not started | P3 |
| 6.x | Hardware Integration | 🔴 Not started | P3 |

**Legend:**
- 🔴 Not started
- 🟡 Partial/In progress
- ✅ Complete

---

## Next Actions (Immediate)

1. **Phase 3.3 - OCR Enhancement** - Improve document text extraction
2. **Phase 3.2 - Better Extraction** - Structured data from invoices
3. **Phase 5.1 - Offline-First** - Make all external calls optional

**Ready to continue?**
