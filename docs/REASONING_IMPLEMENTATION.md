# Kimi-Style Reasoning Implementation

## Overview

This implementation adds transparent AI reasoning (Kimi-style) to the Cerebrum Agent, enabling step-by-step visibility into the agent's decision-making process.

## Key Features

### 1. `reasoning_content` Field
- Added to `AgentResult` class in both `core.py` and `enhanced_core.py`
- Contains step-by-step reasoning/thinking process
- Preserved across multi-turn conversations when configured

### 2. ReasoningTracker Class
Location: `backend/app/agent/enhanced_core.py`

Provides:
- **Step tracking**: Task received, thinking, observation, decision, tool call, error, conclusion
- **Multiple format styles**: markdown (default), plain, structured (JSON)
- **Multi-turn preservation**: Reasoning context maintained across conversations
- **Session management**: Unique session IDs for reasoning chains

### 3. AgentReasoningConfig Class
Configuration options:
- `enabled`: Enable/disable reasoning generation
- `include_in_response`: Include in API responses
- `max_reasoning_length`: Limit reasoning content length
- `preserve_across_turns`: Keep reasoning across multi-turn conversations
- `format_style`: markdown, plain, or structured

### 4. Enhanced Agent Execution
The `run()` method in `EnhancedCerebrumAgent` now:
- Tracks reasoning from task reception to conclusion
- Records layer navigation decisions
- Captures tool selection rationale
- Documents observations and errors
- Formats reasoning for response

### 5. API Endpoints

#### Execute Task with Reasoning
```
POST /api/v1/agent/execute
```
Request body now includes:
- `include_reasoning`: Include reasoning in response
- `reasoning_format`: Format style preference

Response includes:
- `reasoning_content`: Step-by-step reasoning
- `execution_time_ms`: Execution time

#### Reasoning Configuration
```
GET  /api/v1/agent/reasoning/config    # Get current config
POST /api/v1/agent/reasoning/config    # Update config
GET  /api/v1/agent/reasoning/history   # Get reasoning history
POST /api/v1/agent/reasoning/clear     # Clear reasoning history
```

## Usage Examples

### Basic Usage
```python
# Execute task with reasoning
result = await agent.run("Calculate concrete costs for 10x20 slab")
print(result.reasoning_content)
```

### Via API
```bash
# Execute with reasoning
curl -X POST http://api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Calculate concrete costs",
    "include_reasoning": true,
    "reasoning_format": "markdown"
  }'
```

### Response Format
```json
{
  "success": true,
  "action": "READ_MEMORY",
  "layer": "ECONOMICS",
  "data": {...},
  "message": "Calculation complete",
  "timestamp": "2024-01-01T00:00:00",
  "reasoning_content": "## Reasoning Process\n\n### Step 1: Task Received...",
  "execution_time_ms": 1250.5
}
```

## Reasoning Content Format

### Markdown Style (Default)
```markdown
## Reasoning Process

### Step 1: Task Received
*2024-01-01T00:00:00*
Starting task: Calculate concrete costs for 10x20 slab
---

### Step 2: Thinking
Detected cost calculation query
---

### Step 3: Decision
Selected layer: ECONOMICS
**Rationale:** Best match for cost calculation task
---
```

### Plain Style
```
Reasoning Process:

📥 [1] Task Received
   Starting task: Calculate concrete costs
   
🤔 [2] Thinking
   Detected cost calculation query
```

### Structured Style (JSON)
```json
{
  "session_id": "reasoning_20240101_000000_12345",
  "total_steps": 5,
  "steps": [...]
}
```

## Multi-Turn Preservation

When `preserve_across_turns` is enabled:
1. First turn: New reasoning tracker initialized
2. Subsequent turns: Previous reasoning merged with current
3. Each turn adds steps to the growing chain
4. Provides full context across conversation

## Configuration

### Disable Reasoning
```bash
POST /api/v1/agent/reasoning/config
{
  "enabled": false
}
```

### Change Format
```bash
POST /api/v1/agent/reasoning/config
{
  "format_style": "plain",
  "max_reasoning_length": 5000
}
```

## Files Modified

1. **backend/app/agent/core.py**
   - Added `reasoning_content` to `AgentResult`

2. **backend/app/agent/enhanced_core.py**
   - Added `reasoning_content` to enhanced `AgentResult`
   - Added `AgentReasoningConfig` dataclass
   - Added `ReasoningTracker` class
   - Updated `EnhancedCerebrumAgent.__init__()`
   - Updated `run()` method with reasoning tracking
   - Updated `move_to_layer()` with reasoning

3. **backend/app/agent/endpoints.py**
   - Added `reasoning_content` to `AgentTaskResponse`
   - Added `include_reasoning` to `AgentTaskRequest`
   - Added reasoning configuration models
   - Added reasoning endpoints (config, history, clear)

4. **backend/app/agent/__init__.py**
   - Exported `ReasoningTracker` and `AgentReasoningConfig`

## Benefits

1. **Transparency**: Users can see how the agent arrives at conclusions
2. **Debugging**: Easier to identify where reasoning goes wrong
3. **Education**: Users learn how to phrase tasks better
4. **Trust**: Builds confidence in agent decisions
5. **Multi-turn Context**: Maintains reasoning across conversation turns

## Kimi K2-Thinking Style

This implementation follows the Kimi K2-Thinking model:
- Step-by-step reasoning displayed alongside results
- Thinking process visible to users
- Decisions explained with rationale
- Tool calls documented with parameters
- Errors captured with recovery attempts
