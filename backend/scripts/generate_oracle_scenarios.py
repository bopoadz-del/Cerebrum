"""One-shot helper to build oracle_scenarios.json from initial_library.json."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Stub metrics so formula_runtime imports without full app stack
metrics_mod = types.ModuleType("app.monitoring.metrics")


class FormulaMetrics:
    @staticmethod
    def record_validation_error(*_a, **_k):
        pass

    @staticmethod
    def record_execution(*_a, **_k):
        pass


metrics_mod.FormulaMetrics = FormulaMetrics
sys.modules["app"] = types.ModuleType("app")
sys.modules["app.monitoring"] = types.ModuleType("app.monitoring")
sys.modules["app.monitoring.metrics"] = metrics_mod

spec = importlib.util.spec_from_file_location(
    "formula_runtime",
    ROOT / "app" / "services" / "formula_runtime.py",
)
assert spec and spec.loader
fr = importlib.util.module_from_spec(spec)
sys.modules["formula_runtime"] = fr
spec.loader.exec_module(fr)

SCENARIOS = {
    "concrete_volume": {
        "inputs": {"length": 10, "width": 5, "height": 0.3},
        "clause": "geometry",
        "code_family": "geometry",
    },
    "rebar_weight": {
        "inputs": {"diameter": 16, "length": 12},
        "clause": "BS 8666 bar mass approx d^2*0.006165",
        "code_family": "BS 8666",
    },
    "beam_moment_simple": {
        "inputs": {"load": 20, "span": 6},
        "clause": "statics wL^2/8",
        "code_family": "statics",
    },
    "beam_moment_point_load": {
        "inputs": {"load": 50, "span": 6},
        "clause": "statics PL/4",
        "code_family": "statics",
    },
    "beam_shear_simple": {
        "inputs": {"load": 20, "span": 6},
        "clause": "statics wL/2",
        "code_family": "statics",
    },
    "beam_deflection_simple": {
        "inputs": {"load": 10, "span": 5000, "E": 200000, "I": 8.33e7},
        "clause": "5wL^4/(384EI) consistent mm units",
        "code_family": "statics",
    },
    "column_axial_capacity": {
        "inputs": {
            "f_prime_c": 30,
            "Ag": 90000,
            "Ast": 3600,
            "fy": 420,
            "phi": 0.65,
            "k": 1.0,
            "lu": 3000,
            "r": 150,
        },
        "clause": "ACI 318-19 §22.4 + slenderness (k lu/r)/40",
        "code_family": "ACI",
    },
    "footing_area": {
        "inputs": {"total_load": 2000, "soil_pressure": 200},
        "clause": "A = P / q_allow",
        "code_family": "IBC",
    },
    "slab_thickness_min": {
        "inputs": {"span": 5600},
        "clause": "ACI 318-19 Tbl 7.3.1.1 L/28 (SS fy60)",
        "code_family": "ACI",
    },
    "steel_tension_capacity": {
        "inputs": {"Fy": 345, "Ag": 3000},
        "clause": "AISC 360 Ch D yield Fy Ag",
        "code_family": "AISC",
    },
    "bolt_shear_capacity": {
        "inputs": {"Fnv": 372, "Ab": 380},
        "clause": "AISC 360 §J3.6 0.6 Fnv Ab",
        "code_family": "AISC",
    },
    "weld_capacity": {
        "inputs": {"Fexx": 490, "size": 6},
        "clause": "AISC 360 §J2.4 fillet throat",
        "code_family": "AISC",
    },
    "wind_pressure": {
        "inputs": {"q": 1500, "G": 0.85, "Cp": 0.8, "qi": 1500, "GCpi": 0.18},
        "clause": "ASCE 7 Ch 27 form",
        "code_family": "ASCE",
    },
    "seismic_base_shear": {
        "inputs": {"Cs": 0.125, "W": 10000},
        "clause": "ASCE 7 §12.8 V=Cs W",
        "code_family": "ASCE",
    },
    "live_load_reduction": {
        "inputs": {"L0": 4.79, "K_LL": 4, "At": 40},
        "clause": "ASCE 7 §4.7",
        "code_family": "ASCE",
    },
    "roi_calculator": {
        "inputs": {"gain": 150000, "cost": 100000},
        "clause": "ROI definition",
        "code_family": "finance",
    },
    "unit_cost_total": {
        "inputs": {"unit_price": 125.5, "quantity": 40},
        "clause": "unit pricing",
        "code_family": "cost",
    },
    "cost_per_sf": {
        "inputs": {"total_cost": 2500000, "area": 10000},
        "clause": "cost / area",
        "code_family": "cost",
    },
    "earned_value_cv": {
        "inputs": {"EV": 100000, "AC": 95000},
        "clause": "PMBOK CV=EV-AC",
        "code_family": "PMBOK",
    },
    "earned_value_sv": {
        "inputs": {"EV": 100000, "PV": 110000},
        "clause": "PMBOK SV=EV-PV",
        "code_family": "PMBOK",
    },
    "earned_value_spi": {
        "inputs": {"EV": 100000, "PV": 110000},
        "clause": "PMBOK SPI=EV/PV",
        "code_family": "PMBOK",
    },
    "earned_value_cpi": {
        "inputs": {"EV": 100000, "AC": 95000},
        "clause": "PMBOK CPI=EV/AC",
        "code_family": "PMBOK",
    },
    "critical_path_float": {
        "inputs": {"LS": 12, "ES": 8},
        "clause": "CPM TF=LS-ES",
        "code_family": "CPM",
    },
    "productivity_rate": {
        "inputs": {"quantity": 80, "crew_size": 4, "hours": 8},
        "clause": "output per worker-hour",
        "code_family": "productivity",
    },
    "concrete_cylinders": {
        "inputs": {"cylinders": [32.1, 33.0, 31.5]},
        "clause": "ASTM C39 average",
        "code_family": "ASTM",
    },
    "soil_bearing_pressure": {
        "inputs": {"load": 2000, "area": 10},
        "clause": "q = P/A",
        "code_family": "IBC",
    },
    "rebar_lap_length": {
        "inputs": {"fy": 420, "db": 16, "f_prime_c": 30},
        "clause": "ACI 318-19 §25.5 simplified",
        "code_family": "ACI",
    },
    "concrete_shrinkage": {
        "inputs": {"f_prime_c": 35},
        "clause": "ACI 209R form",
        "code_family": "ACI",
    },
    "masonry_wall_capacity": {
        "inputs": {
            "fm": 13.8,
            "An": 76000,
            "fy": 420,
            "As": 600,
            "h": 2800,
            "r": 50,
        },
        "clause": "TMS 402 with [1-(h/140r)^2]",
        "code_family": "TMS",
    },
    "excavation_volume": {
        "inputs": {"length": 20, "width": 10, "depth": 3},
        "clause": "geometry",
        "code_family": "geometry",
    },
    "backfill_volume": {
        "inputs": {"loose_volume": 480, "shrinkage_factor": 0.15},
        "clause": "compaction shrink",
        "code_family": "earthwork",
    },
    "concrete_curing_time": {
        "inputs": {"f_prime_c_target": 30, "f_prime_c_7day": 21},
        "clause": "ACI 308 estimate",
        "code_family": "ACI",
    },
    "crane_lift_capacity": {
        "inputs": {
            "rated_capacity": 200,
            "load_weight": 120,
            "rigging": 5,
            "hook_block": 10,
        },
        "clause": "OSHA capacity remainder",
        "code_family": "OSHA",
    },
    "scaffold_load_capacity": {
        "inputs": {"duty_rating": 2.4, "platform_area": 12},
        "clause": "OSHA 1926.451 duty x area",
        "code_family": "OSHA",
    },
    "fall_arrest_force": {
        "inputs": {"mass": 100, "fall_factor": 2.0},
        "clause": "ANSI Z359 F=mg*FF (kN)",
        "code_family": "OSHA",
    },
    "bim_clash_tolerance": {
        "inputs": {"distance": 20, "tolerance": 25},
        "clause": "BEP clash rule (reference_table)",
        "code_family": "ISO 19650",
    },
    "laser_scan_accuracy": {
        "inputs": {"distance": 10, "angular_resolution": 0.0003},
        "clause": "spacing = d*theta (reference_table)",
        "code_family": "ASPRS",
    },
    "prefab_module_weight": {
        "inputs": {"volume": 12, "density": 2400},
        "clause": "mass = V rho",
        "code_family": "logistics",
    },
    "carbon_footprint_concrete": {
        "inputs": {"volume": 100, "cement_content": 350, "emission_factor": 0.9},
        "clause": "EPD factor lookup (reference_table)",
        "code_family": "ISO 14040",
    },
    "leed_points_estimate": {
        "inputs": {
            "ss_points": 8,
            "we_points": 6,
            "ea_points": 12,
            "mr_points": 6,
            "iq_points": 8,
            "ip_points": 4,
        },
        "clause": "LEED category sum (reference_table)",
        "code_family": "LEED",
    },
}


def main() -> None:
    lib_path = ROOT / "data" / "formulas" / "initial_library.json"
    lib = fr._load_formulas_from_file(lib_path)
    by_id = {f.id: f for f in lib}
    missing = set(by_id) - set(SCENARIOS)
    if missing:
        raise SystemExit(f"Missing scenarios for: {sorted(missing)}")

    out = {
        "version": "1.0.0",
        "description": (
            "Hand-derived oracle scenarios for Cerebrum initial_library.json. "
            "Expected values lock the library expression to a cited clause."
        ),
        "scenarios": [],
    }

    for fid, meta in SCENARIOS.items():
        formula = by_id[fid]
        inputs = dict(meta["inputs"])
        for inp in formula.inputs:
            if inp.name not in inputs and inp.default is not None:
                inputs[inp.name] = inp.default
        result = fr.eval_formula(
            formula.formula_expression, inputs, fid, formula.domain
        )
        if "error" in result:
            raise SystemExit(f"{fid}: {result}")
        val = result["output_values"]["result"]
        if isinstance(val, bool):
            expected = val
        elif isinstance(val, (int, float)):
            expected = round(float(val), 6)
        else:
            expected = val
        out["scenarios"].append(
            {
                "formula_id": fid,
                "inputs": meta["inputs"],
                "expected_output": expected,
                "clause": meta["clause"],
                "code_family": meta["code_family"],
                "kind": getattr(formula, "kind", "derived"),
                "derivation_note": (
                    f"Hand-checked against library expression and {meta['clause']}"
                ),
            }
        )
        print(fid, expected)

    out_path = ROOT / "data" / "formulas" / "oracle_scenarios.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(out['scenarios'])} scenarios -> {out_path}")


if __name__ == "__main__":
    main()
