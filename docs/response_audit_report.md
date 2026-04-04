# Cerebrum Agent Response Formatting Audit Report

**Date:** 2026-04-01  
**Scope:** 14 Agent Layers - Response Formatting Consistency Audit  
**Files Audited:**
- `backend/app/agent/enhanced_core.py` (2,847 lines)
- `backend/app/agent/core.py` (765 lines)
- `backend/app/agent/economics_tools.py` (620 lines)
- `backend/app/agent/coding_tools.py` (650 lines)
- `backend/app/agent/code_enhancement.py` (739 lines)
- `backend/app/agent/endpoints.py` (650 lines)
- `backend/app/agent/planner.py` (430 lines)
- `backend/app/agent/scheduler.py` (420 lines)
- `backend/app/agent/websocket.py` (380 lines)
- `backend/app/agent/web_search.py` (240 lines)

---

## Executive Summary

The Cerebrum agent system uses **inconsistent response formatting patterns** across its 14 layers. While individual tools work correctly, the lack of standardization creates:

1. **Inconsistent user experience** - Same operation types return different structures
2. **Integration difficulties** - API consumers must handle multiple formats
3. **Maintenance burden** - Changes require updates in multiple places
4. **Error handling gaps** - Some layers lack proper error formatting

**Critical Finding:** There are at least **7 different response format patterns** in use across the codebase.

---

## 1. Current Response Formats by Layer

### 1.1 Enhanced Core Layer (Primary Formatters)

**Location:** `backend/app/agent/enhanced_core.py`

#### _format Methods (13 total):

| Method | Purpose | Format Style |
|--------|---------|--------------|
| `_format_currency()` | Currency display | Markdown emoji + formatted number |
| `_format_number()` | Number formatting | Comma-separated decimals |
| `_format_result_message()` | Main dispatcher | Calls specific formatters |
| `_format_error_message()` | Error responses | Structured help + suggestions |
| `_format_memory_search_result()` | Memory results | Grouped by source + truncated |
| `_format_economics_result()` | Cost estimates | Markdown headers + breakdown |
| `_format_formula_result()` | Calculations | Input/output sections |
| `_format_formula_search_result()` | Formula list | Numbered list + examples |
| `_format_bim_result()` | BIM queries | Grouped by element type |
| `_format_quantities_result()` | Quantity takeoffs | Totals + breakdown |
| `_format_validation_result()` | Code validation | Status + issue list |
| `_format_generation_result()` | Code generation | Success confirmation |
| `_format_healing_result()` | Error healing | Status + recommendations |

**Format Style:** Rich Markdown with emoji indicators, structured headers, bullet lists

**Example:**
```python
return f"""## Cost Estimate: {building.title()}

**Project Details**
- Location: {city}
- Building Size: {self._format_number(size, 0)} sq ft

**Total Estimated Cost: {self._format_currency(total)}**"""
```

---

### 1.2 Core Agent Layer (Tool Results)

**Location:** `backend/app/agent/core.py`

**Format Pattern:** Simple dict with `success` + `error`/`data`

```python
# Success pattern
return {
    "success": True,
    "file": file_path,
    "lines_added": len(new_lines),
    "timestamp": datetime.now().isoformat()
}

# Error pattern  
return {"success": False, "error": str(e)}
```

**Tools using this format:**
- `generate_endpoint` → returns `{success, code, language, metadata, errors}`
- `generate_component` → returns `{success, code, language, metadata, errors}`
- `generate_model` → returns `{success, code, language, metadata, errors}`
- `refactor_code` → returns `{success, refactored_code, changes}`
- `validate_code` → returns `{security_violations, syntax_valid, syntax_error, passed}`
- `write_memory` → returns `{success, file, timestamp}`
- `search_memory` → returns `{query, results, total_matches}`
- `read_conversation` → returns `{recent_conversations, memory_md, session_id}`

---

### 1.3 Economics Tools Layer

**Location:** `backend/app/agent/economics_tools.py`

**Format Pattern:** Mixed - some tools return dicts, others return raw data

```python
# Pattern A: Success wrapper
return {
    "success": True,
    "item": item,
}

# Pattern B: Flat data (NO success key)
return {"city": city, **self._cities[city]}

# Pattern C: Error with context
return {
    "success": False,
    "error": f"Missing inputs: {missing}",
    "required_inputs": formula["inputs"],
}

# Pattern D: Clarification response (inconsistent)
return {
    "requires_clarification": True,
    "suggestions": [...],
    "example_queries": [...]
}
```

**Inconsistency Alert:**
- `get_city()` returns `{"city": ..., ...}` without `success` key
- `search_items()` returns `{"success": True, ...}`
- Some errors include `available_regions`, others don't

---

### 1.4 Coding Tools Layer

**Location:** `backend/app/agent/coding_tools.py`

**Format Pattern:** Nested metadata structures

```python
return {
    "success": True,
    "code": code,
    "language": "python",
    "metadata": {
        "lines": len(code.split('\n')),
        "has_pydantic": "BaseModel" in code,
        "endpoints": [...]
    },
    "errors": []
}
```

**Issue:** `errors` field is always a list (even when empty), but some consumers check `if result.get("errors")` which fails for empty lists.

---

### 1.5 Code Enhancement Layer

**Location:** `backend/app/agent/code_enhancement.py`

**Format Pattern:** Analysis results with nested structures

```python
return {
    "file": file_path,
    "issues": [self._issue_to_dict(i) for i in issues],
    "issue_count_by_severity": {"critical": 0, "warning": 0, "info": 0},
    "enhancement_plans": [self._plan_to_dict(p) for p in plans],
    "metrics": {...}
}
```

**Inconsistency:** No `success` key - assumes success unless `error` key present.

---

### 1.6 Web Search Layer

**Location:** `backend/app/agent/web_search.py`

**Format Pattern:** Dataclass-based with explicit success/error

```python
@dataclass
class WebSearchResponse:
    query: str
    results: List[WebSearchResult]
    total_results: int
    search_time_ms: float
    success: bool
    error: Optional[str] = None
```

**Plus separate formatter:** `format_for_agent()` returns Markdown string

---

### 1.7 API Endpoints Layer

**Location:** `backend/app/agent/endpoints.py`

**Format Pattern:** Pydantic models with standardized structure

```python
class AgentTaskResponse(BaseModel):
    success: bool
    action: str
    layer: str
    data: Dict[str, Any]
    message: str
    timestamp: str
```

**Consistency Note:** This is the most consistent layer - all responses follow Pydantic models.

---

### 1.8 Planner Layer

**Location:** `backend/app/agent/planner.py`

**Format Pattern:** Dataclass with `to_dict()` method

```python
@dataclass
class PlanStep:
    id: str
    description: str
    tool: str
    params: Dict[str, Any]
    status: StepStatus
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {...}
```

---

### 1.9 Scheduler Layer

**Location:** `backend/app/agent/scheduler.py`

**Format Pattern:** Similar to planner - dataclass with `to_dict()`

```python
def to_dict(self) -> Dict:
    return {
        "id": self.id,
        "name": self.name,
        "status": self.status.value,
        "next_run": self.next_run,
        ...
    }
```

---

### 1.10 WebSocket Layer

**Location:** `backend/app/agent/websocket.py`

**Format Pattern:** Message type envelopes

```python
{
    "type": "task_completed",  # or task_started, task_failed, error
    "success": result.success,
    "action": result.action.value,
    "layer": result.layer.value,
    "data": result.data,
    "message": result.message,
    "timestamp": result.timestamp
}
```

---

## 2. Inconsistencies Found

### 2.1 Critical Inconsistencies (Fix Immediately)

#### Issue 1: Success Key Inconsistency
**Severity:** HIGH

Some tools return `{"success": True, ...}`, others return flat data without success key.

| Tool | Has `success` key? |
|------|-------------------|
| `search_items` | ✅ Yes |
| `get_item` | ✅ Yes |
| `get_city` | ❌ No - returns flat dict |
| `calculate_formula` | ✅ Yes |
| `get_categories` | ✅ Yes |
| `search_memory` | ❌ No - returns `{query, results, total_matches}` |
| `read_conversation` | ❌ No - returns `{recent_conversations, ...}` |

**Impact:** Consumers cannot reliably check `if result.get("success")`.

---

#### Issue 2: Error Format Inconsistency
**Severity:** HIGH

Three different error patterns exist:

```python
# Pattern A: Simple error string
return {"success": False, "error": "Item not found"}

# Pattern B: Error with context
return {
    "success": False,
    "error": f"City '{city}' not found",
    "available_regions": ["US", "Middle East", "Europe"]
}

# Pattern C: Error with suggestions
return {
    "success": False,
    "error": "Building type not found",
    "suggestions": [...],
    "example_queries": [...]
}
```

**Impact:** Error handlers must check for multiple field combinations.

---

#### Issue 3: Result Key Naming
**Severity:** MEDIUM

Different tools use different keys for similar data:

| Concept | Keys Used |
|---------|-----------|
| Query results | `results`, `items`, `matches`, `data` |
| Total count | `total`, `total_matches`, `count`, `total_results` |
| Error message | `error`, `message`, `detail` |
| Timestamp | `timestamp`, `created_at`, `completed_at` |

---

#### Issue 4: Formatting Layer Coupling
**Severity:** MEDIUM

Response formatting happens at **two different layers**:

1. **Tool Layer** (`economics_tools.py`): Returns raw dicts
2. **Formatter Layer** (`enhanced_core.py`): Converts to Markdown

This creates a tight coupling where tool changes require formatter updates.

---

#### Issue 5: Empty Result Handling
**Severity:** MEDIUM

Inconsistent handling of empty results:

```python
# Pattern A: Empty list with count=0
return {"success": True, "results": [], "total": 0}

# Pattern B: Helpful message (formatted in tool layer)
return {"success": False, "error": "No items found. Try..."}

# Pattern C: Success with empty list, formatted in formatter layer
# Tool returns {"results": []}
# Formatter converts to "I didn't find any..."
```

---

### 2.2 Medium Inconsistencies

#### Issue 6: Currency Formatting
**Severity:** MEDIUM

- `_format_currency()` in `enhanced_core.py` uses `"$"` default
- Economics tools store currency as float without currency code
- No internationalization support (always USD)

#### Issue 7: Number Formatting
**Severity:** LOW

- `_format_number()` uses `:,` for thousands separator
- Some tools use `round()`, others use `f"{value:.2f}"`
- No locale-aware formatting

#### Issue 8: Timestamp Formats
**Severity:** LOW

- ISO 8601: `datetime.now().isoformat()` (most common)
- Unix timestamp: `time.time()` (web search)
- Custom: Not used, but risk of inconsistency

---

## 3. Recommendations for Standardization

### 3.1 Adopt a Unified Response Schema

Create a single `AgentResponse` class used by ALL tools:

```python
from typing import Generic, TypeVar, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"  # Some data available, some failed
    CLARIFICATION = "clarification"  # Need user input

@dataclass
class AgentResponse:
    """Standardized response for all agent tools."""
    
    # Required fields
    status: ResponseStatus
    message: str  # Human-readable summary
    
    # Data fields (at least one should be populated)
    data: Optional[Dict[str, Any]] = None  # Structured data
    formatted_output: Optional[str] = None  # Pre-formatted for display
    
    # Error fields (populated when status != SUCCESS)
    error_code: Optional[str] = None  # Machine-readable error code
    error_details: Optional[Dict[str, Any]] = None  # Contextual error info
    suggestions: Optional[list] = None  # Helpful alternatives
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None  # Timing, source, etc.
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "formatted_output": self.formatted_output,
            "error_code": self.error_code,
            "error_details": self.error_details,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

# Factory methods for common patterns
class ResponseFactory:
    @staticmethod
    def success(message: str, data: Dict = None, formatted: str = None) -> AgentResponse:
        return AgentResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            formatted_output=formatted
        )
    
    @staticmethod
    def error(message: str, code: str = None, details: Dict = None, suggestions: list = None) -> AgentResponse:
        return AgentResponse(
            status=ResponseStatus.ERROR,
            message=message,
            error_code=code,
            error_details=details,
            suggestions=suggestions
        )
    
    @staticmethod
    def clarification(message: str, options: list, examples: list = None) -> AgentResponse:
        return AgentResponse(
            status=ResponseStatus.CLARIFICATION,
            message=message,
            error_details={"options": options, "examples": examples or []}
        )
```

### 3.2 Implement a Response Formatter Registry

Replace the `_format_result_message()` dispatcher with a registry pattern:

```python
class ResponseFormatterRegistry:
    """Registry for response formatters by tool type."""
    
    _formatters: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, tool_name: str):
        """Decorator to register a formatter."""
        def decorator(func: Callable):
            cls._formatters[tool_name] = func
            return func
        return decorator
    
    @classmethod
    def format(cls, tool_name: str, response: AgentResponse) -> str:
        """Format a response for display."""
        formatter = cls._formatters.get(tool_name)
        if formatter:
            return formatter(response)
        return cls._default_format(response)
    
    @classmethod
    def _default_format(cls, response: AgentResponse) -> str:
        """Default formatter for unregistered tools."""
        if not response.success:
            return f"⚠️ {response.message}"
        return response.formatted_output or response.message

# Usage:
@ResponseFormatterRegistry.register("calculate_cost")
def format_cost_response(response: AgentResponse) -> str:
    data = response.data or {}
    return f"💰 Total: ${data.get('total', 0):,.2f}"
```

### 3.3 Create Formatting Utilities Module

Extract common formatting into a shared utilities module:

```python
# backend/app/agent/formatting_utils.py

from typing import Union, Optional
from decimal import Decimal, ROUND_HALF_UP

class Formatters:
    """Standardized formatting utilities."""
    
    @staticmethod
    def currency(amount: Union[float, Decimal], 
                 currency_code: str = "USD",
                 symbol: str = "$",
                 decimals: int = 2) -> str:
        """Format amount as currency."""
        if amount is None:
            amount = 0
        d = Decimal(str(amount)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return f"{symbol}{d:,.{decimals}f}"
    
    @staticmethod
    def number(value: Union[int, float], 
               decimals: int = 0,
               unit: str = None) -> str:
        """Format number with optional unit."""
        if value is None:
            value = 0
        if decimals == 0:
            formatted = f"{int(value):,}"
        else:
            formatted = f"{value:,.{decimals}f}"
        return f"{formatted} {unit}" if unit else formatted
    
    @staticmethod
    def percentage(value: float, decimals: int = 1) -> str:
        """Format as percentage."""
        return f"{value:,.{decimals}f}%"
    
    @staticmethod
    def list(items: list, 
             max_items: int = 10,
             template: str = "{i}. {item}") -> str:
        """Format list with truncation."""
        lines = []
        for i, item in enumerate(items[:max_items], 1):
            lines.append(template.format(i=i, item=item))
        if len(items) > max_items:
            lines.append(f"...and {len(items) - max_items} more")
        return "\n".join(lines)
    
    @staticmethod
    def markdown_section(title: str, 
                        content: str,
                        level: int = 2) -> str:
        """Format markdown section."""
        prefix = "#" * level
        return f"{prefix} {title}\n\n{content}"
```

### 3.4 Standardize Error Responses

Create error code taxonomy:

```python
class ErrorCode(Enum):
    # Input errors (4xx style)
    MISSING_PARAMETER = "missing_parameter"
    INVALID_PARAMETER = "invalid_parameter"
    RESOURCE_NOT_FOUND = "resource_not_found"
    AMBIGUOUS_INPUT = "ambiguous_input"
    
    # System errors (5xx style)
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"
    
    # Domain errors
    CALCULATION_ERROR = "calculation_error"
    VALIDATION_FAILED = "validation_failed"
    INSUFFICIENT_DATA = "insufficient_data"

# Standard error builder
def error_response(
    code: ErrorCode,
    message: str,
    parameter: str = None,
    suggestions: list = None
) -> AgentResponse:
    return ResponseFactory.error(
        message=message,
        code=code.value,
        details={"parameter": parameter} if parameter else None,
        suggestions=suggestions
    )
```

---

## 4. Priority Fixes

### Priority 1: Critical (Fix This Week)

1. **Add `success` key to all tool responses**
   - Files: `economics_tools.py`, `core.py`
   - Risk: Breaking existing consumers
   - Mitigation: Keep backward compatibility for 1 release

2. **Standardize error format**
   - Create `ErrorResponse` class
   - Update all `except` blocks
   - Add error codes

3. **Fix currency formatting bugs**
   - `_format_currency()` handles `None` incorrectly
   - Returns "$0.00" instead of raising error or returning "N/A"

### Priority 2: High (Fix This Sprint)

4. **Extract formatting utilities**
   - Create `formatting_utils.py`
   - Replace inline formatting in all `_format_*` methods
   - Add unit tests

5. **Implement response registry**
   - Replace `_format_result_message()` if-elif chain
   - Register all formatters explicitly
   - Add default formatter fallback

6. **Standardize timestamp formats**
   - Use ISO 8601 everywhere
   - Add timezone awareness (UTC)

### Priority 3: Medium (Next Sprint)

7. **Add type hints to all response functions**
   - Use `AgentResponse` return type
   - Enable mypy strict mode

8. **Create response schemas for API**
   - Convert all endpoint responses to Pydantic models
   - Add OpenAPI documentation

9. **Add response validation tests**
   - Test all tools return valid responses
   - Test formatter handles all response types

### Priority 4: Low (Backlog)

10. **Internationalization support**
    - Currency formatting by locale
    - Number formatting by locale
    - Message translations

11. **Response caching layer**
    - Cache formatted responses
    - Invalidate on data change

---

## 5. Migration Path

### Phase 1: Backward-Compatible Wrapper (Week 1)

```python
def wrap_legacy_response(result: Dict, tool_name: str) -> AgentResponse:
    """Convert legacy responses to new format."""
    if isinstance(result, AgentResponse):
        return result
    
    # Handle old-style responses
    if "success" in result:
        if result["success"]:
            return ResponseFactory.success(
                message=result.get("message", f"{tool_name} completed"),
                data=result
            )
        else:
            return ResponseFactory.error(
                message=result.get("error", "Unknown error"),
                details=result
            )
    
    # Handle responses without success key (assume success)
    return ResponseFactory.success(
        message=f"{tool_name} completed",
        data=result
    )
```

### Phase 2: Tool Updates (Weeks 2-3)

Update each tool to return `AgentResponse`:

```python
# Before
def search_items(query: str) -> Dict:
    results = db.search(query)
    return {"success": True, "results": results, "total": len(results)}

# After
def search_items(query: str) -> AgentResponse:
    results = db.search(query)
    return ResponseFactory.success(
        message=f"Found {len(results)} items",
        data={"results": results, "total": len(results)},
        formatted=format_item_list(results)
    )
```

### Phase 3: Formatter Updates (Week 4)

Update formatters to use registry:

```python
@ResponseFormatterRegistry.register("search_items")
def format_search_response(response: AgentResponse) -> str:
    data = response.data or {}
    results = data.get("results", [])
    return Formatters.list(results, template="{i}. **{item['name']}**")
```

### Phase 4: Cleanup (Week 5)

- Remove backward compatibility wrapper
- Delete deprecated formatters
- Update documentation

---

## 6. Testing Strategy

### 6.1 Unit Tests for Formatters

```python
def test_format_currency():
    assert Formatters.currency(1234.5) == "$1,234.50"
    assert Formatters.currency(None) == "$0.00"
    assert Formatters.currency(1234.5, "EUR", "€") == "€1,234.50"

def test_error_response_structure():
    response = error_response(
        ErrorCode.RESOURCE_NOT_FOUND,
        "Item not found",
        suggestions=["Try a different ID"]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.error_code == "resource_not_found"
    assert len(response.suggestions) == 1
```

### 6.2 Integration Tests

```python
def test_end_to_end_cost_calculation():
    result = agent.tools["calculate_cost"](item_id="123", quantity=100)
    
    # Verify response structure
    assert isinstance(result, AgentResponse)
    assert result.success
    assert "formatted_output" in result.to_dict()
    
    # Verify formatter works
    formatted = ResponseFormatterRegistry.format("calculate_cost", result)
    assert "$" in formatted
    assert "Total" in formatted
```

### 6.3 Regression Tests

Create test fixtures with all current response formats and verify they still work after migration.

---

## 7. Appendix: Response Format Comparison Matrix

| Tool/File | success key | error format | data key | timestamp | formatted output |
|-----------|-------------|--------------|----------|-----------|------------------|
| economics_tools.py | Sometimes | String or dict | Various | No | No |
| core.py | Sometimes | String | Various | Yes | No |
| coding_tools.py | Yes | List | code, metadata | No | No |
| code_enhancement.py | No | error key | Nested | No | No |
| web_search.py | Yes (dataclass) | error field | results | Yes | format_for_agent() |
| endpoints.py | Yes (Pydantic) | HTTP exception | data | Yes | N/A |
| planner.py | N/A (status enum) | error field | to_dict() | Yes | No |
| scheduler.py | N/A (status enum) | error field | to_dict() | Yes | No |
| websocket.py | Yes | error field | data | Yes | N/A |
| enhanced_core.py | N/A (formatters) | N/A | N/A | Yes | _format_* methods |

---

## 8. Conclusion

The Cerebrum agent system has grown organically, leading to inconsistent response formats across its 14 layers. While functional, this inconsistency creates:

- **Technical debt** when adding new features
- **User experience issues** with varying output styles
- **Integration challenges** for API consumers
- **Maintenance burden** for developers

**Recommended immediate actions:**
1. Implement `AgentResponse` standard class
2. Add backward-compatible wrapper
3. Create formatting utilities module
4. Begin phased migration

**Estimated effort:** 2-3 developer weeks for complete migration

**Risk level:** Low (with backward compatibility)

**Impact:** High (improved maintainability, consistent UX)

---

*Report generated by Response Formatting Audit - Cerebrum Agent System*
