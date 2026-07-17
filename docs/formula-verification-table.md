# Formula Verification Table — Cerebrum

One row per formula in `backend/data/formulas/initial_library.json` for operator
one-by-one sign-off. Each row lists the exact oracle inputs, the hand-derived
expected value, the governing clause, and the status of the CI gate.

Oracle scenarios live in `backend/data/formulas/oracle_scenarios.json`.
Tests: `backend/tests/unit/test_formula_oracles.py` (coverage guard + per-formula oracles).

**Status legend:** **GATED** = implemented + oracle test green + covered by the
coverage guard. **Sign-off** is for the operator (`OK` / notes).

**Kind:** `derived` = engineering expression; `reference_table` = cited lookup /
planning estimate (not a code derivation). Caveats are in the library description.

| Formula | Code | Kind | Inputs | Oracle | Clause | Status | Sign-off |
|---------|------|------|--------|--------|--------|--------|----------|
| concrete_volume | geometry | derived | L=10, W=5, H=0.3 m | **15.0 m³** | geometry | GATED | |
| rebar_weight | BS 8666 | derived | d=16 mm, L=12 m | **18.93888 kg** | d²·0.006165 | GATED | |
| beam_moment_simple | statics | derived | w=20 kN/m, L=6 m | **90.0 kN·m** | wL²/8 | GATED | |
| beam_moment_point_load | statics | derived | P=50 kN, L=6 m | **75.0 kN·m** | PL/4 | GATED | |
| beam_shear_simple | statics | derived | w=20 kN/m, L=6 m | **60.0 kN** | wL/2 | GATED | |
| beam_deflection_simple | statics | derived | w=10, L=5000, E=200000, I=8.33e7 (mm units) | **4.884766** | 5wL⁴/(384EI) | GATED | |
| column_axial_capacity | ACI | derived | fc=30, Ag=90000, Ast=3600, fy=420, φ=0.65, k=1, lu=3000, r=150 | **1448.928 kN** | ACI 318-19 §22.4 + (k·lu/r)/40 | GATED | |
| footing_area | IBC | derived | P=2000 kN, q=200 kPa | **10.0 m²** | A=P/q | GATED | |
| slab_thickness_min | ACI | derived | span=5600 mm | **200.0 mm** | ACI 318-19 Tbl 7.3.1.1 L/28 | GATED | |
| steel_tension_capacity | AISC | derived | Fy=345, Ag=3000 | **1035.0 kN** | AISC 360 Ch D | GATED | |
| bolt_shear_capacity | AISC | derived | Fnv=372, Ab=380 | **84.816 kN** | AISC 360 §J3.6 | GATED | |
| weld_capacity | AISC | derived | Fexx=490, size=6 | **1.247148 kN/mm** | AISC 360 §J2.4 | GATED | |
| wind_pressure | ASCE | derived | q=1500, G=0.85, Cp=0.8, qi=1500, GCpi=0.18 | **750.0 Pa** | ASCE 7 Ch 27 | GATED | |
| seismic_base_shear | ASCE | derived | Cs=0.125, W=10000 | **1250.0 kN** | ASCE 7 §12.8 | GATED | |
| live_load_reduction | ASCE | derived | L0=4.79, KLL=4, At=40 | **4.79 kPa** (capped ≤ L0) | ASCE 7 §4.7 | GATED | |
| roi_calculator | finance | derived | gain=150000, cost=100000 | **50.0 %** | ROI definition | GATED | |
| unit_cost_total | cost | derived | unit_price=125.5, qty=40 | **5020.0** | unit pricing | GATED | |
| cost_per_sf | cost | derived | total=2.5e6, area=10000 | **250.0** | cost/area | GATED | |
| earned_value_cv | PMBOK | derived | EV=100000, AC=95000 | **5000.0** | CV=EV−AC | GATED | |
| earned_value_sv | PMBOK | derived | EV=100000, PV=110000 | **-10000.0** | SV=EV−PV | GATED | |
| earned_value_spi | PMBOK | derived | EV=100000, PV=110000 | **0.909091** | SPI=EV/PV | GATED | |
| earned_value_cpi | PMBOK | derived | EV=100000, AC=95000 | **1.052632** | CPI=EV/AC | GATED | |
| critical_path_float | CPM | derived | LS=12, ES=8 | **4.0 days** | TF=LS−ES | GATED | |
| productivity_rate | productivity | derived | qty=80, crew=4, hours=8 | **2.5** | qty/(crew·hours) | GATED | |
| concrete_cylinders | ASTM | derived | [32.1, 33.0, 31.5] MPa | **32.2 MPa** | ASTM C39 average | GATED | |
| soil_bearing_pressure | IBC | derived | load=2000 kN, area=10 m² | **200.0 kPa** | q=P/A | GATED | |
| rebar_lap_length | ACI | derived | fy=420, db=16, fc=30 | **584.237395 mm** | ACI 318-19 §25.5 simplified | GATED | |
| concrete_shrinkage | ACI | derived | fc=35 | **0.00078** | ACI 209R form | GATED | |
| masonry_wall_capacity | TMS | derived | fm=13.8, An=76000, fy=420, As=600, h=2800, r=50 | **733.17888 kN** | TMS 402 [1−(h/140r)²] | GATED | |
| excavation_volume | geometry | derived | 20×10×3 m | **600.0 m³** | geometry | GATED | |
| backfill_volume | earthwork | derived | loose=480, shrink=0.15 | **417.391304 m³** | compaction shrink | GATED | |
| concrete_curing_time | ACI | derived | target=30, 7day=21 | **14.285714 days** | ACI 308 estimate | GATED | |
| crane_lift_capacity | OSHA | derived | rated=200, load=120, rigging=5, hook=10 | **65.0 kN** | capacity remainder | GATED | |
| scaffold_load_capacity | OSHA | derived | duty=2.4 kPa, area=12 m² | **28.8 kN** | OSHA 1926.451 | GATED | |
| fall_arrest_force | OSHA | derived | mass=100 kg, FF=2 | **1.962 kN** | ANSI Z359 F=mg·FF | GATED | |
| bim_clash_tolerance | ISO 19650 | reference_table | distance=20, tol=25 mm | **True** | BEP clash rule | GATED | |
| laser_scan_accuracy | ASPRS | reference_table | d=10 m, θ=0.0003 rad | **3.0 mm** | spacing=d·θ | GATED | |
| prefab_module_weight | logistics | derived | V=12 m³, ρ=2400 | **28800 kg** | m=Vρ | GATED | |
| carbon_footprint_concrete | ISO 14040 | reference_table | V=100, cement=350, EF=0.9 | **31500 kgCO2** | EPD factor | GATED | |
| leed_points_estimate | LEED | reference_table | SS8+WE6+EA12+MR6+IQ8+IP4 | **44 points** | category sum | GATED | |

## Gate checklist

1. Oracle scenario exists for every `initial_library.json` id.
2. `pytest backend/tests/unit/test_formula_oracles.py` green.
3. Column / masonry expressions include slenderness inputs (not short-column-only fakes).
4. Reference-table formulas carry `kind: reference_table` plus caveat in description.
