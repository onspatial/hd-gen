#!/usr/bin/env python3
"""Compare normalized NHTS and simulation source-destination flow matrices."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from flow_chord_common import COMPARABLE_ORDER, ensure_dir, savefig


def read_matrix(path: Path) -> pd.DataFrame:
    matrix = pd.read_csv(path, index_col=0)
    matrix.index = matrix.index.astype(str)
    matrix.columns = matrix.columns.astype(str)
    matrix = matrix.apply(pd.to_numeric, errors="coerce").fillna(0)
    return matrix.reindex(index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER, fill_value=0)


def heatmap(table: pd.DataFrame, output: Path, title: str, label: str, symmetric: bool = False) -> None:
    values = table.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    if symmetric:
        vmax = max(float(np.nanmax(np.abs(values))), 0.1)
        im = ax.imshow(values, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    else:
        im = ax.imshow(values, cmap="Blues")
    ax.set_xticks(range(len(table.columns)), table.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(table.index)), table.index)
    ax.set_xlabel("Destination")
    ax.set_ylabel("Source")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=label)
    threshold = np.nanmax(np.abs(values)) * 0.55 if np.isfinite(values).any() else 1
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if np.isfinite(values[i, j]):
                color = "white" if abs(values[i, j]) > threshold else "black"
                ax.text(j, i, f"{values[i, j]:+.1f}" if symmetric else f"{values[i, j]:.1f}",
                        ha="center", va="center", fontsize=8, color=color)
    fig.tight_layout()
    savefig(fig, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nhts_matrix", type=Path, help="DAYV2PUB comparable counts CSV")
    parser.add_argument("simulation_matrix", type=Path, help="Simulation comparable counts CSV")
    parser.add_argument("--out", type=Path, default=Path("figs/source_destination_comparison"))
    args = parser.parse_args()
    out = ensure_dir(args.out)

    nhts = read_matrix(args.nhts_matrix)
    simulation = read_matrix(args.simulation_matrix)
    nhts_share = nhts / nhts.to_numpy().sum() * 100
    simulation_share = simulation / simulation.to_numpy().sum() * 100
    all_delta = simulation_share - nhts_share

    nhts_cond = nhts.div(nhts.sum(axis=1).replace(0, np.nan), axis=0) * 100
    sim_cond = simulation.div(simulation.sum(axis=1).replace(0, np.nan), axis=0) * 100
    conditional_delta = sim_cond - nhts_cond

    heatmap(
        all_delta,
        out / "01_simulation_minus_nhts_all_trip_share.png",
        "Simulation minus NHTS flow share",
        "Percentage-point difference",
        symmetric=True,
    )
    heatmap(
        conditional_delta,
        out / "02_simulation_minus_nhts_source_conditional.png",
        "Simulation minus NHTS destination mix within each source",
        "Percentage-point difference",
        symmetric=True,
    )

    differences = []
    for source in COMPARABLE_ORDER:
        for destination in COMPARABLE_ORDER:
            differences.append((f"{source} → {destination}", float(all_delta.loc[source, destination])))
    differences.sort(key=lambda x: x[1])
    extremes = differences[:8] + differences[-8:]
    labels = [x[0] for x in extremes]
    values = [x[1] for x in extremes]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(labels, values)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Simulation minus NHTS share (percentage points)")
    ax.set_title("Most underrepresented and overrepresented simulation flows")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    savefig(fig, out / "03_largest_flow_calibration_gaps.png")

    nhts_dest = nhts_share.sum(axis=0)
    sim_dest = simulation_share.sum(axis=0)
    destination_comparison = pd.DataFrame({"NHTS": nhts_dest, "Simulation": sim_dest})
    x = np.arange(len(destination_comparison))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x - width / 2, destination_comparison["NHTS"], width, label="NHTS")
    ax.bar(x + width / 2, destination_comparison["Simulation"], width, label="Simulation")
    ax.set_xticks(x, destination_comparison.index, rotation=30, ha="right")
    ax.set_ylabel("Share of trip destinations (%)")
    ax.set_title("Destination activity mix: simulation versus NHTS")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    savefig(fig, out / "04_destination_mix_comparison.png")

    # Jensen-Shannon distance for a compact overall distribution mismatch score.
    p = nhts_share.to_numpy(dtype=float).ravel() / 100
    q = simulation_share.to_numpy(dtype=float).ravel() / 100
    midpoint = 0.5 * (p + q)
    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    js_distance = float(np.sqrt(0.5 * kl(p, midpoint) + 0.5 * kl(q, midpoint)))

    all_delta.to_csv(out / "simulation_minus_nhts_all_trip_share_pp.csv")
    conditional_delta.to_csv(out / "simulation_minus_nhts_source_conditional_pp.csv")
    destination_comparison.to_csv(out / "destination_mix_comparison.csv")

    over = max(differences, key=lambda x: x[1])
    under = min(differences, key=lambda x: x[1])
    insights = [
        f"Largest overrepresented simulation flow: {over[0]} at {over[1]:+.2f} percentage points.",
        f"Largest underrepresented simulation flow: {under[0]} at {under[1]:+.2f} percentage points.",
        f"Jensen-Shannon distance across the 36-cell flow distribution is {js_distance:.3f}, where 0 is identical and 1 is maximally different.",
        "Use the source-conditional difference chart to diagnose destination choice after controlling for how often each source activity occurs.",
        "A flow-share match does not establish a travel-time or distance match; those should remain separate calibration targets.",
    ]
    (out / "INSIGHTS.txt").write_text("\n".join(f"- {x}" for x in insights) + "\n", encoding="utf-8")
    (out / "comparison_summary.json").write_text(json.dumps({
        "nhts_matrix": str(args.nhts_matrix),
        "simulation_matrix": str(args.simulation_matrix),
        "jensen_shannon_distance": js_distance,
        "largest_overrepresented_flow": {"flow": over[0], "percentage_points": over[1]},
        "largest_underrepresented_flow": {"flow": under[0], "percentage_points": under[1]},
        "insights": insights,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote comparison products to {out}")


if __name__ == "__main__":
    main()
