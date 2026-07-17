"""
Oracle gating tests for the construction formula library.

Every formula in initial_library.json must have a hand-derived scenario in
oracle_scenarios.json. Coverage guard fails CI if any library ID is missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from app.services.formula_runtime import (
    clear_formula_cache,
    evaluate_formula_by_id,
    get_formulas,
)

BACKEND = Path(__file__).resolve().parents[2]
LIBRARY_PATH = BACKEND / "data" / "formulas" / "initial_library.json"
ORACLE_PATH = BACKEND / "data" / "formulas" / "oracle_scenarios.json"


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    clear_formula_cache()
    monkeypatch.setenv("INITIAL_FORMULAS_PATH", str(LIBRARY_PATH))
    yield
    clear_formula_cache()


def _load_library_ids() -> List[str]:
    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return [f["id"] for f in data["formulas"]]


def _load_scenarios() -> List[Dict[str, Any]]:
    data = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


def test_oracle_scenarios_cover_all_library_formulas():
    """Coverage guard: every library formula must have at least one oracle."""
    library_ids = set(_load_library_ids())
    scenario_ids = {s["formula_id"] for s in _load_scenarios()}
    missing = library_ids - scenario_ids
    extra = scenario_ids - library_ids
    assert not missing, f"Library formulas missing oracle scenarios: {sorted(missing)}"
    assert not extra, f"Orphan oracle scenarios (not in library): {sorted(extra)}"


def test_every_library_formula_loads():
    formulas = get_formulas(settings_path=str(LIBRARY_PATH), force_reload=True)
    assert len(formulas) == len(_load_library_ids())
    assert {f.id for f in formulas} == set(_load_library_ids())


@pytest.mark.parametrize(
    "scenario",
    _load_scenarios(),
    ids=lambda s: f"{s['formula_id']}::{s.get('code_family', 'default')}",
)
def test_formula_oracle(scenario: Dict[str, Any]):
    """Run each hand-derived oracle against the live formula runtime."""
    formula_id = scenario["formula_id"]
    result = evaluate_formula_by_id(formula_id, scenario["inputs"])
    assert "error" not in result, (
        f"{formula_id} failed: {result.get('error')} "
        f"(clause={scenario.get('clause')}; derivation={scenario.get('derivation')})"
    )
    actual = result["output_values"]["result"]
    expected = scenario["expected_output"]
    rel = float(scenario.get("rel_tol", 1e-6))
    abs_tol = float(scenario.get("abs_tol", 1e-9))

    if isinstance(expected, bool):
        assert actual is expected or actual == expected
    else:
        assert actual == pytest.approx(expected, rel=rel, abs=abs_tol), (
            f"{formula_id}: got {actual!r}, expected {expected!r}. "
            f"Clause: {scenario.get('clause')}. Derivation: {scenario.get('derivation')}"
        )


def test_reference_table_formulas_are_labeled():
    formulas = get_formulas(settings_path=str(LIBRARY_PATH), force_reload=True)
    ref_ids = {
        "bim_clash_tolerance",
        "laser_scan_accuracy",
        "carbon_footprint_concrete",
        "leed_points_estimate",
    }
    for f in formulas:
        if f.id in ref_ids:
            assert f.kind == "reference_table", f"{f.id} must be kind=reference_table"
            assert f.note, f"{f.id} must carry a reference-table caveat note"
