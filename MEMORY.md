# MEMORY.md

**Note:** Critical protocols (Coding Protocol, Conversation Protocol) are in `SOUL.md` — read them from there.

---

## WORKFLOW PRACTICES

### Sub-Agent Usage (CRITICAL)
**Always use sub-agents for tasks** - This allows Chadi to reach me while I'm working. No more waiting until I finish. Even if I misunderstand or he has a second opinion, he can interrupt/redirect.

#### When to Use Sub-Agents

Spawn a sub-agent for any task that meets these criteria:

| Criteria | Examples |
|----------|----------|
| **Duration >30 seconds** | File processing, data analysis, API calls, web scraping |
| **Parallel work streams** | Multiple independent tasks that can run simultaneously |
| **Multi-step operations** | Git workflows (clone, modify, commit, push), deployments |
| **Long-running tasks** | Model training, batch processing, build/test pipelines |
| **Research tasks** | Web searches, document analysis, fact-checking |
| **Isolated experiments** | Testing code changes, trying alternative approaches |

**Rule of thumb:** If you'd tell a human "this will take a minute," use a sub-agent.

#### Spawn Settings

```json
{
  "runtime": "subagent",
  "label": "descriptive-task-name",
  "description": "What this sub-agent is doing"
}
```

**Important:** `streamTo` is **NOT available** for sub-agents. Results auto-announce back to the parent when complete. The parent session receives the sub-agent's final response automatically — no polling needed.

#### Sub-Agent Git Workflow (CRITICAL)

Sub-agents MUST auto-push after committing. Never ask for permission to push.

**Required sequence:**
1. `git add -A`
2. `git commit -m "descriptive message"`
3. `git push origin main`
4. Report: `Pushed: <commit_hash>`

This is a fire-and-forget workflow. The SSH key is already configured (`~/.ssh/id_ed25519`). Push directly without asking.

#### Benefits of Sub-Agents

1. **User Can Interrupt** - Chadi can send new messages while sub-agents work; main agent remains responsive
2. **Second Opinions** - Multiple sub-agents can work on the same problem in parallel with different approaches
3. **No Waiting** - User isn't blocked; sub-agents work in background
4. **Error Isolation** - Failed sub-agents don't crash the main session
5. **Parallel Processing** - Multiple tasks complete faster than sequential execution
6. **Checkpoint Recovery** - Sub-agent results persist even if parent restarts

#### Labeling Conventions

Use descriptive, consistent labels for tracking:

| Pattern | Example | Purpose |
|---------|---------|---------|
| `action-target` | `deploy-render`, `analyze-csv` | General tasks |
| `research-topic` | `research-llm-costs`, `research-apis` | Research tasks |
| `fix-component` | `fix-auth-bug`, `fix-ui-layout` | Bug fixes |
| `experiment-goal` | `experiment-new-parser`, `experiment-rag` | Experiments |
| `batch-task` | `batch-process-files`, `batch-emails` | Batch operations |

#### Examples of Good Sub-Agent Tasks

**Development Tasks:**
- Clone a repository and analyze its structure
- Run test suites across multiple files
- Generate code from templates
- Perform refactorings across multiple files
- Build and deploy applications

**Data Tasks:**
- Process large CSV/JSON files
- Scrape web data
- Analyze datasets and generate reports
- Migrate data between formats
- Batch update records

**Research Tasks:**
- Search for latest documentation/API changes
- Compare multiple libraries/tools
- Analyze competitor features
- Find code examples and patterns
- Verify facts and claims

**Operational Tasks:**
- Monitor deployment status
- Check service health across multiple endpoints
- Generate documentation from code
- Clean up old files/logs
- Sync data between systems

**Parallel Examples:**
```
Simultaneous sub-agents:
- Sub-agent A: Research pricing APIs
- Sub-agent B: Research authentication options
- Sub-agent C: Research rate limiting strategies
→ Parent combines results for comprehensive comparison
```

---

## CEREBRUM VISION (Reference Document)

**The Goal:** An on-premise, air-gapped construction AI operating system that runs entirely inside a construction company's server room—no internet required, no cloud subscriptions, no data leaks.

### Hardware Architecture (Target)

**The Brain (Jetson Orin Nano - $500)**
- Site office server, internal network only
- 16GB RAM, 1,000 CUDA cores
- Database, document AI, reasoning engine
- 10 years project data storage
- Custom AI model training

**The Eyes (10x Jetson Nano - $250 each)**
- Mounted on cranes, pits, entrances
- Camera + 4GB RAM each
- 24/7 safety detection: hardhats, vests, zones
- Offline-first: stores locally, syncs when network returns

### Core Capabilities (Target)

**1. Document Intelligence**
- Drop PDFs/photos into folder → auto-processed
- Reads handwritten notes, blurry photos
- Classifies: invoice vs safety report vs blueprint
- Extracts: vendor names, amounts, dates, project codes

**2. Semantic Search**
- Ask questions, not search filenames
- "Find concrete invoices over $10K from last month"
- Understands meaning, not just keywords

**3. Safety Monitoring**
- Detects: no hardhat, no vest, restricted zone entry
- Logs: photo + timestamp + location
- No human watching 40 feeds

**4. Self-Coding AI**
- New document format? Writes parser automatically
- Tests in sandbox, deploys if safe
- No software engineer needed

**5. Autonomous Agent**
- Plain English tasks:
  - "Analyze safety reports for accident trends"
  - "Compare invoices to budget, flag anomalies"
  - "Summarize RFIs pending >5 days"
- Breaks into steps, executes, explains reasoning

### 14-Layer Architecture (Target)

1. **Governance** - Access control, audit trails, security rules
2. **Documents** - Reading and understanding files
3. **Spatial** - Linking docs to physical locations (BIM)
4. **ML Lab** - Training/testing AI models
5. **Sandbox** - Safe code execution
6. **Hardware** - Managing edge devices (Orin/Nano)
7. **Workflows** - Document routing
8. **Gateway** - External connections (if internet available)
9. **Self-Coding** - Writing parsers for new formats
10. **Events** - Real-time triggers and alerts
11. **Warehouse** - Long-term data storage
12. **Identity** - Login and permissions
13. **Monitoring** - System performance
14. **Healing** - Self-repair when things break

*Each layer operates independently. If one breaks, others continue.*

### Security Model

- **Air-gapped:** Works offline. No internet for daily ops.
- **Encrypted:** AES-256 hardware-accelerated
- **One-way flow:** Internal → summary outward only
- **Local only:** Raw documents never leave the building

### AI Model Strategy

**Training (Cloud, once):**
- Tinker ML customizes Llama 3.2 for construction
- Trained model downloaded to Orin box
- Internet only for training, not inference

**Inference (Local, always):**
- Llama 3.2 runs on Orin
- ZVec vector database for semantic search
- Entirely offline operation

### Integration Capabilities

- **BIM/IFC:** Link docs to 3D coordinates
- **Drones:** Aerial footage for progress tracking
- **Mobile:** Field photos with GPS
- **Export:** Procore, BIM 360, Excel when needed

### The Difference

**Traditional Software:**
- Upload to cloud (security risk)
- Monthly subscriptions forever
- Requires perfect internet
- Hire engineers to customize

**Cerebrum:**
- Your hardware (data sovereignty)
- Works offline (construction reality)
- Self-adapts to your docs
- $1,250 hardware cost, then free

---


---

## GitHub Repository
- **Repo URL:** git@github.com:bopoadz-del/Cerebrum.git
- **Local path:** /root/.openclaw/workspace/cerebrum-fix

## Deployment Notes
- Using Render for deployment
- Auto-deploy enabled from GitHub pushes
- Environment variable RSMEANS_API_KEY added to Render

## SSH Key Status
- Need private SSH key to push to GitHub from this server
- User mentioned they already provided it in a previous conversation

## Agent Enhancement (2025-01-20)

### Files Created
- `backend/app/agent/enhanced_core.py` - Enhanced agent with semantic memory search, layer navigation
- `backend/app/agent/enhanced_endpoints.py` - REST API endpoints for enhanced features

### Key Features
- **Semantic Memory Search**: Relevance scoring, indexed conversations, insights extraction
- **Layer Navigation**: Dependency checking, state management, transition tracking
- **All 14 Layers Connected**: Each layer has tools available via `/agent/v2` endpoints

### New Endpoints
- `/api/v1/agent/v2/execute` - Enhanced task execution
- `/api/v1/agent/v2/memory/*` - Memory search and management
- `/api/v1/agent/v2/layer/*` - Layer navigation and state
- `/api/v1/agent/v2/tools` - Tool listing

### Commit
`cdd5390` - "Add enhanced agent: semantic memory search, layer navigation, all endpoints connected"

## Self-Modification Engine (2025-03-15)

### Files Created
- `backend/app/agent/self_modification.py` - Core self-modification engine
- `backend/app/agent/self_modification_endpoints.py` - REST API for self-mod

### Capabilities
The agent can now modify its own codebase:

**1. Dynamic Layer Creation**
- Generate new architectural layers with tools
- Automatic dependency resolution
- Safety-checked code generation

**2. Code Modification**
- Find-and-replace modifications
- AI-powered refactoring
- Pattern-based changes

**3. Safety Mechanisms**
- Git checkpoint before any change
- Syntax validation
- Dangerous pattern detection (eval, exec, os.system)
- Automatic rollback on failure
- Approval workflow (can be bypassed for autonomous mode)

**4. Git Integration**
- Every change is tracked
- Rollback points created
- Modification history stored
- Author attribution to "Cerebrum Agent"

### API Endpoints

**Layer Management:**
- `POST /api/v1/agent/self-mod/layers/create` - Create new layer
- `GET /api/v1/agent/self-mod/layers/pending` - List pending layers

**Code Modification:**
- `POST /api/v1/agent/self-mod/code/modify` - Modify existing code
- `POST /api/v1/agent/self-mod/code/refactor` - AI refactoring
- `POST /api/v1/agent/self-mod/validate` - Validate code safety

**Approval Workflow:**
- `POST /api/v1/agent/self-mod/modifications/{id}/approve`
- `POST /api/v1/agent/self-mod/modifications/{id}/reject`
- `POST /api/v1/agent/self-mod/modifications/{id}/apply`
- `POST /api/v1/agent/self-mod/modifications/{id}/rollback`

**Autonomous Mode:**
- `POST /api/v1/agent/self-mod/autonomous/execute` - One-shot execution

### Safety Checks
Blocks: `eval()`, `exec()`, `os.system()`, `subprocess.call(shell=True)`, `rm -rf`
Requires: Syntax validation, Git checkpoint, Test validation

### Commit
`b35da55` - "Add self-modification engine: dynamic layer creation, code modification, git tracking, safety checks"

## Code Enhancement System (2025-03-15)

### Files Created
- `backend/app/agent/code_enhancement.py` - Code analysis and enhancement engine
- `backend/app/agent/enhancement_endpoints.py` - REST API for code enhancement

### Capabilities
The agent can analyze and improve existing code:

**1. Issue Detection**
- Bare except clauses
- Mutable default arguments
- Missing docstrings
- Missing type hints
- Long/complex functions
- Hardcoded secrets
- Deep nesting

**2. Automatic Enhancement**
- Fix error handling patterns
- Add missing docstrings
- Add type annotations
- Refactor complex code

**3. Analysis Features**
- Code metrics (LOC, complexity, coverage)
- Health score (0-100)
- Prioritized improvement list
- Diff preview before apply

### API Endpoints

**Analysis:**
- `POST /api/v1/agent/enhance/analyze` - Analyze file for issues
- `GET /api/v1/agent/enhance/scan` - Scan repository for improvements
- `GET /api/v1/agent/enhance/metrics/{file}` - Get file metrics

**Enhancement:**
- `POST /api/v1/agent/enhance/preview` - Preview enhancement diff
- `POST /api/v1/agent/enhance/apply` - Apply enhancement with git tracking
- `POST /api/v1/agent/enhance/autonomous` - Auto-enhance by target goal

**Utilities:**
- `GET /api/v1/agent/enhance/issues/types` - List detectable issues

### Example Usage

```bash
# Analyze a file
curl -X POST /api/v1/agent/enhance/analyze \
  -d '{"file_path": "backend/app/agent/core.py"}'

# Preview error handling improvements
curl -X POST /api/v1/agent/enhance/preview \
  -d '{"file_path": "backend/app/agent/core.py", "enhancement_types": ["error_handling"]}'

# Autonomously fix error handling across agent code
curl -X POST /api/v1/agent/enhance/autonomous?target=error+handling&scope=backend/app/agent
```

### Commit
`fbb7c13` - "Add code enhancement system: auto-analyze, detect issues, improve code quality"

## Frontend-Agent Connection (2025-03-15)

### Files Created/Modified
- `frontend/src/hooks/useAgentChat.ts` - React hook for agent chat
- `frontend/src/components/AgentChatInterface.tsx` - Agent chat UI component
- `frontend/src/App.tsx` - Added agent mode toggle

### Features
**Agent Mode Toggle**
- Switch between Standard and Agent chat modes
- Visual indicator showing current layer
- Persistent session ID for memory

**useAgentChat Hook**
- Connects to `/api/v1/agent/v2/execute` endpoint
- Memory search via `/api/v1/agent/v2/memory/search`
- Layer navigation via `/api/v1/agent/v2/layer/navigate`
- Real-time layer display

**Agent Commands in Chat:**
- `/agent status` - Check agent status
- `/agent layers` - List available layers
- `/agent navigate <layer>` - Switch to a layer
- `/agent search <query>` - Search memory
- `/agent enhance` - Run code enhancement
- `/agent help` - Show all commands

**Natural Language Support**
- Type any request and agent routes to appropriate layer
- Automatic memory search before response
- Suggested next actions based on context

### UI Elements
- Brain icon for agent mode
- Layer badge showing current layer (coding, economics, vdc, etc.)
- Suggested prompts for agent tasks
- Full markdown rendering for responses

### Commit
`9bf594b` - "Connect agent to frontend: add useAgentChat hook, AgentChatInterface, and mode toggle"


## Agent Entry [2026-04-01 00:19:43]
**Tags:** #test, #pricing

Test memory entry about concrete costs and RSMeans pricing


## Agent Entry [2026-04-01 12:24:58]
**Tags:** #test, #chat, #concrete
**Layers:** economics

Testing the agent chat interface - concrete costs for foundation work


## Agent Entry [2026-04-01 17:14:26]
**Tags:** #memory_write

Cerebrum is an AI-powered construction intelligence platform designed for construction management, cost estimation, and building information modeling (BIM). It combines traditional construction industry knowledge with modern AI capabilities including RSMeans integration for cost data, BIM analysis for IFC models, autonomous agent with 14 specialized layers, voice interface, and Google Drive project management integration.


## Agent Entry [2026-04-01 17:14:26]
**Tags:** #memory_write

Cerebrum implements a 14-layer architecture: 1) Coding - self-coding generation, 2) Registry - capability registry, 3) Validation - security & testing, 4) Hotswap - dynamic deployment, 5) Healing - self-healing, 6) Prompts - prompt management, 7) Triggers - event triggers, 8) Economics - cost estimation, 9) VDC - virtual design & construction, 10) Edge - edge inference, 11) Portal - user portal, 12) Enterprise - security/auth, 13) Connectors - external integrations, 14) Monitoring - observability. The agent can navigate between layers using POST /api/v1/agent/layer/move


## Agent Entry [2026-04-01 17:14:26]
**Tags:** #memory_write

The Cerebrum chat interface has two modes: Standard Mode for quick commands like /cost, /estimate, /formula, /search, and Agent Mode for complex multi-step tasks. The interface supports desktop (3-panel layout) and mobile (tab-based), with features like Smart Context (auto-brief at 90% capacity), file attachments, voice input, web search, copy/share, and timestamps.


## Agent Entry [2026-04-01 17:14:26]
**Tags:** #memory_write

Common Cerebrum commands: /help shows all commands, /cost <item> searches RSMeans, /estimate <type> <size> for building estimates (types: office, warehouse, retail, hospital, school, apartment, hotel), /formula <query> finds construction formulas, /search <query> searches documents, /layer <name> switches layers, /status shows agent status, /plan <goal> creates execution plans.


## Agent Entry [2026-04-01 17:14:26]
**Tags:** #memory_write

Cost estimation features include RSMeans integration with CSI MasterFormat divisions (01-33), location cost indices by region (Northeast, West, Midwest, South, Mountain), quick building estimates by type, detailed line-item estimates with contingency, and construction formulas (concrete volume, rebar weight, beam moment, cost per sf, earned value metrics). API endpoints: /api/v1/economics/rsmeans/search, /api/v1/economics/estimate/quick, /api/v1/economics/estimate.
