"""
Oracle gating tests for the construction formula library.

Every formula in initial_library.json must have a scenario in
oracle_scenarios.json. Expected values are hand-derived against the
cited clause and locked here with pytest.approx.

Imports formula_runtime directly to avoid heavy app.services package side-effects.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FORMULAS_DIR = BACKEND_ROOT / "data" / "formulas"
LIBRARY_PATH = FORMULAS_DIR / "initial_library.json"
ORACLE_PATH = FORMULAS_DIR / "oracle_scenarios.json"
RUNTIME_PATH = BACKEND_ROOT / "app" / "services" / "formula_runtime.py"


def _load_runtime():
    """Load formula_runtime without importing app.services.__init__."""
    if "app.services.formula_runtime" in sys.modules:
        return sys.modules["app.services.formula_runtime"]

    import types

    sys.path.insert(0, str(BACKEND_ROOT))

    # Minimal package stubs so formula_runtime can import FormulaMetrics
    if "app" not in sys.modules or not getattr(sys.modules["app"], "__path__", None):
        app_pkg = types.ModuleType("app")
        app_pkg.__path__ = [str(BACKEND_ROOT / "app")]
        sys.modules["app"] = app_pkg
    if "app.monitoring" not in sys.modules:
        mon = types.ModuleType("app.monitoring")
        mon.__path__ = [str(BACKEND_ROOT / "app" / "monitoring")]
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
        pkg.__path__ = [str(BACKEND_ROOT / "app" / "services")]
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


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    fr.clear_formula_cache()
    monkeypatch.setenv("INITIAL_FORMULAS_PATH", str(LIBRARY_PATH))
    fr.clear_formula_cache()
    yield
    fr.clear_formula_cache()


def _load_oracle_scenarios() -> List[Dict[str, Any]]:
    data = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


def _library_ids() -> List[str]:
    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return [f["id"] for f in data["formulas"]]


def test_oracle_file_exists():
    assert ORACLE_PATH.exists(), "oracle_scenarios.json is required for formula gating"


def test_coverage_guard_every_library_formula_has_oracle():
    """Coverage guard: CI fails if a library formula lacks an oracle scenario."""
    library_ids = set(_library_ids())
    oracle_ids = {s["formula_id"] for s in _load_oracle_scenarios()}
    missing = sorted(library_ids - oracle_ids)
    extra = sorted(oracle_ids - library_ids)
    assert not missing, f"Library formulas missing oracle scenarios: {missing}"
    assert not extra, f"Oracle scenarios for unknown formulas: {extra}"
    assert len(library_ids) == len(oracle_ids) == 40


@pytest.mark.parametrize(
    "scenario",
    _load_oracle_scenarios(),
    ids=lambda s: s["formula_id"],
)
def test_formula_oracle(scenario: Dict[str, Any]):
    """Per-formula oracle: evaluate_formula_by_id matches hand-derived expected."""
    formula_id = scenario["formula_id"]
    result = fr.evaluate_formula_by_id(formula_id, scenario["inputs"])
    assert "error" not in result, f"{formula_id}: {result.get('error')}"
    actual = result["output_values"]["result"]
    expected = scenario["expected_output"]

    if isinstance(expected, bool):
        assert actual is expected or actual == expected
    elif isinstance(expected, (int, float)):
        assert actual == pytest.approx(expected, rel=1e-4, abs=1e-6)
    else:
        assert actual == expected


def test_reference_table_formulas_are_labeled():
    """Reference lookups must be honestly labeled (Fork Batch 5–6 pattern)."""
    formulas = {f.id: f for f in fr.get_formulas(force_reload=True)}
    for fid in (
        "bim_clash_tolerance",
        "laser_scan_accuracy",
        "carbon_footprint_concrete",
        "leed_points_estimate",
    ):
        assert formulas[fid].kind == "reference_table", fid
        assert "reference_table" in formulas[fid].tags


def test_column_and_masonry_include_slenderness_inputs():
    formulas = {f.id: f for f in fr.get_formulas(force_reload=True)}
    col_names = {i.name for i in formulas["column_axial_capacity"].inputs}
    mas_names = {i.name for i in formulas["masonry_wall_capacity"].inputs}
    assert {"k", "lu", "r"}.issubset(col_names)
    assert {"h", "r"}.issubset(mas_names)
    assert "(k * lu / r)" in formulas["column_axial_capacity"].formula_expression
    assert "140" in formulas["masonry_wall_capacity"].formula_expression
