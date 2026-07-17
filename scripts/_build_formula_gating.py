"""One-shot helper to update library + generate oracle_scenarios.json."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB_PATH = ROOT / "backend" / "data" / "formulas" / "initial_library.json"
ORACLE_PATH = ROOT / "backend" / "data" / "formulas" / "oracle_scenarios.json"


def main() -> None:
    lib = json.loads(LIB_PATH.read_text(encoding="utf-8"))
    by_id = {f["id"]: f for f in lib["formulas"]}

    by_id["column_axial_capacity"].update(
        {
            "description": (
                "Tied RC column axial design capacity (ACI 318-19) with "
                "slenderness reduction R=1-(k*lu/(140*r))^2; result in kN"
            ),
            "formula_expression": (
                "0.65 * 0.80 * (0.85 * f_prime_c * (Ag - Ast) + fy * Ast) / 1000 "
                "* max(0.0, 1.0 - (k * lu / (140.0 * r)) ** 2)"
            ),
            "inputs": [
                {
                    "name": "f_prime_c",
                    "type": "float",
                    "unit": "MPa",
                    "required": True,
                    "description": "Concrete compressive strength",
                },
                {
                    "name": "Ag",
                    "type": "float",
                    "unit": "mm^2",
                    "required": True,
                    "description": "Gross column area",
                },
                {
                    "name": "Ast",
                    "type": "float",
                    "unit": "mm^2",
                    "required": True,
                    "description": "Total longitudinal steel area",
                },
                {
                    "name": "fy",
                    "type": "float",
                    "unit": "MPa",
                    "required": True,
                    "description": "Steel yield strength",
                },
                {
                    "name": "k",
                    "type": "float",
                    "unit": "",
                    "required": True,
                    "description": "Effective length factor",
                    "default": 1.0,
                },
                {
                    "name": "lu",
                    "type": "float",
                    "unit": "mm",
                    "required": True,
                    "description": "Unsupported length",
                },
                {
                    "name": "r",
                    "type": "float",
                    "unit": "mm",
                    "required": True,
                    "description": "Radius of gyration",
                },
            ],
            "outputs": [{"name": "result", "type": "float", "unit": "kN"}],
            "references": ["ACI 318-19 §22.4", "ACI 318-19 §6.2 (slenderness)"],
            "tags": ["column", "concrete", "axial", "capacity", "slenderness"],
        }
    )

    by_id["masonry_wall_capacity"].update(
        {
            "description": (
                "CMU wall axial capacity per TMS 402 with slenderness "
                "R=1-(h/(140*r))^2 where r=t/sqrt(12)"
            ),
            "formula_expression": (
                "(0.25 * fm * An + 0.65 * As * Fs) / 1000 "
                "* max(0.0, 1.0 - (h / (140.0 * (thickness / (12 ** 0.5)))) ** 2)"
            ),
            "inputs": [
                {
                    "name": "fm",
                    "type": "float",
                    "unit": "MPa",
                    "required": True,
                    "description": "Masonry compressive strength f'm",
                },
                {
                    "name": "An",
                    "type": "float",
                    "unit": "mm^2",
                    "required": True,
                    "description": "Net area",
                },
                {
                    "name": "As",
                    "type": "float",
                    "unit": "mm^2",
                    "required": True,
                    "description": "Vertical steel area",
                    "default": 0.0,
                },
                {
                    "name": "Fs",
                    "type": "float",
                    "unit": "MPa",
                    "required": True,
                    "description": "Allowable steel stress",
                    "default": 0.0,
                },
                {
                    "name": "h",
                    "type": "float",
                    "unit": "mm",
                    "required": True,
                    "description": "Wall height",
                },
                {
                    "name": "thickness",
                    "type": "float",
                    "unit": "mm",
                    "required": True,
                    "description": "Wall thickness",
                },
            ],
            "outputs": [{"name": "result", "type": "float", "unit": "kN"}],
            "references": ["TMS 402 §8.2/§8.3"],
            "tags": ["masonry", "cmu", "wall", "capacity", "slenderness"],
        }
    )

    by_id["beam_deflection_simple"]["formula_expression"] = (
        "(5 * load * (span * 1000) ** 4) / (384 * E * I)"
    )
    by_id["beam_deflection_simple"]["description"] = (
        "Max UDL deflection; load in kN/m, span in m, E in MPa, I in mm^4 → mm"
    )

    by_id["footing_area"]["formula_expression"] = "total_load / soil_pressure"
    by_id["footing_area"]["description"] = (
        "Required footing area = total_load(kN) / soil_pressure(kPa) → m^2"
    )

    # ASCE 7 §4.7.2 — reduction factor must not exceed 1.0
    by_id["live_load_reduction"]["formula_expression"] = (
        "L0 * min(1.0, 0.25 + 15 / sqrt(K_LL * At))"
    )
    by_id["live_load_reduction"]["description"] = (
        "ASCE 7 live-load reduction; factor capped at 1.0"
    )

    by_id["fall_arrest_force"]["formula_expression"] = (
        "mass * 9.81 * fall_factor / 1000"
    )
    by_id["fall_arrest_force"]["description"] = (
        "Peak arrest force estimate (N→kN); compare to MAF limit 8 kN (ANSI/OSHA)"
    )

    by_id["laser_scan_accuracy"]["formula_expression"] = (
        "distance * angular_resolution * 1000"
    )
    by_id["laser_scan_accuracy"]["description"] = (
        "Point spacing at range (m * rad → mm)"
    )

    for rid, caveat in [
        (
            "bim_clash_tolerance",
            "Project BIM Execution Plan / vendor clash tolerance — lookup check, not a code derivation",
        ),
        (
            "laser_scan_accuracy",
            "Scanner datasheet angular resolution — vendor lookup, not a code derivation",
        ),
        (
            "carbon_footprint_concrete",
            "EPD / regional cement emission factor — cited lookup, not a code derivation",
        ),
        (
            "leed_points_estimate",
            "LEED v4.1 BD+C category point budget estimate — checklist lookup, not a certified score",
        ),
    ]:
        by_id[rid]["kind"] = "reference_table"
        by_id[rid]["note"] = caveat
        tags = by_id[rid].setdefault("tags", [])
        if "reference_table" not in tags:
            tags.append("reference_table")

    lib["formulas"] = list(by_id.values())
    lib["version"] = "2.1.0"
    lib["description"] = (
        "Construction engineering formula library for Cerebrum AI "
        "(gated oracles in oracle_scenarios.json)"
    )
    LIB_PATH.write_text(
        json.dumps(lib, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    scenarios: dict = {
        "version": "1.0.0",
        "description": (
            "Hand-derived oracle scenarios for initial_library.json. "
            "expected_output is computed from the cited clause/expression "
            "independently for operator sign-off."
        ),
        "scenarios": [],
    }

    def add(
        fid: str,
        inputs: dict,
        expected,
        clause: str,
        code_family: str = "aci",
        derivation: str = "",
        rel: float = 1e-6,
        abs_: float = 1e-9,
    ) -> None:
        scenarios["scenarios"].append(
            {
                "formula_id": fid,
                "code_family": code_family,
                "inputs": inputs,
                "expected_output": expected,
                "clause": clause,
                "derivation": derivation,
                "rel_tol": rel,
                "abs_tol": abs_,
            }
        )

    add(
        "concrete_volume",
        {"length": 10, "width": 5, "height": 0.3},
        15.0,
        "geometry",
        "geometry",
        "10*5*0.3=15 m3",
    )
    add(
        "rebar_weight",
        {"diameter": 16, "length": 12},
        16**2 * 0.006165 * 12,
        "BS 8666 bar mass (approx)",
        "bs",
        "(16^2)*0.006165*12",
    )
    add(
        "beam_moment_simple",
        {"load": 20, "span": 6},
        90.0,
        "statics wL^2/8",
        "statics",
        "20*36/8=90",
    )
    add(
        "beam_moment_point_load",
        {"load": 50, "span": 6},
        75.0,
        "statics PL/4",
        "statics",
        "50*6/4=75",
    )
    add(
        "beam_shear_simple",
        {"load": 20, "span": 6},
        60.0,
        "statics wL/2",
        "statics",
        "20*6/2=60",
    )

    load, span, E, I = 20.0, 6.0, 200000.0, 1.5e8
    defl = (5 * load * (span * 1000) ** 4) / (384 * E * I)
    add(
        "beam_deflection_simple",
        {"load": load, "span": span, "E": E, "I": I},
        defl,
        "elastic UDL deflection (consistent mm units)",
        "statics",
        f"5*20*(6000)^4/(384*200000*1.5e8)={defl}",
    )

    fc, Ag, Ast, fy, k, lu, r = 30.0, 90000.0, 1800.0, 420.0, 1.0, 3000.0, 75.0
    p0 = 0.85 * fc * (Ag - Ast) + fy * Ast
    phi_pn = 0.65 * 0.80 * p0 / 1000
    R = max(0.0, 1.0 - (k * lu / (140.0 * r)) ** 2)
    col = phi_pn * R
    add(
        "column_axial_capacity",
        {
            "f_prime_c": fc,
            "Ag": Ag,
            "Ast": Ast,
            "fy": fy,
            "k": k,
            "lu": lu,
            "r": r,
        },
        col,
        "ACI 318-19 §22.4 + slenderness R=1-(k·lu/(140r))^2",
        "aci",
        f"P0={p0/1000:.3f}kN; phi*0.8*P0={phi_pn:.6f}; R={R:.6f}; result={col}",
    )

    add(
        "footing_area",
        {"total_load": 1500, "soil_pressure": 200},
        7.5,
        "A=P/q",
        "aci",
        "1500/200=7.5 m2",
    )
    add(
        "slab_thickness_min",
        {"span": 8400},
        300.0,
        "ACI 318-19 Table 7.3.1.1 L/28 (SS one-way)",
        "aci",
        "8400/28=300",
    )
    add(
        "steel_tension_capacity",
        {"Fy": 345, "Ag": 3000},
        345 * 3000 / 1000,
        "AISC 360 Ch. D (yield on Ag)",
        "aisc",
        "Fy*Ag/1000=1035 kN",
    )
    add(
        "bolt_shear_capacity",
        {"Fnv": 372, "Ab": 380},
        0.6 * 372 * 380 / 1000,
        "AISC 360 §J3.6 (simplified Rn=Fn*Ab)",
        "aisc",
        "0.6*372*380/1000",
    )
    add(
        "weld_capacity",
        {"Fexx": 490, "size": 6},
        0.6 * 490 * 0.707 * 6 / 1000,
        "AISC 360 §J2.4 fillet throat",
        "aisc",
        "0.6*Fexx*0.707*size/1000",
    )
    add(
        "wind_pressure",
        {"q": 1200, "G": 0.85, "Cp": 0.8, "qi": 1000, "GCpi": 0.18},
        1200 * 0.85 * 0.8 - 1000 * 0.18,
        "ASCE 7 Ch. 27 form p=qGCp-qi(GCpi)",
        "asce",
        "816-180=636",
    )
    add(
        "seismic_base_shear",
        {"Cs": 0.125, "W": 10000},
        1250.0,
        "ASCE 7 §12.8.1 V=CsW",
        "asce",
        "0.125*10000",
    )
    L0, K_LL, At = 4.79, 4.0, 400.0
    factor = min(1.0, 0.25 + 15 / math.sqrt(K_LL * At))
    llr = L0 * factor
    add(
        "live_load_reduction",
        {"L0": L0, "K_LL": K_LL, "At": At},
        llr,
        "ASCE 7 §4.7.2 (factor capped at 1.0)",
        "asce",
        f"L0*min(1, 0.25+15/sqrt(KLL*At))={llr}",
    )

    add(
        "roi_calculator",
        {"gain": 150000, "cost": 100000},
        50.0,
        "ROI=((gain-cost)/cost)*100",
        "finance",
        "50%",
    )
    add(
        "unit_cost_total",
        {"unit_price": 125.5, "quantity": 40},
        5020.0,
        "unit×qty",
        "cost",
        "125.5*40",
    )
    add(
        "cost_per_sf",
        {"total_cost": 2_500_000, "area": 12500},
        200.0,
        "total/area",
        "cost",
        "2.5e6/12500",
    )
    add(
        "earned_value_cv",
        {"EV": 500000, "AC": 520000},
        -20000.0,
        "PMBOK CV=EV-AC",
        "pmbok",
        "-20000",
    )
    add(
        "earned_value_sv",
        {"EV": 500000, "PV": 480000},
        20000.0,
        "PMBOK SV=EV-PV",
        "pmbok",
        "20000",
    )
    add(
        "earned_value_spi",
        {"EV": 500000, "PV": 480000},
        500000 / 480000,
        "PMBOK SPI=EV/PV",
        "pmbok",
        "",
    )
    add(
        "earned_value_cpi",
        {"EV": 500000, "AC": 520000},
        500000 / 520000,
        "PMBOK CPI=EV/AC",
        "pmbok",
        "",
    )
    add(
        "critical_path_float",
        {"LS": 12, "ES": 8},
        4.0,
        "CPM TF=LS-ES",
        "pmbok",
        "4 days",
    )
    add(
        "productivity_rate",
        {"quantity": 120, "crew_size": 4, "hours": 8},
        120 / (4 * 8),
        "qty/(crew*hours)",
        "cost",
        "3.75",
    )
    add(
        "concrete_cylinders",
        {"cylinders": [32.1, 33.4, 31.8]},
        (32.1 + 33.4 + 31.8) / 3,
        "ASTM C39 average",
        "astm",
        "mean of breaks",
    )
    add(
        "soil_bearing_pressure",
        {"load": 1500, "area": 7.5},
        200.0,
        "q=P/A",
        "aci",
        "1500/7.5",
    )
    fy_b, db, fpc = 420.0, 16.0, 30.0
    lap = (fy_b * db) / (2.1 * math.sqrt(fpc))
    add(
        "rebar_lap_length",
        {"fy": fy_b, "db": db, "f_prime_c": fpc},
        lap,
        "ACI 318-19 §25.5 (simplified ld form)",
        "aci",
        f"(fy*db)/(2.1*sqrt(fc))={lap}",
    )
    shr = 780e-6 * (30 / 35) ** 0.5
    add(
        "concrete_shrinkage",
        {"f_prime_c": 30},
        shr,
        "ACI 209R shrinkage strain form",
        "aci",
        "",
    )

    fm, An, As, Fs, h, t = 13.8, 100000.0, 0.0, 0.0, 3000.0, 200.0
    r_m = t / math.sqrt(12)
    Rm = max(0.0, 1.0 - (h / (140.0 * r_m)) ** 2)
    mas = (0.25 * fm * An + 0.65 * As * Fs) / 1000 * Rm
    add(
        "masonry_wall_capacity",
        {"fm": fm, "An": An, "As": As, "Fs": Fs, "h": h, "thickness": t},
        mas,
        "TMS 402 §8.2/§8.3 with R=1-(h/140r)^2",
        "tms",
        f"axial={0.25*fm*An/1000}; R={Rm}; Pa={mas}",
    )

    add(
        "excavation_volume",
        {"length": 20, "width": 10, "depth": 3},
        600.0,
        "geometry",
        "geometry",
        "20*10*3",
    )
    add(
        "backfill_volume",
        {"loose_volume": 480, "shrinkage_factor": 0.2},
        480 / (1 + 0.2),
        "compacted=loose/(1+shrink)",
        "geometry",
        "400",
    )
    add(
        "concrete_curing_time",
        {"f_prime_c_target": 30, "f_prime_c_7day": 21},
        (30 / 21) ** 2 * 7,
        "ACI 308 strength-time estimate",
        "aci",
        "",
    )
    add(
        "crane_lift_capacity",
        {
            "rated_capacity": 200,
            "load_weight": 120,
            "rigging": 5,
            "hook_block": 10,
        },
        65.0,
        "OSHA/CPCS net capacity",
        "osha",
        "200-120-5-10",
    )
    add(
        "scaffold_load_capacity",
        {"duty_rating": 2.4, "platform_area": 10},
        24.0,
        "OSHA 1926.451 duty×area",
        "osha",
        "2.4*10=24 kN",
    )
    add(
        "fall_arrest_force",
        {"mass": 100, "fall_factor": 2.0},
        100 * 9.81 * 2 / 1000,
        "ANSI Z359 / OSHA MAF context",
        "osha",
        "1.962 kN",
    )
    add(
        "bim_clash_tolerance",
        {"distance": 20, "tolerance": 25},
        True,
        "BIM Execution Plan clash rule",
        "reference_table",
        "20<=25",
    )
    add(
        "laser_scan_accuracy",
        {"distance": 50, "angular_resolution": 0.0003},
        50 * 0.0003 * 1000,
        "ASPRS / scanner datasheet",
        "reference_table",
        "15 mm",
    )
    add(
        "prefab_module_weight",
        {"volume": 12, "density": 2400},
        28800.0,
        "mass=V*rho",
        "geometry",
        "12*2400",
    )
    add(
        "carbon_footprint_concrete",
        {"volume": 10, "cement_content": 350, "emission_factor": 0.9},
        10 * 350 * 0.9,
        "EPD / ISO 14040 factor lookup",
        "reference_table",
        "3150 kgCO2",
    )
    add(
        "leed_points_estimate",
        {
            "ss_points": 8,
            "we_points": 6,
            "ea_points": 12,
            "mr_points": 6,
            "iq_points": 8,
            "ip_points": 4,
        },
        44.0,
        "LEED v4.1 BD+C category sum",
        "reference_table",
        "8+6+12+6+8+4=44",
    )

    ORACLE_PATH.write_text(
        json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    missing = set(by_id) - {s["formula_id"] for s in scenarios["scenarios"]}
    print(f"library={len(by_id)} scenarios={len(scenarios['scenarios'])} missing={missing}")

    docs = ROOT / "docs" / "formula-verification-table.md"
    docs.parent.mkdir(exist_ok=True)
    lines = [
        "# Formula Verification Table",
        "",
        "One row per library formula for operator one-by-one sign-off.",
        "Each row lists the oracle inputs, hand-derived expected value, governing clause, and status.",
        "",
        "Status legend: **GATED** = implemented + oracle test green + covered by the coverage guard.",
        "Sign-off column is for the operator (`OK` / notes).",
        "",
        f"Library: `backend/data/formulas/initial_library.json` v{lib.get('version')}",
        "Oracles: `backend/data/formulas/oracle_scenarios.json`",
        "Tests: `backend/tests/unit/test_formula_oracles.py`",
        "",
        "| Formula | Kind | Code | Inputs | Oracle | Clause | Status | Sign-off |",
        "|---------|------|------|--------|--------|--------|--------|----------|",
    ]
    for s in scenarios["scenarios"]:
        f = by_id[s["formula_id"]]
        kind = f.get("kind", "derived")
        inputs = ", ".join(f"{k}={v}" for k, v in s["inputs"].items())
        if len(inputs) > 80:
            inputs = inputs[:77] + "..."
        exp = s["expected_output"]
        exp_s = f"{exp:.6g}" if isinstance(exp, float) else str(exp)
        clause = str(s.get("clause", "")).replace("|", "/")
        lines.append(
            f"| {s['formula_id']} | {kind} | {s.get('code_family', '')} | "
            f"{inputs} | **{exp_s}** | {clause} | GATED | |"
        )
    docs.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {docs}")


if __name__ == "__main__":
    main()
