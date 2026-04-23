"""
Unit tests for agent.py placeholder replacements.

Tests cover: memory_search, _handle_reasoning_request,
_handle_workflow_request, _call_llm_for_response.
All LLM / DeepSeek calls are mocked so tests run offline.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.endpoints.agent import (
    memory_search,
    _handle_reasoning_request,
    _handle_workflow_request,
    _call_llm_for_response,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.llm.models import LLMMessage, LLMChoice, LLMResponse, Role


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_llm_response(text: str) -> LLMResponse:
    """Build a minimal LLMResponse with a single assistant choice."""
    return LLMResponse(
        id="test",
        model="deepseek-chat",
        provider="deepseek",
        choices=[
            LLMChoice(
                index=0,
                message=LLMMessage(role=Role.ASSISTANT, content=text),
                finish_reason="stop",
            )
        ],
    )


# ─── memory_search ────────────────────────────────────────────────────────────

class TestMemorySearch:
    """Tests for the /memory/search endpoint (formula-library keyword search)."""

    @pytest.mark.asyncio
    async def test_returns_memory_search_response(self):
        req = MemorySearchRequest(query="concrete", limit=5)
        result = await memory_search(req)
        assert isinstance(result, MemorySearchResponse)
        assert isinstance(result.results, list)
        assert isinstance(result.total_found, int)

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        req = MemorySearchRequest(query="steel", limit=2)
        result = await memory_search(req)
        assert len(result.results) <= 2

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self):
        req = MemorySearchRequest(query="load", limit=10)
        result = await memory_search(req)
        for item in result.results:
            assert "id" in item
            assert "name" in item
            assert "domain" in item
            assert "type" in item
            assert item["type"] == "formula"

    @pytest.mark.asyncio
    async def test_empty_query_returns_response(self):
        """Empty / no-match query should return empty list, not raise."""
        req = MemorySearchRequest(query="xyzzy_no_match_12345", limit=5)
        result = await memory_search(req)
        assert result.total_found == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_score(self):
        """Higher-relevance hits should come first."""
        req = MemorySearchRequest(query="concrete", limit=20)
        result = await memory_search(req)
        scores = [r["score"] for r in result.results]
        assert scores == sorted(scores, reverse=True)


# ─── _handle_reasoning_request ───────────────────────────────────────────────

class TestHandleReasoningRequest:
    """Tests for _handle_reasoning_request."""

    @pytest.mark.asyncio
    async def test_variance_analysis_with_numeric_context(self):
        """Should use HeavyReasoningEngine when boq_value and drawing_value present."""
        ctx = {"boq_value": 100.0, "drawing_value": 115.0, "item_name": "concrete_volume"}
        result = await _handle_reasoning_request("variance_analysis", "check variance", ctx)
        assert result["action"] == "variance_analysis"
        assert "variance" in result
        assert abs(result["variance"] - 15.0) < 0.01
        assert result["variance_percent"] == pytest.approx(15.0, abs=0.1)
        assert result["is_significant"] is True
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_variance_analysis_within_tolerance(self):
        ctx = {"boq_value": 100.0, "drawing_value": 102.0}
        result = await _handle_reasoning_request("variance_analysis", "", ctx)
        assert result["is_significant"] is False

    @pytest.mark.asyncio
    async def test_check_compliance_with_cost_data(self):
        ctx = {"estimated_cost": 500_000.0, "actual_cost": 600_000.0}
        result = await _handle_reasoning_request("check_compliance", "", ctx)
        assert result["action"] == "check_compliance"
        assert "status" in result
        assert result["is_overrun"] is True
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_analyze_document_with_boq_data(self):
        ctx = {
            "boq_data": {"quantities": [{"id": "q1", "value": 100}]},
            "drawing_data": {"quantities": [{"id": "q1", "value": 120}]},
            "spec_data": {"sections": []},
        }
        result = await _handle_reasoning_request("analyze_document", "", ctx)
        assert result["action"] == "analyze_document"
        assert "risk_level" in result
        assert "overall_status" in result

    @pytest.mark.asyncio
    async def test_llm_fallback_when_no_numeric_context(self):
        """Without numeric context, should fall back to LLM."""
        mock_response = _make_llm_response("Analysis: no structural issues found.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _handle_reasoning_request("analyze_document", "check doc", {})
        assert result["action"] == "analyze_document"
        assert "Analysis" in result["analysis"]
        assert result["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_unknown_action_falls_back_to_llm(self):
        mock_response = _make_llm_response("General analysis result.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _handle_reasoning_request("unknown_action", "test", {})
        assert result["action"] == "unknown_action"
        assert result["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_dict(self):
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ):
            result = await _handle_reasoning_request("analyze_document", "test", {})
        assert result["confidence"] == 0.0
        assert "failed" in result["analysis"].lower()


# ─── _handle_workflow_request ─────────────────────────────────────────────────

class TestHandleWorkflowRequest:
    """Tests for _handle_workflow_request."""

    @pytest.mark.asyncio
    async def test_full_qto_workflow(self):
        ctx = {"quantities": [{"id": "q1"}, {"id": "q2"}, {"id": "q3"}]}
        result = await _handle_workflow_request("full_qto", "run QTO", ctx)
        assert result["workflow"] == "full_qto"
        assert result["steps_completed"] == result["total_steps"] == 4
        assert result["result"]["item_count"] == 3
        assert len(result["steps"]) == 4

    @pytest.mark.asyncio
    async def test_change_order_workflow_with_cost_data(self):
        ctx = {"estimated_cost": 100_000.0, "actual_cost": 120_000.0}
        result = await _handle_workflow_request("change_order_workflow", "", ctx)
        assert result["workflow"] == "change_order_workflow"
        assert result["steps_completed"] == 4
        assert "status" in result["result"]

    @pytest.mark.asyncio
    async def test_risk_assessment_calls_llm(self):
        mock_response = _make_llm_response("Risk: medium. Mitigation: review specs.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _handle_workflow_request("risk_assessment", "assess risk", {})
        assert result["workflow"] == "risk_assessment"
        assert "Risk" in result["summary"]
        assert result["steps_completed"] == 4

    @pytest.mark.asyncio
    async def test_compliance_check_calls_llm(self):
        mock_response = _make_llm_response("Compliance: all checks passed.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _handle_workflow_request("compliance_check", "check code", {})
        assert result["workflow"] == "compliance_check"
        assert result["steps_completed"] == 4

    @pytest.mark.asyncio
    async def test_generic_workflow_calls_llm(self):
        mock_response = _make_llm_response("Generic workflow completed.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _handle_workflow_request("custom_workflow", "do something", {})
        assert result["workflow"] == "custom_workflow"
        assert "Generic" in result["summary"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_dict(self):
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network error"),
        ):
            result = await _handle_workflow_request("risk_assessment", "test", {})
        assert result["steps_completed"] == 0
        assert "failed" in result["summary"].lower()


# ─── _call_llm_for_response ───────────────────────────────────────────────────

class TestCallLlmForResponse:
    """Tests for _call_llm_for_response."""

    @pytest.mark.asyncio
    async def test_returns_llm_content(self):
        mock_response = _make_llm_response("Here is the construction advice.")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await _call_llm_for_response("What is RSMeans?", "general_query")
        assert result == "Here is the construction advice."

    @pytest.mark.asyncio
    async def test_passes_action_in_system_prompt(self):
        """Check that the action label reaches the LLM call."""
        mock_response = _make_llm_response("ok")
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_chat:
            await _call_llm_for_response("hello", "calculate_cost")
        call_kwargs = mock_chat.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        system_msg = next((m for m in messages if m.role == Role.SYSTEM), None)
        assert system_msg is not None
        assert "calculate_cost" in system_msg.content

    @pytest.mark.asyncio
    async def test_graceful_on_llm_error(self):
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            side_effect=RuntimeError("timeout"),
        ):
            result = await _call_llm_for_response("question", "query")
        assert "error" in result.lower() or "encountered" in result.lower()

    @pytest.mark.asyncio
    async def test_handles_empty_choices(self):
        """LLM returns no choices → fallback message."""
        empty_response = LLMResponse(id="x", model="m", provider="p", choices=[])
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=empty_response,
        ):
            result = await _call_llm_for_response("test", "act")
        assert isinstance(result, str)
        assert len(result) > 0
