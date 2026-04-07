# BIM & Infrastructure Reinstatement Roadmap

## Current State (bd8af2c - GREEN)
✅ Agent system fully working (14 layers, self-mod, web search)
✅ Frontend connected (useAgentChat, AgentChatInterface)
✅ Backend deploys fast (no conda)
❌ BIM IFC processing disabled
❌ Infrastructure data (85+ RSMeans items) missing

---

## Phase 1: Restore Safe Changes (No Breaking Risk)

### 1.1 Add Infrastructure Data Back
**Commits to cherry-pick:**
- `290e919` - RSMeans mock data (50+ items)
- `75a2520` - Infrastructure data (85+ items)

**Risk:** None - pure data additions
**Benefit:** Economics layer has full cost database

### 1.2 Add BIM Environment Variables
**Commit to cherry-pick:**
- `4016694` - BIM env vars to render.yaml and config.py

**Risk:** None - just config
**Benefit:** Ready for BIM when we add it

---

## Phase 2: Smart BIM Integration (No Conda)

### 2.1 Make ifcopenshell Truly Optional
```python
# In BIM endpoints - graceful fallback
IFC_ENABLED = False
try:
    import ifcopenshell
    IFC_ENABLED = True
except ImportError:
    logger.warning("ifcopenshell not available - BIM processing disabled")

@app.post("/bim/upload")
async def upload_ifc(file: UploadFile):
    # Always allow upload
    file_id = await store_file(file)
    
    if IFC_ENABLED:
        # Process in background
        asyncio.create_task(process_ifc_async(file_id))
    else:
        # Just store, return "processing unavailable"
        await mark_as_unprocessed(file_id)
    
    return {"file_id": file_id, "status": "stored" if not IFC_ENABLED else "processing"}
```

**Risk:** Low - BIM endpoints already have try/except
**Benefit:** App works with or without ifcopenshell

### 2.2 Attempt pip install ifcopenshell
**Try:** `pip install ifcopenshell` (not conda)
- If wheel exists for Linux x86_64 → Works!
- If not → Gracefully disabled

**Test:** Deploy, check logs for "ifcopenshell not available"

---

## Phase 3: Options if pip install fails

### Option A: Pre-built Base Image
Create a custom base image:
```dockerfile
FROM render/ifcopenshell-python3.11:latest
# Or use conda in builder stage only
```

**Effort:** Medium (need to maintain image)
**Speed:** Fast (pre-built)

### Option B: BIM Microservice
Separate service just for IFC processing:
- Main app: Fast, no ifcopenshell
- BIM service: Can use conda, heavy
- Communicate via HTTP queue

**Effort:** High (new service)
**Speed:** Fastest (main app unaffected)

### Option C: File Storage Only
Skip IFC parsing entirely:
- Upload works (stores to S3)
- Download works (get file back)
- No property extraction/takeoffs
- Add manual entry forms instead

**Effort:** Low
**Benefit:** Users can still attach IFC files

---

## Recommended Sequence

| Step | Action | Deploy After? |
|------|--------|---------------|
| 1 | Cherry-pick infrastructure data | ✅ Yes |
| 2 | Cherry-pick BIM env vars | ✅ Yes |
| 3 | Add graceful ifcopenshell handling | ✅ Yes |
| 4 | Try pip install ifcopenshell | ✅ Yes |
| 5 | If fails, decide: Option A/B/C | - |

---

## What We DON'T Touch

❌ No conda in Dockerfile
❌ No multi-stage builds (until we prove they work)
❌ No changes to agent system (it's working!)
❌ No frontend changes needed

---

## Decision Points

**After Step 3:** Is app still green? → Continue
**After Step 4:** Does ifcopenshell import? → If YES, done! If NO, pick Option A/B/C

Your call on which path to take.
