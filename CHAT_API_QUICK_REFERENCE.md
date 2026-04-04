# Chat API Quick Reference

## New Endpoints

### Chat Completions (Enhanced)
```http
POST /api/v1/chat/completions
```

**Features**:
- Automatic web search detection
- Code execution for Python blocks
- Long context support (8000 tokens)

**Example**:
```json
{
  "model": "cerebrum-default",
  "messages": [{"role": "user", "content": "Hello!"}],
  "temperature": 0.7,
  "max_tokens": 2048,
  "enable_web_search": true,
  "enable_code_execution": true
}
```

---

### Execute Code
```http
POST /api/v1/chat/execute-code
```

**Execute Python code safely**.

**Request**:
```json
{
  "code": "print('Hello World')",
  "context": {"x": 10},
  "timeout": 30
}
```

**Response**:
```json
{
  "success": true,
  "output": "Hello World\n",
  "execution_time_ms": 150,
  "figures": [],
  "analysis": {...}
}
```

---

### Analyze Image (Upload)
```http
POST /api/v1/chat/analyze-image
```

**Analyze uploaded image file**.

**Form Data**:
- `file`: Image file (jpg, png, gif, webp, tiff)
- `prompt`: Optional custom prompt
- `analysis_type`: `general`, `ocr`, `document`, `construction`, `chart`
- `extract_text`: Boolean

---

### Analyze Image (Base64)
```http
POST /api/v1/chat/analyze-image/base64
```

**Analyze base64-encoded image**.

**Request**:
```json
{
  "image_data": "data:image/jpeg;base64,/9j/4AAQ...",
  "prompt": "Extract all text",
  "analysis_type": "ocr"
}
```

---

### Web Search
```http
POST /api/v1/chat/web-search
```

**Explicit web search**.

**Request**:
```json
{
  "query": "construction technology trends",
  "count": 5
}
```

**Response**:
```json
{
  "success": true,
  "query": "construction technology trends",
  "results": [
    {
      "title": "...",
      "url": "...",
      "description": "...",
      "source": "..."
    }
  ],
  "total_results": 5,
  "search_time_ms": 450
}
```

---

### Streaming Chat
```http
POST /api/v1/chat/completions/stream
```

**Server-Sent Events streaming**.

Same request format as `/completions` but returns SSE stream.

---

### List Models
```http
GET /api/v1/chat/models
```

**List available models with capabilities**.

---

### Get Capabilities
```http
GET /api/v1/chat/capabilities
```

**Get available chat features**.

---

### Health Check
```http
GET /api/v1/chat/health
```

**Check chat service health**.

---

## Document Analysis Endpoints

### Analyze Document Text
```http
POST /api/v1/documents/analyze
```

**AI-powered document analysis**.

**Request**:
```json
{
  "text": "Document content...",
  "document_type": "report",
  "analysis_depth": "standard"
}
```

**Response**:
```json
{
  "success": true,
  "summary": {
    "overview": "...",
    "key_points": ["..."],
    "topics": ["..."],
    "word_count": 500,
    "reading_time_minutes": 3
  },
  "entities": [...],
  "sentiment": {"sentiment": "positive", "score": 0.7},
  "action_items": [...]
}
```

---

### Analyze Document File
```http
POST /api/v1/documents/analyze/file
```

**Upload and analyze document**.

**Form Data**:
- `file`: Document file (pdf, docx, txt, png, jpg)
- `analysis_depth`: `basic`, `standard`, `deep`
- `extract_text`: Boolean

---

### Summarize Document
```http
POST /api/v1/documents/summarize
```

**Quick document summarization**.

**Form Data**:
- `text`: Document text
- `max_sentences`: Number of sentences (default: 3)

---

### Extract Keywords
```http
POST /api/v1/documents/extract-keywords
```

**Extract key topics and keywords**.

**Form Data**:
- `text`: Document text
- `top_n`: Number of keywords (default: 10)

---

## Code Analysis Endpoint

### Analyze Code
```http
POST /api/v1/chat/analyze-code
```

**Analyze code without executing**.

**Form Data**:
- `code`: Python code to analyze

**Response**:
```json
{
  "safe": true,
  "violations": [],
  "line_count": 15,
  "estimated_complexity": 3,
  "detected_patterns": {"data_analysis": true},
  "suggestions": ["Consider adding visualizations"]
}
```

---

## Configuration

### Environment Variables

```bash
# Web Search
BRAVE_API_KEY=your_brave_api_key
WEB_SEARCH_ENABLED=true

# OpenAI (for Vision & Document Analysis)
OPENAI_API_KEY=your_openai_api_key
```

---

## Example cURL Commands

### Chat with Web Search
```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "messages": [{"role": "user", "content": "Latest construction tech?"}],
    "enable_web_search": true
  }'
```

### Execute Python Code
```bash
curl -X POST http://localhost:8000/api/v1/chat/execute-code \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "code": "import numpy as np\nprint(np.random.rand(5))"
  }'
```

### Analyze Image
```bash
curl -X POST http://localhost:8000/api/v1/chat/analyze-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@blueprint.jpg" \
  -F "analysis_type=construction"
```

### Analyze Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "text": "Your document text here...",
    "analysis_depth": "deep"
  }'
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid token |
| 403 | Forbidden - Not authorized |
| 413 | Payload Too Large - File too big |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Feature not configured |

---

## Security Notes

- Code execution runs in isolated process with resource limits
- Only search queries are sent to external APIs
- Image files are validated before processing
- All operations are logged for audit
