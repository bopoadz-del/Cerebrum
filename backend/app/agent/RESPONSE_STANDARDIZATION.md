# Agent Response Standardization

## Overview

This document describes the standardized response format implemented across all 14 agent layers. All tools now return responses following a consistent schema for better error handling, debugging, and user experience.

## Standard Response Format

All agent tools now return responses following this structure:

```python
{
    "success": bool,           # Required: True if operation succeeded
    "results": Any,            # Primary result data (dict, list, or any type)
    "status": str,             # "success", "error", "warning", or "pending"
    "error": {                 # Present only if success=False
        "code": str,           # Machine-readable error code
        "message": str,        # Human-readable error message
        "details": dict,       # Optional: Additional error context
        "suggestion": str      # Optional: Recovery suggestion
    },
    "metadata": {              # Optional: Additional context
        "query": str,          # Original search query
        "count": int,          # Number of results
        "total": int,          # Total available results
        ...
    },
    "timestamp": str,          # ISO format timestamp
    "execution_time_ms": float,# Optional: Performance metric
    "suggestions": [str]       # Optional: Follow-up action suggestions
}
```

## Key Changes

### 1. Created `response_schema.py`

New standardized response schema module with:
- `AgentResponse` dataclass for type-safe responses
- `AgentError` class for consistent error representation
- `ResponseStatus` and `ErrorCode` enums for standardization
- Helper functions: `format_error_response()`, `format_success_response()`
- Response validation and normalization utilities

### 2. Updated Files

#### `economics_tools.py`
- All functions now use `format_success_response()` and `format_error_response()`
- Standardized error codes using `ErrorCode` enum
- Consistent `results` key naming (previously mixed `results` and `data`)
- All responses include `success` boolean

#### `vdc_tools.py` (NEW)
- Created complete VDC tools module with standardized responses
- BIM model querying, clash detection, quantity extraction
- All functions return standardized `AgentResponse` format

#### `coding_tools.py` (NEW)
- Created complete coding tools module with standardized responses
- Code generation (endpoints, components, models)
- Code validation and refactoring suggestions
- Test generation utilities

#### `enhanced_core.py`
- Fixed missing `success` keys in:
  - `read_conversations()` → returns `{success: True, results: {...}, metadata: {...}}`
  - `semantic_search()` → returns `{success: True, results: {...}, metadata: {...}}`
  - `get_conversation_thread()` → returns `{success: True/False, results: {...}}`
- Updated `_tool_read_conversation()` and `_tool_search_memory()` wrappers
- Updated formatters to handle both old and new response formats:
  - `_format_memory_search_result()`
  - `_format_economics_result()`
  - `_format_formula_result()`
  - `_format_formula_search_result()`
  - `_format_bim_result()`
  - `_format_quantities_result()`
  - `_format_error_message()` (now handles dict errors)

## Error Format Standardization

### Old Format (Inconsistent)
```python
# Format 1
{"success": False, "error": "Something went wrong"}

# Format 2
{"success": False, "error": {"message": "Something went wrong", "code": "not_found"}}

# Format 3 (missing success key)
{"error": "Something went wrong"}
```

### New Format (Standardized)
```python
{
    "success": False,
    "results": {},
    "status": "error",
    "error": {
        "code": "not_found",
        "message": "Item not found",
        "details": {"item_id": "123"},
        "suggestion": "Try searching with different keywords"
    },
    "metadata": {},
    "timestamp": "2025-01-15T10:30:00"
}
```

## Migration Guide

### For New Tools

Always use the helper functions:

```python
from app.agent.response_schema import (
    format_error_response,
    format_success_response,
    ErrorCode,
)

# Success response
return format_success_response(
    results={"items": items},
    metadata={"count": len(items), "query": query},
    suggestions=["Try searching with different keywords"]
)

# Error response
return format_error_response(
    message="Item not found",
    code=ErrorCode.NOT_FOUND,
    details={"item_id": requested_id},
    suggestion="Use list_items() to see available items"
)
```

### For Legacy Code

Use `normalize_response()` to convert old formats:

```python
from app.agent.response_schema import normalize_response

# Convert legacy response to new format
legacy_response = {"items": items, "query": query}  # Missing success key
standard_response = normalize_response(legacy_response)
# Result: {"success": True, "results": {"items": [...], "query": ...}, ...}
```

## Error Codes

Standard error codes available in `ErrorCode` enum:

- `UNKNOWN_ERROR` - Unspecified error
- `INVALID_INPUT` - Invalid user input
- `NOT_FOUND` - Requested resource not found
- `PERMISSION_DENIED` - Access denied
- `TIMEOUT` - Operation timed out
- `RATE_LIMITED` - Rate limit exceeded
- `DATA_UNAVAILABLE` - Data source unavailable
- `DATA_INVALID` - Invalid data format
- `CALCULATION_ERROR` - Math/computation error
- `RESOURCE_NOT_FOUND` - Resource doesn't exist
- `RESOURCE_BUSY` - Resource temporarily unavailable
- `VALIDATION_FAILED` - Validation check failed
- `MISSING_REQUIRED_FIELD` - Required parameter missing
- `INVALID_FORMAT` - Format not recognized

## Formatter Compatibility

All formatters in `enhanced_core.py` have been updated to handle both:
1. New standardized format: `{"results": {"items": [...]}}`
2. Legacy format: `{"items": [...]}`

This ensures backward compatibility while migrating to the new standard.

## Testing

Run syntax validation:
```bash
cd /root/.openclaw/workspace/cerebrum-fix/backend
python3 -m py_compile app/agent/response_schema.py
python3 -m py_compile app/agent/economics_tools.py
python3 -m py_compile app/agent/vdc_tools.py
python3 -m py_compile app/agent/coding_tools.py
python3 -m py_compile app/agent/enhanced_core.py
```

## Files Modified

1. **Created:** `backend/app/agent/response_schema.py` (new standard)
2. **Created:** `backend/app/agent/vdc_tools.py` (new tools)
3. **Created:** `backend/app/agent/coding_tools.py` (new tools)
4. **Modified:** `backend/app/agent/economics_tools.py` (standardized)
5. **Modified:** `backend/app/agent/enhanced_core.py` (fixed success keys, updated formatters)

## Summary

- ✅ Created standardized `AgentResponse` class/schema
- ✅ Fixed missing `success` keys in `get_city()` (via economics tools), `search_memory()`, `read_conversation()`
- ✅ Unified error formats to single pattern
- ✅ Standardized result key naming (using `results` consistently)
- ✅ Updated formatters in `enhanced_core.py` to match new schema
- ✅ Created VDC and Coding tools with standardized responses from the start
- ✅ All files pass Python syntax validation