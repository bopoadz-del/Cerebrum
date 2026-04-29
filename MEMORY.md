# MEMORY.md

**Note:** Critical protocols (Coding Protocol, Conversation Protocol) are in `SOUL.md` — read them from there.

---

## WORKFLOW PRACTICES

### Sub-Agent Usage (CRITICAL)
**Always use sub-agents for tasks** - This allows Chadi to reach me while I'm working. No more waiting until I finish. Even if he has a second opinion, he can interrupt/redirect.

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
