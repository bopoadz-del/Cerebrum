# User-Friendly Error Handling Guide

## Overview

This document describes the standardized error handling system for Cerebrum, designed to provide clear, actionable error messages for non-technical users.

## Error Categories

Errors are categorized into the following types:

| Category | Description | User-Friendly Message |
|----------|-------------|----------------------|
| `NETWORK` | Connection issues | "Connection issue. Check your internet." |
| `DATABASE` | Database errors | "Service temporarily unavailable." |
| `AUTHENTICATION` | Login/auth errors | "You need to sign in to do that." |
| `AUTHORIZATION` | Permission errors | "You don't have permission to do that." |
| `VALIDATION` | Input validation errors | "That doesn't look right." |
| `NOT_FOUND` | Resource not found | "We couldn't find what you're looking for." |
| `RATE_LIMIT` | Too many requests | "You've made too many requests. Please slow down." |
| `TIMEOUT` | Request timeout | "The request took too long." |
| `SERVICE_UNAVAILABLE` | Server errors | "Something went wrong on our end." |
| `UNKNOWN` | Unclassified errors | "Something unexpected happened." |

## HTTP Status Code Mapping

| HTTP Code | User Message | Suggestion |
|-----------|-------------|------------|
| 400 | "We couldn't process your request." | "Please check your input and try again." |
| 401 | "You need to sign in to do that." | "Please sign in to your account." |
| 403 | "You don't have permission to do that." | "Contact your administrator." |
| 404 | "We couldn't find what you're looking for." | "Check the URL or search for it." |
| 429 | "You've made too many requests." | "Wait a moment and try again." |
| 500 | "Something went wrong on our end." | "Please try again in a few moments." |
| 502 | "We're experiencing temporary issues." | "Please try again shortly." |
| 503 | "Service temporarily unavailable." | "We're doing maintenance or experiencing high traffic." |
| 504 | "The request took too long." | "Please try again in a moment." |

## Error Response Format

All errors return a standardized JSON structure:

```json
{
  "success": false,
  "error": {
    "message": "Something went wrong on our end.",
    "suggestion": "We're working on fixing this. Please try again in a few moments.",
    "category": "service_unavailable",
    "retry_allowed": true,
    "actions": [
      {"label": "Try Again", "action": "retry"}
    ]
  }
}
```

## Action Buttons

Errors can include action buttons for user interaction:

| Button Type | Action | Example |
|-------------|--------|---------|
| `retry` | Retry the operation | `{"label": "Try Again", "action": "retry"}` |
| `navigate` | Navigate to a route | `{"label": "Go Home", "action": "navigate:/"}` |
| `signin` | Navigate to login | `{"label": "Sign In", "action": "navigate:/login"}` |

## Usage in Code

### Basic Usage

```python
from app.errors import format_error_response

try:
    result = some_operation()
except Exception as e:
    error_response = format_error_response(e, operation="processing your request")
    raise HTTPException(status_code=500, detail=error_response["error"])
```

### Using the Decorator

```python
from app.errors import handle_errors

@handle_errors(operation_name="creating project")
async def create_project(data: ProjectCreate):
    # Code that might raise exceptions
    return result
```

### Custom Error Mapping

```python
from app.errors import ERROR_MAPPINGS, ErrorCategory

# Add custom error mapping
ERROR_MAPPINGS["my_custom_error"] = {
    "category": ErrorCategory.VALIDATION,
    "user_message": "Your input was not valid.",
    "suggestion": "Please check the format and try again.",
    "retry_allowed": True,
}
```

## Guidelines for Writing User-Friendly Errors

1. **Be Clear**: Avoid technical jargon. Use simple language.
2. **Be Helpful**: Always provide a suggestion for what to do next.
3. **Be Concise**: Keep messages short and to the point.
4. **Be Actionable**: Include specific steps the user can take.
5. **Be Friendly**: Use a conversational tone. Avoid blame.

### Good Examples

✅ "We couldn't find that file. Please check the name and try again."

✅ "Connection issue. Check your internet and try again."

✅ "That already exists. Try a different name."

### Bad Examples

❌ "FileNotFoundError: [Errno 2] No such file or directory"

❌ "HTTP 500 Internal Server Error"

❌ "SQLIntegrityError: duplicate key value violates unique constraint"

## Testing Error Handling

To test error responses, you can use the debug mode:

```python
error_response = format_error_response(
    e,
    operation="test operation",
    context={"debug_mode": True}  # Includes technical details
)
```

In debug mode, the response will include:
- `technical_detail`: The original error message
- `error_type`: The exception class name

## Frontend Integration

The frontend should:

1. Display the `message` prominently
2. Show the `suggestion` as secondary text
3. Render action buttons if provided
4. Show a retry button if `retry_allowed` is true
5. Only show technical details in development mode

Example React component:

```jsx
function ErrorDisplay({ error }) {
  return (
    <div className="error-container">
      <h3>{error.message}</h3>
      <p>{error.suggestion}</p>
      {error.retry_allowed && (
        <button onClick={handleRetry}>Try Again</button>
      )}
      {error.actions?.map(action => (
        <button onClick={() => handleAction(action.action)}>
          {action.label}
        </button>
      ))}
    </div>
  );
}
```