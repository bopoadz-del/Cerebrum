#!/bin/bash
# Quick test script for Cerebrum deployment

set -e

BASE_URL="${1:-https://cerebrum-api.onrender.com}"

echo "=========================================="
echo "CEREBRUM DEPLOYMENT TEST"
echo "=========================================="
echo "Testing against: $BASE_URL"
echo ""

# Test 1: Health check
echo "[1/7] Health Check..."
response=$(curl -s "$BASE_URL/health/live" || echo "FAIL")
if [[ "$response" == *"healthy"* ]] || [[ "$response" == *"ok"* ]]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed: $response"
fi

# Test 2: API Docs
echo ""
echo "[2/7] API Docs..."
response=$(curl -s "$BASE_URL/docs" -o /dev/null -w "%{http_code}")
if [[ "$response" == "200" ]]; then
    echo "✅ API docs accessible"
else
    echo "⚠️ API docs returned HTTP $response"
fi

# Test 3: OpenAPI schema
echo ""
echo "[3/7] OpenAPI Schema..."
response=$(curl -s "$BASE_URL/openapi.json" -o /dev/null -w "%{http_code}")
if [[ "$response" == "200" ]]; then
    echo "✅ OpenAPI schema accessible"
else
    echo "⚠️ OpenAPI returned HTTP $response"
fi

# Test 4: Formula Executor endpoint
echo ""
echo "[4/7] Formula Executor..."
response=$(curl -s -X POST "$BASE_URL/api/v1/executor/execute" \
  -H "Content-Type: application/json" \
  -d '{"formula": {"expression": "10 * 5 * 0.3"}, "formula_type": "CONCRETE"}' 2>/dev/null || echo "FAIL")
if [[ "$response" != "FAIL" ]] && [[ "$response" != *"error"* ]]; then
    echo "✅ Formula executor responding"
else
    echo "⚠️ Formula executor: $response"
fi

# Test 5: Learning endpoint
echo ""
echo "[5/7] Learning Engine..."
response=$(curl -s "$BASE_URL/api/v1/learning/statistics" 2>/dev/null || echo "FAIL")
if [[ "$response" != "FAIL" ]] && [[ "$response" != *"error"* ]]; then
    echo "✅ Learning engine responding"
else
    echo "⚠️ Learning engine: $response"
fi

# Test 6: MLflow endpoint
echo ""
echo "[6/7] MLflow..."
response=$(curl -s "$BASE_URL/api/v1/ml/experiments" 2>/dev/null || echo "FAIL")
if [[ "$response" != "FAIL" ]] && [[ "$response" != *"error"* ]]; then
    echo "✅ MLflow responding"
else
    echo "⚠️ MLflow: $response"
fi

# Test 7: Recommendations
echo ""
echo "[7/7] Recommendations..."
response=$(curl -s "$BASE_URL/api/v1/recommendations/templates" 2>/dev/null || echo "FAIL")
if [[ "$response" != "FAIL" ]] && [[ "$response" != *"error"* ]]; then
    echo "✅ Recommendations responding"
else
    echo "⚠️ Recommendations: $response"
fi

echo ""
echo "=========================================="
echo "DEPLOYMENT TEST COMPLETE"
echo "=========================================="
echo ""
echo "URLs:"
echo "  Frontend: https://cerebrum-30d9c.web.app"
echo "  API: $BASE_URL"
echo "  Docs: $BASE_URL/docs"
