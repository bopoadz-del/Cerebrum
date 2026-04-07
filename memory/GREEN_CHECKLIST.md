# Cerebrum Green Checklist

> Production readiness checklist. Run all curls after each deploy.

---

## [ ] Health Endpoint

```bash
# Basic health check
curl -s http://localhost:8000/health | jq .

# Expected response:
# { "status": "healthy", "timestamp": "..." }
```

---

## [ ] Agent Status (14 Layers)

```bash
# Check all 14 agent layers are running
curl -s http://localhost:8000/api/agents/status | jq '.layers | length'

# Verify each layer responds
curl -s http://localhost:8000/api/agents/layers/1/status
curl -s http://localhost:8000/api/agents/layers/2/status
# ... repeat for layers 3-14
```

---

## [ ] Layer Navigation

```bash
# Test layer switching/navigation
curl -s -X POST http://localhost:8000/api/agents/navigate \
  -H "Content-Type: application/json" \
  -d '{"from_layer": 1, "to_layer": 2}' | jq .

# Verify navigation history
curl -s http://localhost:8000/api/agents/navigation/history | jq .
```

---

## [ ] Chat Routing

```bash
# Test chat message routing
curl -s -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "layer": 1}' | jq .

# Check routing logs
curl -s http://localhost:8000/api/chat/routing/status | jq .
```

---

## [ ] File Uploads

```bash
# Test file upload endpoint (small test file)
curl -s -X POST http://localhost:8000/api/files/upload \
  -F "file=@/tmp/test-file.txt" | jq .

# Verify upload status
curl -s http://localhost:8000/api/files/status | jq .
```

---

## [ ] WebSocket

```bash
# Test WebSocket connection (using websocat or similar)
websocat ws://localhost:8000/ws -n1 <<< '{"ping": true}'

# Alternative with curl for HTTP upgrade check
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
  http://localhost:8000/ws
```

---

## [ ] Voice Health

```bash
# Check voice service health
curl -s http://localhost:8000/api/voice/health | jq .

# Test transcription endpoint (if available)
curl -s -X POST http://localhost:8000/api/voice/transcribe \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "test"}' | jq .

# Verify voice WebSocket
curl -s http://localhost:8000/api/voice/ws/status | jq .
```

---

## All-in-One Test Script

```bash
#!/bin/bash
# green-check.sh - Run all checks and output summary

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0

echo "=== Cerebrum Green Checklist ==="
echo "Started: $(date -Iseconds)"
echo ""

check() {
    local name=$1
    local cmd=$2
    echo -n "[ ] $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✓ PASS"
        ((PASS++))
    else
        echo "✗ FAIL"
        ((FAIL++))
    fi
}

# Run all checks
check "Health Endpoint" "curl -sf $BASE_URL/health"
check "Agent Status" "curl -sf $BASE_URL/api/agents/status"
check "Layer Navigation" "curl -sf $BASE_URL/api/agents/navigation/history"
check "Chat Routing" "curl -sf $BASE_URL/api/chat/routing/status"
check "File Uploads" "curl -sf $BASE_URL/api/files/status"
check "WebSocket" "curl -sf -N -H 'Connection: Upgrade' -H 'Upgrade: websocket' $BASE_URL/ws"
check "Voice Health" "curl -sf $BASE_URL/api/voice/health"

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo "Finished: $(date -Iseconds)"

exit $FAIL
```

---

*Run this checklist after every deploy. Update DEPLOYMENT_TRACKING.md with results.*
