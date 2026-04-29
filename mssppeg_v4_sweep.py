#!/usr/bin/env python3
"""
MSSPPEG v4 — Parallel parameter sweep across 72 configurations.

Imports from mssppeg_v4_physics.py and runs a multiprocessing sweep.
All results logged incrementally to CSV; 4 PNG plots generated post-run.
"""

import os
import csv
import time
import multiprocessing
from itertools import product
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mssppeg_v4_physics import build_array, make_deriv, total_mech_energy, run_one

# ==================== CONFIGS ====================
SPACINGS = ["25cm", "50cm"]
ARM_MODES = ["upper_double", "lower_double"]
HINGE_CWS = [5, 10, 15]
TIP_CWS = [1, 2, 3]
MAIN_CLUTCHES = ["oneway", "rectifier"]
HINGE_CLUTCHES = ["oneway"]
V_WINDS = [6.0]

CASES = list(product(SPACINGS, ARM_MODES, HINGE_CWS, TIP_CWS,
                     MAIN_CLUTCHES, HINGE_CLUTCHES, V_WINDS))
TOTAL_CASES = len(CASES)

CSV_PATH = "/root/.openclaw/workspace/mssppeg_v4_sweep.csv"
PLOT_DIR = "/root/.openclaw/workspace"

# CSV columns
CSV_HEADER = [
    "run_id", "spacing", "arm_mode", "hinge_cw", "tip_cw",
    "main_clutch", "hinge_clutch", "v_wind", "t_stop",
    "E_init_j", "elec_total", "main_gen_j", "hinge1_j", "hinge2_j",
    "fric_j", "aero_j", "main_clutch_j", "hinge_clutch_plus_genheat_j",
    "peak_shaft_rpm", "peak_fly_rpm", "final_residual_j", "runtime_s",
]

# ==================== WORKER ====================
csv_lock = multiprocessing.Lock()

def worker(args_tuple):
    idx, cfg = args_tuple
    run_id = (
        f"{cfg['spacing']}_{cfg['arm_mode']}_hc{cfg['hinge_cw']}_tc{cfg['tip_cw']}_"
        f"{cfg['main_clutch']}_{cfg['hinge_clutch']}_vw{cfg['v_wind']}"
    )
    t_start = time.time()
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
    except Exception as e:
        print(f"[ERROR] Case {run_id} failed: {e}")
        row = {
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
            "runtime_s": time.time() - t_start,
        }

    # Incremental write with lock
    with csv_lock:
        file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
        with open(CSV_PATH, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    return idx, run_id, row["elec_total"], row["runtime_s"], row.get("error", None) is not None


# ==================== PROGRESS ====================
def log_progress(result_queue, total, t0):
    completed = 0
    while completed < total:
        idx, run_id, elec, runtime, failed = result_queue.get()
        completed += 1
        if completed % 10 == 0 or completed == total:
            elapsed = time.time() - t0
            avg_per_case = elapsed / completed
            eta = avg_per_case * (total - completed)
            print(f"Completed {completed} / {total} cases  |  ETA: {timedelta(seconds=int(eta))}")


# ==================== MAIN ====================
def main():
    # Build config list
    configs = []
    for spacing, arm_mode, hinge_cw, tip_cw, main_clutch, hinge_clutch, v_wind in CASES:
        configs.append({
            "spacing": spacing,
            "arm_mode": arm_mode,
            "hinge_cw": hinge_cw,
            "tip_cw": tip_cw,
            "main_clutch": main_clutch,
            "hinge_clutch": hinge_clutch,
            "v_wind": v_wind,
        })

    # Remove old CSV if present
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)

    print(f"Starting sweep: {TOTAL_CASES} cases")
    print(f"CSV output: {CSV_PATH}")
    print(f"Plots output: {PLOT_DIR}")
    t0 = time.time()

    # Use pool with initializer to share lock
    def init_worker(lock):
        global csv_lock
        csv_lock = lock

    lock = multiprocessing.Lock()
    with multiprocessing.Pool(processes=min(8, multiprocessing.cpu_count()),
                              initializer=init_worker, initargs=(lock,)) as pool:
        results = pool.map(worker, enumerate(configs))

    elapsed = time.time() - t0
    print(f"\nSweep complete in {timedelta(seconds=int(elapsed))}")

    # ==================== POST-PROCESSING ====================
    import pandas as pd
    df = pd.read_csv(CSV_PATH)
    print(f"\nLoaded {len(df)} rows from CSV")

    # Best case by elec_total for each (main_clutch, v_wind)
    print("\n=== Best case by (main_clutch, v_wind) ===")
    for (mc, vw), group in df.groupby(["main_clutch", "v_wind"]):
        best = group.loc[group["elec_total"].idxmax()]
        print(f"  main_clutch={mc}  v_wind={vw}  ->  run_id={best['run_id']}  elec_total={best['elec_total']:.2f} J")

    # Rectifier improvement % over oneway per wind speed
    print("\n=== Rectifier improvement over oneway per v_wind ===")
    for vw, group in df.groupby("v_wind"):
        oneway = group[group["main_clutch"] == "oneway"]["elec_total"].mean()
        rect = group[group["main_clutch"] == "rectifier"]["elec_total"].mean()
        if oneway > 0:
            imp = (rect / oneway - 1) * 100
            print(f"  v_wind={vw}  oneway_avg={oneway:.2f} J  rectifier_avg={rect:.2f} J  improvement={imp:+.1f}%")
        else:
            print(f"  v_wind={vw}  oneway_avg=0.0  rectifier_avg={rect:.2f} J  (baseline zero)")

    # ==================== PLOTS ====================
    print("\nGenerating plots...")

    # 1. Bar chart: elec_total vs arm_mode/spacing (grouped by main_clutch)
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot = df.groupby(["main_clutch", "arm_mode", "spacing"])["elec_total"].mean().unstack(level=0)
    pivot.plot(kind="bar", ax=ax, color=["steelblue", "coral"])
    ax.set_title("Mean elec_total by arm_mode / spacing (grouped by main_clutch)")
    ax.set_ylabel("Electrical Energy (J)")
    ax.set_xlabel("(arm_mode, spacing)")
    ax.legend(title="main_clutch")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "mssppeg_v4_plot_bar.png"), dpi=150)
    plt.close()
    print("  Saved: mssppeg_v4_plot_bar.png")

    # 2. Scatter: peak_shaft_rpm vs peak_fly_rpm (colored by elec_total)
    fig, ax = plt.subplots(figsize=(8, 8))
    sc = ax.scatter(df["peak_shaft_rpm"], df["peak_fly_rpm"],
                    c=df["elec_total"], cmap="viridis", s=80, edgecolors="k", linewidths=0.3)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("elec_total (J)")
    ax.set_xlabel("Peak Shaft RPM")
    ax.set_ylabel("Peak Flywheel RPM")
    ax.set_title("Peak Shaft vs Flywheel RPM (colored by elec_total)")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "mssppeg_v4_plot_scatter.png"), dpi=150)
    plt.close()
    print("  Saved: mssppeg_v4_plot_scatter.png")

    # 3. Residual histogram: final_residual_j distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df["final_residual_j"].dropna(), bins=20, color="steelblue", edgecolor="black")
    ax.set_title("Distribution of final_residual_j")
    ax.set_xlabel("Final Residual (J)")
    ax.set_ylabel("Count")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "mssppeg_v4_plot_residual_hist.png"), dpi=150)
    plt.close()
    print("  Saved: mssppeg_v4_plot_residual_hist.png")

    # 4. Heatmap: elec_total vs hinge_cw × tip_cw (best config only)
    # "best config" = highest elec_total overall
    best_idx = df["elec_total"].idxmax()
    best_cfg = df.loc[best_idx]
    # Filter rows matching the best case's spacing, arm_mode, main_clutch, hinge_clutch, v_wind
    filtered = df[
        (df["spacing"] == best_cfg["spacing"]) &
        (df["arm_mode"] == best_cfg["arm_mode"]) &
        (df["main_clutch"] == best_cfg["main_clutch"]) &
        (df["hinge_clutch"] == best_cfg["hinge_clutch"]) &
        (df["v_wind"] == best_cfg["v_wind"])
    ]
    pivot_hm = filtered.pivot_table(index="hinge_cw", columns="tip_cw",
                                    values="elec_total", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(pivot_hm.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(np.arange(len(pivot_hm.columns)))
    ax.set_yticks(np.arange(len(pivot_hm.index)))
    ax.set_xticklabels(pivot_hm.columns)
    ax.set_yticklabels(pivot_hm.index)
    ax.set_xlabel("tip_cw")
    ax.set_ylabel("hinge_cw")
    ax.set_title(f"elec_total heatmap (best config: {best_cfg['run_id']})")
    # Annotate cells
    for i in range(len(pivot_hm.index)):
        for j in range(len(pivot_hm.columns)):
            val = pivot_hm.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", color="black", fontsize=9)
    cb = plt.colorbar(im, ax=ax)
    cb.set_label("elec_total (J)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "mssppeg_v4_plot_heatmap.png"), dpi=150)
    plt.close()
    print("  Saved: mssppeg_v4_plot_heatmap.png")

    print("\nAll done.")

if __name__ == "__main__":
    main()
