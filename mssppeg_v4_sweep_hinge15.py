#!/usr/bin/env python3
"""
MSSPPEG v4 — Parallel parameter sweep (hinge CW = 15 subset)
"""

import os
import sys
import csv
import time
import traceback
from itertools import product
from multiprocessing import Pool

# Import the physics module (must be in same directory or on PYTHONPATH)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mssppeg_v4_physics import run_one

# ==================== SWEEP CONFIGURATION ====================
SPACINGS      = ["25cm", "50cm"]
ARM_MODES     = ["upper_double", "lower_double"]
HINGE_CWS     = [15]
TIP_CWS       = [1, 2, 3]
MAIN_CLUTCHES = ["oneway", "rectifier"]
HINGE_CLUTCHES = ["oneway"]
V_WINDS       = [6.0]

T_MAX = 120.0

CSV_COLUMNS = [
    "run_id", "spacing", "arm_mode", "hinge_cw", "tip_cw",
    "main_clutch", "hinge_clutch", "v_wind",
    "t_stop", "E_init_j", "elec_total",
    "main_gen_j", "hinge1_j", "hinge2_j",
    "fric_j", "aero_j", "main_clutch_j", "hinge_clutch_plus_genheat_j",
    "peak_shaft_rpm", "peak_fly_rpm", "final_residual_j",
    "runtime_s",
]

def _worker(cfg):
    """Wrapper that catches exceptions so one bad case doesn't kill the pool."""
    try:
        result = run_one(cfg, t_max=T_MAX)
        return {"status": "ok", "cfg": cfg, "result": result}
    except Exception as e:
        return {
            "status": "error",
            "cfg": cfg,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

def main():
    # Build case list
    cases = []
    for spacing, arm_mode, hinge_cw, tip_cw, main_clutch, hinge_clutch, v_wind in product(
        SPACINGS, ARM_MODES, HINGE_CWS, TIP_CWS, MAIN_CLUTCHES, HINGE_CLUTCHES, V_WINDS
    ):
        cases.append({
            "spacing": spacing,
            "arm_mode": arm_mode,
            "hinge_cw": hinge_cw,
            "tip_cw": tip_cw,
            "main_clutch": main_clutch,
            "hinge_clutch": hinge_clutch,
            "v_wind": v_wind,
        })

    n_cases = len(cases)
    print(f"Sweep: {n_cases} cases  |  workers: {min(8, os.cpu_count())}")
    print(f"Cases: spacing={SPACINGS}, arm_mode={ARM_MODES}, hinge_cw={HINGE_CWS}, "
          f"tip_cw={TIP_CWS}, main_clutch={MAIN_CLUTCHES}, hinge_clutch={HINGE_CLUTCHES}, v_wind={V_WINDS}")
    print("-" * 60)

    csv_path = "mssppeg_v4_sweep_hinge15.csv"
    # Write header
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

    t_start_global = time.time()
    results = []
    errors = []

    with Pool(processes=min(8, os.cpu_count())) as pool:
        for i, raw in enumerate(pool.imap_unordered(_worker, cases), start=1):
            if raw["status"] == "ok":
                cfg = raw["cfg"]
                r = raw["result"]
                row = {
                    "run_id": i,
                    "spacing": cfg["spacing"],
                    "arm_mode": cfg["arm_mode"],
                    "hinge_cw": cfg["hinge_cw"],
                    "tip_cw": cfg["tip_cw"],
                    "main_clutch": cfg["main_clutch"],
                    "hinge_clutch": cfg["hinge_clutch"],
                    "v_wind": cfg["v_wind"],
                    "t_stop": r["t_stop"],
                    "E_init_j": r["E_init_j"],
                    "elec_total": r["elec_total"],
                    "main_gen_j": r["main_gen_j"],
                    "hinge1_j": r["hinge1_j"],
                    "hinge2_j": r["hinge2_j"],
                    "fric_j": r["fric_j"],
                    "aero_j": r["aero_j"],
                    "main_clutch_j": r["main_clutch_j"],
                    "hinge_clutch_plus_genheat_j": r["hinge_clutch_plus_genheat_j"],
                    "peak_shaft_rpm": r["peak_shaft_rpm"],
                    "peak_fly_rpm": r["peak_fly_rpm"],
                    "final_residual_j": r["final_residual_j"],
                    "runtime_s": r["runtime_s"],
                }
                results.append(row)
                with open(csv_path, "a", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                    writer.writerow(row)
            else:
                errors.append({"case": raw["cfg"], "error": raw["error"], "traceback": raw["traceback"]})
                print(f"  [ERROR] case {i}: {raw['error']}")

            if i % 5 == 0 or i == n_cases:
                elapsed = time.time() - t_start_global
                print(f"  Progress: {i}/{n_cases}  ({elapsed:.1f}s elapsed, {i/elapsed:.2f} cases/s)")

    # Summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\nErrors: {len(errors)} / {n_cases}")
        for e in errors:
            cfg = e["case"]
            print(f"  - {cfg['spacing']} {cfg['arm_mode']} cwH={cfg['hinge_cw']} cwT={cfg['tip_cw']} "
                  f"main={cfg['main_clutch']} hinge={cfg['hinge_clutch']} v={cfg['v_wind']}: {e['error']}")
    else:
        print(f"\nAll {n_cases} cases completed without errors.")

    if results:
        elec = [r["elec_total"] for r in results]
        shaft_rpm = [r["peak_shaft_rpm"] for r in results]
        fly_rpm = [r["peak_fly_rpm"] for r in results]
        rt = [r["runtime_s"] for r in results]

        print(f"\nElectrical output (J):")
        print(f"  min={min(elec):.2f}  max={max(elec):.2f}  mean={sum(elec)/len(elec):.2f}  median={sorted(elec)[len(elec)//2]:.2f}")
        print(f"\nPeak shaft RPM:")
        print(f"  min={min(shaft_rpm):.1f}  max={max(shaft_rpm):.1f}  mean={sum(shaft_rpm)/len(shaft_rpm):.1f}")
        print(f"\nPeak flywheel RPM:")
        print(f"  min={min(fly_rpm):.1f}  max={max(fly_rpm):.1f}  mean={sum(fly_rpm)/len(fly_rpm):.1f}")
        print(f"\nRuntime per case (s):")
        print(f"  min={min(rt):.2f}  max={max(rt):.2f}  mean={sum(rt)/len(rt):.2f}  total={sum(rt):.1f}")
        print(f"\nWall-clock time: {time.time() - t_start_global:.1f}s")
        print(f"Speedup: {sum(rt) / (time.time() - t_start_global):.1f}x")

    print(f"\nResults saved to: {csv_path}")

if __name__ == "__main__":
    main()
