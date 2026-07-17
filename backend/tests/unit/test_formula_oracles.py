"""
Oracle gating tests for the construction formula library.

Every formula in initial_library.json must have a hand-derived scenario in
oracle_scenarios.json. Coverage guard fails CI if any library ID is missing.

Imports formula_runtime via an isolated loader to avoid app.services side effects.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

BACKEND = Path(__file__).resolve().parents[2]
LIBRARY_PATH = BACKEND / "data" / "formulas" / "initial_library.json"
ORACLE_PATH = BACKEND / "data" / "formulas" / "oracle_scenarios.json"
RUNTIME_PATH = BACKEND / "app" / "services" / "formula_runtime.py"


def _load_runtime():
    """Load formula_runtime without importing app.services.__init__."""
    if "app.services.formula_runtime" in sys.modules:
        return sys.modules["app.services.formula_runtime"]

    import types

    sys.path.insert(0, str(BACKEND))

    if "app" not in sys.modules or not getattr(sys.modules["app"], "__path__", None):
        app_pkg = types.ModuleType("app")
        app_pkg.__path__ = [str(BACKEND / "app")]
        sys.modules["app"] = app_pkg
    if "app.monitoring" not in sys.modules:
        mon = types.ModuleType("app.monitoring")
        mon.__path__ = [str(BACKEND / "app" / "monitoring")]
        sys.modules["app.monitoring"] = mon
    if "app.monitoring.metrics" not in sys.modules:
        try:
            import importlib

            sys.modules["app.monitoring.metrics"] = importlib.import_module(
                "app.monitoring.metrics"
            )
        except Exception:
            metrics_mod = types.ModuleType("app.monitoring.metrics")

            class FormulaMetrics:
                @staticmethod
                def record_validation_error(*_a, **_k):
                    pass

                @staticmethod
                def record_execution(*_a, **_k):
                    pass

            metrics_mod.FormulaMetrics = FormulaMetrics
            sys.modules["app.monitoring.metrics"] = metrics_mod

    if "app.services" not in sys.modules:
        pkg = types.ModuleType("app.services")
        pkg.__path__ = [str(BACKEND / "app" / "services")]
        sys.modules["app.services"] = pkg

    spec = importlib.util.spec_from_file_location(
        "app.services.formula_runtime",
        RUNTIME_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.services.formula_runtime"] = module
    spec.loader.exec_module(module)
    return module


fr = _load_runtime()
clear_formula_cache = fr.clear_formula_cache
evaluate_formula_by_id = fr.evaluate_formula_by_id
get_formulas = fr.get_formulas


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
