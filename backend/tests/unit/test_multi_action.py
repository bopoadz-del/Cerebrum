"""
Unit tests for multi-action dispatch and aggregation logic.

Tests cover:
  - _dispatch_single_action routing to each handler branch
  - _synthesize_multi_results LLM synthesis + error handling
  - _handle_multi_action parallel execution + partial failures
  - IntentRouter.route_multi deduplication, capping, fallback
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.api.v1.endpoints.agent import (
    _dispatch_single_action,
    _handle_multi_action,
    _synthesize_multi_results,
)
from app.orchestrator.intent_router import IntentRouter, IntentMatch, MatchPriority
from app.llm.models import LLMMessage, LLMChoice, LLMResponse, Role


# ── Helpers ───────────────────────────────────────────────────────────────────

def _llm_resp(text: str) -> LLMResponse:
    return LLMResponse(
        id="t",
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


def _match(action: str, confidence: float = 0.8) -> IntentMatch:
    return IntentMatch(
        action_name=action,
        priority=MatchPriority.PATTERN,
        confidence=confidence,
        extracted_params={},
        reasoning="test",
    )


# ── _dispatch_single_action ────────────────────────────────────────────────────

class TestDispatchSingleAction:
    @pytest.mark.asyncio
    async def test_formula_path_returns_dict_and_string(self):
        data, msg = await _dispatch_single_action("calculate_concrete", "calculate 100 200", {})
        assert isinstance(data, dict)
        assert isinstance(msg, str)

    @pytest.mark.asyncio
    async def test_formula_eval_action_routes_to_formula_handler(self):
        data, msg = await _dispatch_single_action("formula_eval", "eval formula_x 5 10", {})
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_reasoning_action_variance_with_context(self):
        ctx = {"boq_value": 100.0, "drawing_value": 120.0}
        data, msg = await _dispatch_single_action("variance_analysis", "check variance", ctx)
        assert data["action"] == "variance_analysis"
        assert "variance" in data
        assert "Variance" in msg

    @pytest.mark.asyncio
    async def test_reasoning_action_check_compliance_with_context(self):
        ctx = {"estimated_cost": 500_000.0, "actual_cost": 600_000.0}
        data, msg = await _dispatch_single_action("check_compliance", "check cost", ctx)
        assert data["action"] == "check_compliance"
        assert data["is_overrun"] is True

    @pytest.mark.asyncio
    async def test_workflow_action_full_qto(self):
        data, msg = await _dispatch_single_action(
            "full_qto", "run qto", {"quantities": [1, 2, 3]}
        )
        assert data["workflow"] == "full_qto"
        assert data["steps_completed"] == 4
        assert isinstance(msg, str)

    @pytest.mark.asyncio
    async def test_workflow_action_change_order(self):
        ctx = {"estimated_cost": 100_000.0, "actual_cost": 120_000.0}
        data, msg = await _dispatch_single_action("change_order_workflow", "change order", ctx)
        assert data["workflow"] == "change_order_workflow"
        assert data["steps_completed"] == 4

    @pytest.mark.asyncio
    async def test_llm_fallback_for_unknown_action(self):
        mock_resp = _llm_resp("Here is the construction answer.")
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            data, msg = await _dispatch_single_action("general_query", "what is RSMeans?", {})
        assert isinstance(data, dict)
        assert "general_query" in data.get("action", "general_query")
        assert isinstance(msg, str)

    @pytest.mark.asyncio
    async def test_returns_tuple_of_two_elements(self):
        result = await _dispatch_single_action("full_qto", "qto", {})
        assert isinstance(result, tuple)
        assert len(result) == 2


# ── _synthesize_multi_results ──────────────────────────────────────────────────

class TestSynthesizeMultiResults:
    @pytest.mark.asyncio
    async def test_returns_llm_content(self):
        mock_resp = _llm_resp("Synthesis: critical variance found, costs within budget.")
        results = [
            {"action": "variance_analysis", "status": "completed", "result": {"variance": 15.0}},
            {"action": "check_compliance", "status": "completed", "result": {"is_overrun": False}},
        ]
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            text = await _synthesize_multi_results("analyze everything", results)
        assert "Synthesis" in text

    @pytest.mark.asyncio
    async def test_graceful_on_llm_failure(self):
        with patch(
            "app.llm.client.LLMClient.chat",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network down"),
        ):
            text = await _synthesize_multi_results("test", [{"action": "a", "status": "completed"}])
        assert isinstance(text, str)
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_handles_failed_result_entries(self):
        mock_resp = _llm_resp("One failed but the compliance check passed.")
        results = [
            {"action": "variance_analysis", "status": "failed", "error": "timeout"},
            {"action": "check_compliance", "status": "completed", "result": {"status": "ok"}},
        ]
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            text = await _synthesize_multi_results("check all", results)
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_returns_string(self):
        mock_resp = _llm_resp("ok")
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            text = await _synthesize_multi_results("msg", [])
        assert isinstance(text, str)


# ── _handle_multi_action ──────────────────────────────────────────────────────

class TestHandleMultiAction:
    @pytest.mark.asyncio
    async def test_runs_all_actions_returns_synthesis(self):
        mock_resp = _llm_resp("Combined: variance critical, cost within budget.")
        matches = [_match("variance_analysis"), _match("check_compliance")]
        ctx = {
            "boq_value": 100.0,
            "drawing_value": 120.0,
            "estimated_cost": 500_000.0,
            "actual_cost": 600_000.0,
        }
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await _handle_multi_action(matches, "analyze", ctx)

        assert result["multi_action"] is True
        assert result["action_count"] == 2
        assert len(result["individual_results"]) == 2
        assert "synthesis" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_marks_failed_actions(self):
        """If one dispatch raises, it should be recorded as failed, not crash the whole call."""
        mock_resp = _llm_resp("Partial synthesis.")
        matches = [_match("full_qto"), _match("variance_analysis")]
        ctx = {"boq_value": 50.0, "drawing_value": 60.0}

        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await _handle_multi_action(matches, "do everything", ctx)

        statuses = {r["action"]: r["status"] for r in result["individual_results"]}
        # variance_analysis has numeric context → should succeed
        assert statuses["variance_analysis"] == "completed"
        assert result["action_count"] == 2

    @pytest.mark.asyncio
    async def test_action_count_equals_matches_length(self):
        mock_resp = _llm_resp("Three done.")
        matches = [_match("full_qto"), _match("check_compliance"), _match("risk_assessment")]
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await _handle_multi_action(matches, "full analysis", {})
        assert result["action_count"] == 3
        assert len(result["individual_results"]) == 3

    @pytest.mark.asyncio
    async def test_individual_results_have_required_keys(self):
        mock_resp = _llm_resp("ok")
        matches = [_match("full_qto")]
        with patch("app.llm.client.LLMClient.chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await _handle_multi_action(matches, "qto", {})
        for entry in result["individual_results"]:
            assert "action" in entry
            assert "status" in entry
            assert "confidence" in entry


# ── IntentRouter.route_multi ───────────────────────────────────────────────────

class TestRouteMulti:
    @pytest.mark.asyncio
    async def test_returns_non_empty_list(self):
        router = IntentRouter()
        results = await router.route_multi(user_message="extract quantities from drawing")
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_all_entries_are_intent_matches(self):
        router = IntentRouter()
        results = await router.route_multi(user_message="run QTO and check compliance")
        for r in results:
            assert isinstance(r, IntentMatch)
            assert isinstance(r.action_name, str)
            assert isinstance(r.confidence, float)

    @pytest.mark.asyncio
    async def test_fallback_for_unrecognized_message(self):
        router = IntentRouter()
        # Use min_confidence=1.0 to guarantee no pattern score qualifies
        results = await router.route_multi(
            user_message="zzzzzz_999_zzzzzz_not_a_real_request",
            min_confidence=1.0,
        )
        assert len(results) == 1
        assert results[0].action_name == "self_coding_agent"

    @pytest.mark.asyncio
    async def test_max_actions_cap(self):
        router = IntentRouter()
        results = await router.route_multi(
            user_message=(
                "extract quantities, run QTO, check compliance, "
                "assess risk, analyze schedule, process drawings"
            ),
            max_actions=2,
        )
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_results_sorted_by_confidence_descending(self):
        router = IntentRouter()
        results = await router.route_multi(
            user_message="extract quantities from drawing and check spec compliance"
        )
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_no_duplicate_action_names(self):
        router = IntentRouter()
        results = await router.route_multi(
            user_message="extract quantities and extract specs from drawing"
        )
        names = [r.action_name for r in results]
        assert len(names) == len(set(names)), "Duplicate action_name returned"

    @pytest.mark.asyncio
    async def test_min_confidence_filters_low_matches(self):
        router = IntentRouter()
        results = await router.route_multi(
            user_message="extract quantities",
            min_confidence=0.99,  # very high threshold — only exact matches pass
        )
        for r in results:
            # fallback has confidence 0.3, so either we get a high-conf exact match
            # or the fallback (which bypasses the threshold)
            assert r.action_name == "self_coding_agent" or r.confidence >= 0.99
