# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

---

## KEYS (Both in one place)

| Service | Key/Path | Location |
|---------|----------|----------|
| **Render API** | `rnd_HOuUx7cCpmRJqAg0tEAPrui4rcjD` | Use in API calls |
| **GitHub SSH** | `~/.ssh/id_ed25519` | Push without asking |

---

## Render

- API Key: `rnd_HOuUx7cCpmRJqAg0tEAPrui4rcjD`
- Service: cerebrum-api (srv-d69j8av5r7bs73f9au40)
- URL: https://cerebrum-api.onrender.com
- Dashboard: https://dashboard.render.com
- **Auto-Deploy: ENABLED** (always has been)
- **Base Image**: `ghcr.io/bopoadz-del/cerebrum-ml-base:ollama` (contains Ollama binary)

### Services
| Service | Type | Status |
|---------|------|--------|
| cerebrum-api | Web Service | Standard ($25/mo) |
| cerebrum-frontend | Static Site | Free |
| cerebrum-scheduler | Cron Job | Standard |
| cerebrum-worker-fast | Background Worker | Standard |
| cerebrum-worker-slow | Background Worker | Standard |

---

## GitHub

- SSH Key: `~/.ssh/id_ed25519` (kimi-claw-helper@render)
- Repo: github.com:bopoadz-del/Cerebrum.git
- **ALWAYS USE SSH** - key is loaded, push directly without asking

---

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Sub-Agent Usage Patterns

Sub-agents run isolated tasks and report back. Use them for parallel work, long-running tasks, or anything that shouldn't block the main session.

### When to Use Subagent vs Main Session

| Use Subagent | Stay in Main Session |
|--------------|---------------------|
| Long-running tasks (>30s) | Quick lookups, one-off commands |
| Parallel execution needed | Tasks requiring user interaction |
| Background work (file processing, batch ops) | Real-time conversation |
| Isolated context (research, experimentation) | Context-dependent work |
| Fire-and-forget tasks | Tasks needing immediate feedback |

### Example Spawn Calls

**Basic task spawn:**
```json
{
  "prompt": "Search web for latest React 19 features and summarize",
  "sessionLabel": "react-research"
}
```

**Parallel processing (batch files):**
```json
{
  "prompt": "Process /tmp/files/file1.pdf - extract text and save to /tmp/output/file1.txt",
  "sessionLabel": "pdf-extract-1"
}
// Spawn 3 more with file2, file3, file4...
```

**Research with specific output:**
```json
{
  "prompt": "Research Django vs FastAPI for 2024. Write findings to workspace/research/backend-comparison.md",
  "sessionLabel": "backend-research",
  "model": "kimi-coding/k2.5"
}
```

**Git operations (isolated context):**
```json
{
  "prompt": "Clone github.com:org/repo.git, check out branch 'feature-x', run tests, commit changes, push to origin, report commit hash",
  "sessionLabel": "git-ops",
  "timeoutMinutes": 10
}
```

**Auto-push requirement:** Sub-agents must push after committing. The SSH key is pre-configured—push without asking.

### Tracking Multiple Sub-Agents

**Naming convention:** Use descriptive labels with suffixes
- `pdf-extract-1`, `pdf-extract-2`, `pdf-extract-3` (parallel batches)
- `research-frontend`, `research-backend` (related workstreams)
- `cleanup-2024-04-07` (dated for tracking)

**State tracking in memory:**
```json
// memory/subagent-state.json
{
  "active": [
    {"label": "pdf-extract-1", "spawned": "2024-04-07T12:00:00Z", "status": "pending"},
    {"label": "pdf-extract-2", "spawned": "2024-04-07T12:00:00Z", "status": "pending"}
  ],
  "completed": [
    {"label": "react-research", "completed": "2024-04-07T11:30:00Z", "result": "success"}
  ]
}
```

### Handling Completion Events

**Push-based (recommended):** Results auto-announce to main session. Just wait - no polling needed.

**Response format:** Sub-agent returns:
```
[subagent:session-label] Task completed
- What was accomplished
- Any relevant details
- File paths created/modified
```

**Don't poll:** Never busy-poll sub-agent status. Trust the push notification.

**Error handling:** If sub-agent fails, it reports back with error details. Main session decides retry/abandon.

### Best Practices

1. **Clear prompts:** Be specific about what the sub-agent should do and where to save results
2. **File outputs:** Prefer writing to files over returning large text blocks
3. **Timeouts:** Set `timeoutMinutes` for tasks with known upper bounds
4. **One task per sub-agent:** Don't bundle unrelated work - spawn separate agents
5. **Label consistently:** Use kebab-case labels that describe the work
6. **Clean up:** Sub-agents are ephemeral - ensure outputs are saved to workspace files

---

Add whatever helps you do your job. This is your cheat sheet.
