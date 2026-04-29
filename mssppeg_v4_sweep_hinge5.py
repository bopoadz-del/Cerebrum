#!/usr/bin/env python3
"""
MSSPPEG v4 — parallel parameter sweep (hinge5 subset).

Subset: 24 cases total
- SPACINGS = ["25cm", "50cm"]
- ARM_MODES = ["upper_double", "lower_double"]
- HINGE_CWS = [5]
- TIP_CWS = [1, 2, 3]
- MAIN_CLUTCHES = ["oneway", "rectifier"]
- HINGE_CLUTCHES = ["oneway"]
- V_WINDS = [6.0]
"""

import os
import csv
import time
import traceback
from itertools import product
from multiprocessing import Pool

from mssppeg_v4_physics import run_one

# ========== SWEEP SPACE ==========
SPACINGS = ["25cm", "50cm"]
ARM_MODES = ["upper_double", "lower_double"]
HINGE_CWS = [5]
TIP_CWS = [1, 2, 3]
MAIN_CLUTCHES = ["oneway", "rectifier"]
HINGE_CLUTCHES = ["oneway"]
V_WINDS = [6.0]

OUTPUT_CSV = "mssppeg_v4_sweep_hinge5.csv"

COLUMNS = [
    "run_id", "spacing", "arm_mode", "hinge_cw", "tip_cw",
    "main_clutch", "hinge_clutch", "v_wind", "t_stop",
    "E_init_j", "elec_total", "main_gen_j", "hinge1_j", "hinge2_j",
    "fric_j", "aero_j", "main_clutch_j", "hinge_clutch_plus_genheat_j",
    "peak_shaft_rpm", "peak_fly_rpm", "final_residual_j", "runtime_s",
]


def worker(args):
    idx, cfg = args
    run_id = f"run_{idx:03d}"
    t0 = time.time()
    try:
        res = run_one(cfg, t_max=120.0)
        row = {
            "run_id": run_id,
            "spacing": cfg["spacing"],
            "arm_mode": cfg["arm_mode"],
            "hinge_cw": cfg["hinge_cw"],
            "tip_cw": cfg["tip_cw"],
            "main_clutch": cfg["main_clutch"],
            "hinge_clutch": cfg["hinge_clutch"],
            "v_wind": cfg["v_wind"],
            "t_stop": res["t_stop"],
            "E_init_j": res["E_init_j"],
            "elec_total": res["elec_total"],
            "main_gen_j": res["main_gen_j"],
            "hinge1_j": res["hinge1_j"],
            "hinge2_j": res["hinge2_j"],
            "fric_j": res["fric_j"],
            "aero_j": res["aero_j"],
            "main_clutch_j": res["main_clutch_j"],
            "hinge_clutch_plus_genheat_j": res["hinge_clutch_plus_genheat_j"],
            "peak_shaft_rpm": res["peak_shaft_rpm"],
            "peak_fly_rpm": res["peak_fly_rpm"],
            "final_residual_j": res["final_residual_j"],
            "runtime_s": res["runtime_s"],
        }
        return row
    except Exception:
        return {
            "run_id": run_id,
            "spacing": cfg["spacing"],
            "arm_mode": cfg["arm_mode"],
            "hinge_cw": cfg["hinge_cw"],
            "tip_cw": cfg["tip_cw"],
            "main_clutch": cfg["main_clutch"],
            "hinge_clutch": cfg["hinge_clutch"],
            "v_wind": cfg["v_wind"],
            "t_stop": 0.0,
            "E_init_j": 0.0,
            "elec_total": 0.0,
            "main_gen_j": 0.0,
            "hinge1_j": 0.0,
            "hinge2_j": 0.0,
            "fric_j": 0.0,
            "aero_j": 0.0,
            "main_clutch_j": 0.0,
            "hinge_clutch_plus_genheat_j": 0.0,
            "peak_shaft_rpm": 0.0,
            "peak_fly_rpm": 0.0,
            "final_residual_j": 0.0,
            "runtime_s": time.time() - t0,
            "_error": traceback.format_exc(),
        }


def main():
    cases = list(product(
        SPACINGS, ARM_MODES, HINGE_CWS, TIP_CWS,
        MAIN_CLUTCHES, HINGE_CLUTCHES, V_WINDS
    ))
    print(f"Total cases: {len(cases)}")

    configs = []
    for (sp, am, hc, tc, mc, hgc, vw) in cases:
        configs.append({
            "spacing": sp,
            "arm_mode": am,
            "hinge_cw": hc,
            "tip_cw": tc,
            "main_clutch": mc,
            "hinge_clutch": hgc,
            "v_wind": vw,
        })

    n_procs = min(8, os.cpu_count())
    print(f"Using {n_procs} processes")

    results = []
    errors = []
    t_start = time.time()

    with Pool(processes=n_procs) as pool:
        for idx, row in enumerate(pool.imap_unordered(worker, enumerate(configs)), start=1):
            if "_error" in row:
                err = row.pop("_error")
                errors.append((row["run_id"], err))
                print(f"[{idx}/{len(cases)}] ERROR in {row['run_id']}: {err.splitlines()[-1]}")
            else:
                results.append(row)

            if idx % 5 == 0:
                elapsed = time.time() - t_start
                print(f"  ... progress: {idx}/{len(cases)} done ({elapsed:.1f}s elapsed)")

    total_elapsed = time.time() - t_start
    print(f"\nSweep complete: {len(results)} succeeded, {len(errors)} failed")
    print(f"Total wall time: {total_elapsed:.1f}s")

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {OUTPUT_CSV}")

    # Summary stats
    if results:
        et = [r["elec_total"] for r in results]
        print(f"\n=== Summary Stats ===")
        print(f"  elec_total  mean={sum(et)/len(et):.2f}  min={min(et):.2f}  max={max(et):.2f}")
        rt = [r["runtime_s"] for r in results]
        print(f"  runtime_s   mean={sum(rt)/len(rt):.2f}  min={min(rt):.2f}  max={max(rt):.2f}")
        sr = [r["peak_shaft_rpm"] for r in results]
        print(f"  peak_shaft  mean={sum(sr)/len(sr):.2f}  min={min(sr):.2f}  max={max(sr):.2f}")
        fr = [r["peak_fly_rpm"] for r in results]
        print(f"  peak_fly    mean={sum(fr)/len(fr):.2f}  min={min(fr):.2f}  max={max(fr):.2f}")

        # Best by main clutch
        oneway = [r for r in results if r["main_clutch"] == "oneway"]
        rectif = [r for r in results if r["main_clutch"] == "rectifier"]
        if oneway:
            print(f"\n  Oneway  elec mean={sum(r['elec_total'] for r in oneway)/len(oneway):.2f}")
        if rectif:
            print(f"  Rectifier elec mean={sum(r['elec_total'] for r in rectif)/len(rectif):.2f}")

    if errors:
        print(f"\n=== Errors ({len(errors)}) ===")
        for rid, err in errors:
            print(f"  {rid}: {err.splitlines()[-1]}")


if __name__ == "__main__":
    main()
