# Formula Verification Table

One row per library formula for operator one-by-one sign-off.
Each row lists the oracle inputs, hand-derived expected value, governing clause, and status.

Status legend: **GATED** = implemented + oracle test green + covered by the coverage guard.
Sign-off column is for the operator (`OK` / notes).

Library: `backend/data/formulas/initial_library.json` v2.1.0
Oracles: `backend/data/formulas/oracle_scenarios.json`
Tests: `backend/tests/unit/test_formula_oracles.py`

| Formula | Kind | Code | Inputs | Oracle | Clause | Status | Sign-off |
|---------|------|------|--------|--------|--------|--------|----------|
| concrete_volume | derived | geometry | length=10, width=5, height=0.3 | **15** | geometry | GATED | |
| rebar_weight | derived | bs | diameter=16, length=12 | **18.9389** | BS 8666 bar mass (approx) | GATED | |
| beam_moment_simple | derived | statics | load=20, span=6 | **90** | statics wL^2/8 | GATED | |
| beam_moment_point_load | derived | statics | load=50, span=6 | **75** | statics PL/4 | GATED | |
| beam_shear_simple | derived | statics | load=20, span=6 | **60** | statics wL/2 | GATED | |
| beam_deflection_simple | derived | statics | load=20.0, span=6.0, E=200000.0, I=150000000.0 | **11.25** | elastic UDL deflection (consistent mm units) | GATED | |
| column_axial_capacity | derived | aci | f_prime_c=30.0, Ag=90000.0, Ast=1800.0, fy=420.0, k=1.0, lu=3000.0, r=75.0 | **1435.09** | ACI 318-19 §22.4 + slenderness R=1-(k·lu/(140r))^2 | GATED | |
| footing_area | derived | aci | total_load=1500, soil_pressure=200 | **7.5** | A=P/q | GATED | |
| slab_thickness_min | derived | aci | span=8400 | **300** | ACI 318-19 Table 7.3.1.1 L/28 (SS one-way) | GATED | |
| steel_tension_capacity | derived | aisc | Fy=345, Ag=3000 | **1035** | AISC 360 Ch. D (yield on Ag) | GATED | |
| bolt_shear_capacity | derived | aisc | Fnv=372, Ab=380 | **84.816** | AISC 360 §J3.6 (simplified Rn=Fn*Ab) | GATED | |
| weld_capacity | derived | aisc | Fexx=490, size=6 | **1.24715** | AISC 360 §J2.4 fillet throat | GATED | |
| wind_pressure | derived | asce | q=1200, G=0.85, Cp=0.8, qi=1000, GCpi=0.18 | **636** | ASCE 7 Ch. 27 form p=qGCp-qi(GCpi) | GATED | |
| seismic_base_shear | derived | asce | Cs=0.125, W=10000 | **1250** | ASCE 7 §12.8.1 V=CsW | GATED | |
| live_load_reduction | derived | asce | L0=4.79, K_LL=4.0, At=400.0 | **2.99375** | ASCE 7 §4.7.2 (factor capped at 1.0) | GATED | |
| roi_calculator | derived | finance | gain=150000, cost=100000 | **50** | ROI=((gain-cost)/cost)*100 | GATED | |
| unit_cost_total | derived | cost | unit_price=125.5, quantity=40 | **5020** | unit×qty | GATED | |
| cost_per_sf | derived | cost | total_cost=2500000, area=12500 | **200** | total/area | GATED | |
| earned_value_cv | derived | pmbok | EV=500000, AC=520000 | **-20000** | PMBOK CV=EV-AC | GATED | |
| earned_value_sv | derived | pmbok | EV=500000, PV=480000 | **20000** | PMBOK SV=EV-PV | GATED | |
| earned_value_spi | derived | pmbok | EV=500000, PV=480000 | **1.04167** | PMBOK SPI=EV/PV | GATED | |
| earned_value_cpi | derived | pmbok | EV=500000, AC=520000 | **0.961538** | PMBOK CPI=EV/AC | GATED | |
| critical_path_float | derived | pmbok | LS=12, ES=8 | **4** | CPM TF=LS-ES | GATED | |
| productivity_rate | derived | cost | quantity=120, crew_size=4, hours=8 | **3.75** | qty/(crew*hours) | GATED | |
| concrete_cylinders | derived | astm | cylinders=[32.1, 33.4, 31.8] | **32.4333** | ASTM C39 average | GATED | |
| soil_bearing_pressure | derived | aci | load=1500, area=7.5 | **200** | q=P/A | GATED | |
| rebar_lap_length | derived | aci | fy=420.0, db=16.0, f_prime_c=30.0 | **584.237** | ACI 318-19 §25.5 (simplified ld form) | GATED | |
| concrete_shrinkage | derived | aci | f_prime_c=30 | **0.00072214** | ACI 209R shrinkage strain form | GATED | |
| masonry_wall_capacity | derived | tms | fm=13.8, An=100000.0, As=0.0, Fs=0.0, h=3000.0, thickness=200.0 | **297.474** | TMS 402 §8.2/§8.3 with R=1-(h/140r)^2 | GATED | |
| excavation_volume | derived | geometry | length=20, width=10, depth=3 | **600** | geometry | GATED | |
| backfill_volume | derived | geometry | loose_volume=480, shrinkage_factor=0.2 | **400** | compacted=loose/(1+shrink) | GATED | |
| concrete_curing_time | derived | aci | f_prime_c_target=30, f_prime_c_7day=21 | **14.2857** | ACI 308 strength-time estimate | GATED | |
| crane_lift_capacity | derived | osha | rated_capacity=200, load_weight=120, rigging=5, hook_block=10 | **65** | OSHA/CPCS net capacity | GATED | |
| scaffold_load_capacity | derived | osha | duty_rating=2.4, platform_area=10 | **24** | OSHA 1926.451 duty×area | GATED | |
| fall_arrest_force | derived | osha | mass=100, fall_factor=2.0 | **1.962** | ANSI Z359 / OSHA MAF context | GATED | |
| bim_clash_tolerance | reference_table | reference_table | distance=20, tolerance=25 | **True** | BIM Execution Plan clash rule | GATED | |
| laser_scan_accuracy | reference_table | reference_table | distance=50, angular_resolution=0.0003 | **15** | ASPRS / scanner datasheet | GATED | |
| prefab_module_weight | derived | geometry | volume=12, density=2400 | **28800** | mass=V*rho | GATED | |
| carbon_footprint_concrete | reference_table | reference_table | volume=10, cement_content=350, emission_factor=0.9 | **3150** | EPD / ISO 14040 factor lookup | GATED | |
| leed_points_estimate | reference_table | reference_table | ss_points=8, we_points=6, ea_points=12, mr_points=6, iq_points=8, ip_points=4 | **44** | LEED v4.1 BD+C category sum | GATED | |
