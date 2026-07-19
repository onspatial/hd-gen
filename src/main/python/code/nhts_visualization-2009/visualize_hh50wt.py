#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import ensure_dir, savefig, write_summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize 100 household replicate weights.")
    ap.add_argument("input", type=Path, help="Path to hh50wt.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/hh50wt"))
    ap.add_argument("--chunksize", type=int, default=20000)
    args = ap.parse_args()
    out = ensure_dir(args.out)

    header = pd.read_csv(args.input, nrows=0).columns.tolist()
    reps = [c for c in header if c.startswith("HHWGT") and c != "HHWGT"]
    reps = sorted(reps, key=lambda x: int(x.replace("HHWGT", "")))
    usecols = ["HOUSEID", "HHWGT"] + reps

    finals, cvs, ratio_lo, ratio_hi = [], [], [], []
    rep_sum = np.zeros(len(reps), dtype=float)
    rep_sumsq = np.zeros(len(reps), dtype=float)
    rep_count = np.zeros(len(reps), dtype=float)
    ratio_samples = []
    nrows = 0

    for chunk in pd.read_csv(args.input, usecols=usecols, chunksize=args.chunksize, low_memory=False):
        final = pd.to_numeric(chunk["HHWGT"], errors="coerce").to_numpy(float)
        r = chunk[reps].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        valid = np.isfinite(final) & (final > 0)
        final = final[valid]
        r = r[valid]
        ratio = r / final[:, None]
        finals.append(final)
        cvs.append(np.nanstd(ratio, axis=1, ddof=1))
        ratio_lo.append(np.nanpercentile(ratio, 5, axis=1))
        ratio_hi.append(np.nanpercentile(ratio, 95, axis=1))
        rep_sum += np.nansum(r, axis=0)
        rep_sumsq += np.nansum(r * r, axis=0)
        rep_count += np.sum(np.isfinite(r), axis=0)
        if sum(len(x) for x in ratio_samples) < 20000:
            take = min(2000, len(ratio))
            if take:
                ratio_samples.append(ratio[:take])
        nrows += len(chunk)

    final = np.concatenate(finals)
    cv = np.concatenate(cvs)
    lo = np.concatenate(ratio_lo)
    hi = np.concatenate(ratio_hi)
    rep_mean = rep_sum / rep_count
    final_mean = np.nanmean(final)
    figures: list[str] = []

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(final, bins=np.logspace(np.log10(max(final.min(), 0.1)), np.log10(final.max()), 60))
    ax.set_xscale("log")
   #  ax.set_title("Distribution of final household weights")
    ax.set_xlabel("HHWGT, log scale")
    ax.set_ylabel("Households")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "01_final_weight_distribution.png")
    figures.append("01_final_weight_distribution.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    mean_ratio = rep_mean / final_mean
    max_diff_pct = np.max(np.abs(mean_ratio - 1)) * 100
    ax.plot(np.arange(1, len(reps)+1), mean_ratio, marker="o", markersize=3)
    ax.axhline(1, linestyle="--", linewidth=1)
    ax.set_ylim(0.9995, 1.0005)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
   #  ax.set_title("Household replicate means are calibrated to the final-weight mean")
    ax.set_xlabel("Replicate number")
    ax.set_ylabel("Mean replicate / mean final")
    ax.text(0.01, 0.06, f"Maximum absolute difference: {max_diff_pct:.2e}%", transform=ax.transAxes)
    ax.grid(alpha=0.25)
    savefig(fig, out, "02_replicate_mean_stability.png")
    figures.append("02_replicate_mean_stability.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(cv[np.isfinite(cv)], bins=50)
   #  ax.set_title("Household-level variability across replicate weights")
    ax.set_xlabel("Standard deviation of replicate/final ratios")
    ax.set_ylabel("Households")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "03_household_replicate_cv.png")
    figures.append("03_household_replicate_cv.png")

    decile = pd.qcut(final, 10, duplicates="drop")
    med = pd.DataFrame({"decile": decile, "cv": cv}).groupby("decile", observed=True)["cv"].median()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(1, len(med)+1), med.values)
   #  ax.set_title("Median replicate variability by final-weight decile")
    ax.set_xlabel("Final household-weight decile, low to high")
    ax.set_ylabel("Median ratio standard deviation")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "04_variability_by_weight_decile.png")
    figures.append("04_variability_by_weight_decile.png")

    rng = np.random.default_rng(42)
    idx = rng.choice(len(final), size=min(30000, len(final)), replace=False)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(final[idx], cv[idx], s=5, alpha=0.25)
    ax.set_xscale("log")
   #  ax.set_title("Final household weight vs replicate variability")
    ax.set_xlabel("Final weight, log scale")
    ax.set_ylabel("Replicate/final ratio standard deviation")
    ax.grid(alpha=0.2)
    savefig(fig, out, "05_weight_vs_variability.png")
    figures.append("05_weight_vs_variability.png")

    widths = hi - lo
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(widths[np.isfinite(widths)], bins=50)
   #  ax.set_title("Width of each household's 5th-95th percentile replicate range")
    ax.set_xlabel("95th minus 5th percentile of replicate/final ratio")
    ax.set_ylabel("Households")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "06_replicate_ratio_range.png")
    figures.append("06_replicate_ratio_range.png")

    rs = np.vstack(ratio_samples) if ratio_samples else np.empty((0, len(reps)))
    if len(rs):
        q = np.nanpercentile(rs, [5, 25, 50, 75, 95], axis=0)
        x = np.arange(1, len(reps)+1)
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.fill_between(x, q[0], q[4], alpha=0.2, label="5th-95th percentile")
        ax.fill_between(x, q[1], q[3], alpha=0.35, label="25th-75th percentile")
        ax.plot(x, q[2], linewidth=1.2, label="Median")
        ax.axhline(1, linestyle="--", linewidth=1)
       #  ax.set_title("Replicate-to-final ratio envelope across sampled households")
        ax.set_xlabel("Replicate number")
        ax.set_ylabel("Replicate / final weight")
        ax.legend()
        ax.grid(alpha=0.2)
        savefig(fig, out, "07_replicate_ratio_envelope.png")
        figures.append("07_replicate_ratio_envelope.png")

    write_summary(out, "hh50wt", nrows, figures, [
        f"Detected {len(reps)} replicate-weight columns.",
        "Plots focus on stability and household-level variability; replicate weights are intended for variance estimation.",
    ])


if __name__ == "__main__":
    main()
