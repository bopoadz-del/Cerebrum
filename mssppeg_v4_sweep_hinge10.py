#!/usr/bin/env python3
"""
MSSPPEG v4 — Parallel sweep for hinge CW = 10 subset.
"""

import os
import csv
import time
import traceback
from multiprocessing import Pool

import numpy as np
from mssppeg_v4_physics import run_one

SPACINGS = ["25cm", "50cm"]
ARM_MODES = ["upper_double", "lower_double"]
HINGE_CWS = [10]
TIP_CWS = [1, 2, 3]
MAIN_CLUTCHES = ["oneway", "rectifier"]
HINGE_CLUTCHES = ["oneway"]
V_WINDS = [6.0]

CASES = [
    {
        "spacing": s,
        "arm_mode": a,
        "hinge_cw": h,
        "tip_cw": t,
        "main_clutch": m,
        "hinge_clutch": hc,
        "v_wind": v,
    }
    for s in SPACINGS
    for a in ARM_MODES
    for h in HINGE_CWS
    for t in TIP_CWS
    for m in MAIN_CLUTCHES
    for hc in HINGE_CLUTCHES
    for v in V_WINDS
]

CSV_COLUMNS = [
    "run_id",
    "spacing",
    "arm_mode",
    "hinge_cw",
    "tip_cw",
    "main_clutch",
    "hinge_clutch",
    "v_wind",
    "t_stop",
    "E_init_j",
    "elec_total",
    "main_gen_j",
    "hinge1_j",
    "hinge2_j",
    "fric_j",
    "aero_j",
    "main_clutch_j",
    "hinge_clutch_plus_genheat_j",
    "peak_shaft_rpm",
    "peak_fly_rpm",
    "final_residual_j",
    "runtime_s",
]


def _run_case(args):
    idx, cfg = args
    run_id = f"{idx:03d}"
    try:
        result = run_one(cfg, t_max=120.0)
        row = {
            "run_id": run_id,
            "spacing": cfg["spacing"],
            "arm_mode": cfg["arm_mode"],
            "hinge_cw": cfg["hinge_cw"],
            "tip_cw": cfg["tip_cw"],
            "main_clutch": cfg["main_clutch"],
            "hinge_clutch": cfg["hinge_clutch"],
            "v_wind": cfg["v_wind"],
            "t_stop": result["t_stop"],
            "E_init_j": result["E_init_j"],
            "elec_total": result["elec_total"],
            "main_gen_j": result["main_gen_j"],
            "hinge1_j": result["hinge1_j"],
            "hinge2_j": result["hinge2_j"],
            "fric_j": result["fric_j"],
            "aero_j": result["aero_j"],
            "main_clutch_j": result["main_clutch_j"],
            "hinge_clutch_plus_genheat_j": result["hinge_clutch_plus_genheat_j"],
            "peak_shaft_rpm": result["peak_shaft_rpm"],
            "peak_fly_rpm": result["peak_fly_rpm"],
            "final_residual_j": result["final_residual_j"],
            "runtime_s": result["runtime_s"],
        }
        return idx, row, None
    except Exception as e:
        return idx, None, (run_id, str(e), traceback.format_exc())


def main():
    total = len(CASES)
    print(f"Total cases: {total}")
    print(f"Processes: {min(8, os.cpu_count())}")
    print()

    results = [None] * total
    errors = []

    t0 = time.time()
    with Pool(processes=min(8, os.cpu_count())) as pool:
        for idx, row, err in pool.imap_unordered(_run_case, enumerate(CASES, start=1)):
            if err is not None:
                run_id, msg, tb = err
                errors.append(err)
                print(f"[{run_id}] ERROR: {msg}")
            else:
                results[idx - 1] = row

            if idx % 5 == 0 or idx == total:
                print(f"Progress: {idx}/{total} ({100*idx/total:.1f}%)")

    elapsed = time.time() - t0

    # Write CSV
    csv_path = "/root/.openclaw/workspace/mssppeg_v4_sweep_hinge10.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in results:
            if row is not None:
                writer.writerow(row)

    # Summary stats
    ok_rows = [r for r in results if r is not None]
    n_ok = len(ok_rows)
    n_fail = total - n_ok

    print(f"\n=== SWEEP COMPLETE ===")
    print(f"Total cases: {total}")
    print(f"Successful:  {n_ok}")
    print(f"Failed:      {n_fail}")
    print(f"Wall time:   {elapsed:.1f} s")
    print(f"CSV saved:   {csv_path}")

    if ok_rows:
        elec = np.array([r["elec_total"] for r in ok_rows])
        shaft = np.array([r["peak_shaft_rpm"] for r in ok_rows])
        fly = np.array([r["peak_fly_rpm"] for r in ok_rows])
        runtime = np.array([r["runtime_s"] for r in ok_rows])

        print(f"\n--- Electrical energy (J) ---")
        print(f"  mean:  {np.mean(elec):.2f}")
        print(f"  std:   {np.std(elec):.2f}")
        print(f"  min:   {np.min(elec):.2f}")
        print(f"  max:   {np.max(elec):.2f}")

        print(f"\n--- Peak shaft RPM ---")
        print(f"  mean:  {np.mean(shaft):.1f}")
        print(f"  std:   {np.std(shaft):.1f}")
        print(f"  min:   {np.min(shaft):.1f}")
        print(f"  max:   {np.max(shaft):.1f}")

        print(f"\n--- Peak flywheel RPM ---")
        print(f"  mean:  {np.mean(fly):.1f}")
        print(f"  std:   {np.std(fly):.1f}")
        print(f"  min:   {np.min(fly):.1f}")
        print(f"  max:   {np.max(fly):.1f}")

        print(f"\n--- Per-case runtime (s) ---")
        print(f"  mean:  {np.mean(runtime):.2f}")
        print(f"  std:   {np.std(runtime):.2f}")
        print(f"  min:   {np.min(runtime):.2f}")
        print(f"  max:   {np.max(runtime):.2f}")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for run_id, msg, _ in errors:
            print(f"  {run_id}: {msg}")


if __name__ == "__main__":
    main()
