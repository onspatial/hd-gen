#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import gc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from main.python.code.realism.nhts_visualization.viz_common import ensure_dir, savefig, write_summary


def ordered(prefix: str, header: list[str], final_name: str) -> list[str]:
    cols = [c for c in header if c.startswith(prefix) and c != final_name]
    return sorted(cols, key=lambda x: int(x.replace(prefix, "")))


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize person, self, and day replicate weights.")
    ap.add_argument("input", type=Path, help="Path to per50wt.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/per50wt"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    try:
        import polars as pl
    except ImportError as exc:
        raise SystemExit("polars is required for this 838 MB file: pip install polars") from exc

    header = pd.read_csv(args.input, nrows=0).columns.tolist()
    groups = {
        "Person": ("WTPERFIN", ordered("WTPERFIN", header, "WTPERFIN")),
        "Self": ("SFWGT", ordered("SFWGT", header, "SFWGT")),
        "Day": ("DAYWGT", ordered("DAYWGT", header, "DAYWGT")),
    }
    usecols: list[str] = []
    for final_name, reps in groups.values():
        usecols.extend([final_name] + reps)

    # Polars parses this wide file substantially faster and with lower overhead than pandas.
    frame = pl.read_csv(args.input, columns=usecols, infer_schema_length=2000, low_memory=True)
    nrows = frame.height
    final: dict[str, np.ndarray] = {}
    cv: dict[str, np.ndarray] = {}
    rep_mean: dict[str, np.ndarray] = {}
    envelopes: dict[str, np.ndarray] = {}

    for name, (final_col, rep_cols) in groups.items():
        f = frame[final_col].cast(pl.Float64, strict=False).to_numpy()
        r = frame.select([pl.col(c).cast(pl.Float64, strict=False) for c in rep_cols]).to_numpy()
        valid = np.isfinite(f) & (f > 0)
        fv = f[valid]
        rv = r[valid]
        ratio = rv / fv[:, None]
        final[name] = fv
        cv[name] = np.nanstd(ratio, axis=1, ddof=1)
        rep_mean[name] = np.nanmean(rv, axis=0)
        envelopes[name] = ratio[: min(10000, len(ratio))].copy()
        del f, r, fv, rv, ratio
        gc.collect()

    del frame
    gc.collect()
    figures: list[str] = []

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, name in zip(axes, groups):
        vals = final[name]
        bins = np.logspace(np.log10(max(np.nanmin(vals), 0.1)), np.log10(np.nanmax(vals)), 55)
        ax.hist(vals, bins=bins)
        ax.set_xscale("log")
        ax.set_title(name)
        ax.set_xlabel("Final weight, log scale")
        ax.set_ylabel("Persons")
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Final person-related weight distributions")
    savefig(fig, out, "01_final_weight_distributions.png")
    figures.append("01_final_weight_distributions.png")

    fig, ax = plt.subplots(figsize=(11, 5))
    for name in groups:
        x = np.arange(1, len(rep_mean[name]) + 1)
        ax.plot(x, (rep_mean[name] / np.nanmean(final[name]) - 1) * 100, label=name)
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_title("Replicate mean difference from each final-weight mean")
    ax.set_xlabel("Replicate number")
    ax.set_ylabel("Percent difference")
    ax.legend()
    ax.grid(alpha=0.25)
    savefig(fig, out, "02_replicate_mean_stability.png")
    figures.append("02_replicate_mean_stability.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    max_cv = max(np.nanpercentile(cv[k], 99.5) for k in groups)
    bins = np.linspace(0, max_cv, 60)
    for name in groups:
        ax.hist(cv[name], bins=bins, histtype="step", linewidth=1.6, density=True, label=name)
    ax.set_title("Record-level variability across replicate weights")
    ax.set_xlabel("Standard deviation of replicate/final ratios")
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(alpha=0.2)
    savefig(fig, out, "03_replicate_variability.png")
    figures.append("03_replicate_variability.png")

    decile = pd.qcut(final["Person"], 10, duplicates="drop")
    med = pd.DataFrame({"decile": decile, "cv": cv["Person"]}).groupby("decile", observed=True)["cv"].median()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(1, len(med)+1), med.values)
    ax.set_title("Median person-weight replicate variability by final-weight decile")
    ax.set_xlabel("Person final-weight decile, low to high")
    ax.set_ylabel("Median ratio standard deviation")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "04_person_variability_by_decile.png")
    figures.append("04_person_variability_by_decile.png")

    n = min(len(cv["Person"]), len(cv["Day"]))
    rng = np.random.default_rng(42)
    idx = rng.choice(n, size=min(40000, n), replace=False)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(cv["Person"][idx], cv["Day"][idx], s=5, alpha=0.25)
    ax.set_title("Person-weight vs day-weight replicate variability")
    ax.set_xlabel("Person replicate ratio SD")
    ax.set_ylabel("Day replicate ratio SD")
    ax.grid(alpha=0.2)
    savefig(fig, out, "05_person_vs_day_variability.png")
    figures.append("05_person_vs_day_variability.png")

    for i, name in enumerate(groups, start=6):
        sample = envelopes[name]
        q = np.nanpercentile(sample, [5, 25, 50, 75, 95], axis=0)
        x = np.arange(1, sample.shape[1] + 1)
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.fill_between(x, q[0], q[4], alpha=0.2, label="5th-95th percentile")
        ax.fill_between(x, q[1], q[3], alpha=0.35, label="25th-75th percentile")
        ax.plot(x, q[2], linewidth=1.2, label="Median")
        ax.axhline(1, linestyle="--", linewidth=1)
        ax.set_title(f"{name} replicate-to-final ratio envelope")
        ax.set_xlabel("Replicate number")
        ax.set_ylabel("Replicate / final weight")
        ax.legend()
        ax.grid(alpha=0.2)
        filename = f"{i:02d}_{name.lower()}_ratio_envelope.png"
        savefig(fig, out, filename)
        figures.append(filename)

    write_summary(out, "per50wt", nrows, figures, [
        "The file contains three families of final and 100 replicate weights: person, self, and day.",
        "Replicate-weight plots diagnose stability and record-level variation; formal survey variance estimates require the survey's replicate-weight method.",
        "Polars is used to keep this very wide 838 MB CSV fast and memory-efficient.",
    ])


if __name__ == "__main__":
    main()
