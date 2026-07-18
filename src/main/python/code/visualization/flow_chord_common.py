#!/usr/bin/env python3
"""Shared plotting utilities for directed source-destination chord diagrams.

The chord renderer is intentionally dependency-light: pandas, numpy, and
matplotlib only. Ribbons are colored by source, and a small arrow marker at the
receiving arc indicates the destination.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Sequence
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Polygon, Wedge
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 190,
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.labelsize": 10,
})

COMPARABLE_ORDER = ["Home", "Work", "Restaurant", "Recreation"]
COMPARABLE_COLORS = {
    "Home": "#1f77b4",
    "Work": "#f2a65a",
    "School": "#8c564b",
    "Restaurant": "#d62728",
    "Recreation": "#e78ac3",
    "Other": "#8bd3dd",
}

DETAILED_ORDER = [
    "Home", "Work", "Restaurant", "Recreation", "School", "Medical", "Shopping", 
    "Personal business", "Escort",  "Other",
]
DETAILED_COLORS = {
    "Home": "#1f77b4",
    "Work": "#f2a65a",
    "School": "#8c564b",
    "Medical": "#9467bd",
    "Shopping": "#bcbd22",
    "Recreation": "#e78ac3",
    "Personal business": "#7f7f7f",
    "Escort": "#ff9896",
    "Restaurant": "#d62728",
    "Other": "#8bd3dd",
}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def savefig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _polar(theta: float, radius: float) -> tuple[float, float]:
    return radius * math.cos(theta), radius * math.sin(theta)


def _ribbon_path(
    source: tuple[float, float],
    destination: tuple[float, float],
    radius: float = 0.875,
    control_radius: float = 0.20,
    arc_points: int = 12,
) -> MplPath:
    """Create a smooth closed ribbon from two clockwise angular intervals."""
    s0, s1 = source
    d0, d1 = destination
    sa = np.linspace(s0, s1, max(3, arc_points))
    da = np.linspace(d0, d1, max(3, arc_points))

    vertices: list[tuple[float, float]] = []
    codes: list[int] = []

    vertices.append(_polar(float(sa[0]), radius)); codes.append(MplPath.MOVETO)
    for a in sa[1:]:
        vertices.append(_polar(float(a), radius)); codes.append(MplPath.LINETO)

    vertices.extend([
        _polar(s1, control_radius),
        _polar(d0, control_radius),
        _polar(d0, radius),
    ])
    codes.extend([MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])

    for a in da[1:]:
        vertices.append(_polar(float(a), radius)); codes.append(MplPath.LINETO)

    vertices.extend([
        _polar(d1, control_radius),
        _polar(s0, control_radius),
        _polar(s0, radius),
    ])
    codes.extend([MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])

    vertices.append((0.0, 0.0)); codes.append(MplPath.CLOSEPOLY)
    return MplPath(vertices, codes)


def plot_directed_chord(
    matrix: pd.DataFrame,
    output: Path,
    title: str,
    colors: Mapping[str, str],
    fixed_sectors: bool = False,
    min_flow_share_pct: float = 0.0,
    subtitle: str | None = None,
    center_unit: str = "trips",
) -> None:
    """Plot a directed chord diagram.

    Parameters
    ----------
    matrix:
        Square source-by-destination flow matrix.
    fixed_sectors:
        If True, every category receives an equal angular sector and flow uses
        a common angular scale. Empty categories remain visible, which makes
        diagrams from different datasets directly comparable.
    min_flow_share_pct:
        Flows below this percent of the total are omitted to reduce clutter.
    """
    labels = list(matrix.index.astype(str))
    m = matrix.reindex(index=labels, columns=labels, fill_value=0).to_numpy(dtype=float, copy=True)
    m[~np.isfinite(m)] = 0
    m[m < 0] = 0
    total = float(m.sum())
    if total <= 0:
        raise ValueError("Flow matrix has no positive values")

    threshold = total * max(min_flow_share_pct, 0.0) / 100.0
    shown = m.copy()
    if threshold > 0:
        shown[shown < threshold] = 0
        if shown.sum() <= 0:
            shown = m.copy()

    outgoing = shown.sum(axis=1)
    incoming = shown.sum(axis=0)
    touch = outgoing + incoming
    n = len(labels)
    gap = math.radians(3.0 if n <= 7 else 2.0)
    start_angle = math.radians(82)

    sector_bounds: list[tuple[float, float]] = []
    used_bounds: list[tuple[float, float]] = []
    flow_scale: float

    if fixed_sectors:
        sector_span = (2 * math.pi - n * gap) / n
        max_touch = max(float(touch.max()), 1.0)
        flow_scale = sector_span * 0.88 / max_touch
        cursor = start_angle
        for i in range(n):
            sector_start = cursor
            sector_end = cursor - sector_span
            sector_bounds.append((sector_start, sector_end))
            used_span = float(touch[i]) * flow_scale
            mid = (sector_start + sector_end) / 2
            used_bounds.append((mid + used_span / 2, mid - used_span / 2))
            cursor = sector_end - gap
    else:
        available = 2 * math.pi - n * gap
        total_touch = max(float(touch.sum()), 1.0)
        flow_scale = available / total_touch
        cursor = start_angle
        for i in range(n):
            span = float(touch[i]) * flow_scale
            sector_start = cursor
            sector_end = cursor - span
            sector_bounds.append((sector_start, sector_end))
            used_bounds.append((sector_start, sector_end))
            cursor = sector_end - gap

    source_segments: dict[tuple[int, int], tuple[float, float]] = {}
    destination_segments: dict[tuple[int, int], tuple[float, float]] = {}
    for group in range(n):
        cursor = used_bounds[group][0]
        for destination in range(n):
            width = float(shown[group, destination]) * flow_scale
            if width > 0:
                source_segments[(group, destination)] = (cursor, cursor - width)
                cursor -= width
        for source in range(n):
            width = float(shown[source, group]) * flow_scale
            if width > 0:
                destination_segments[(source, group)] = (cursor, cursor - width)
                cursor -= width

    fig, ax = plt.subplots(figsize=(10.5, 10.5))
    ax.set_aspect("equal")
    ax.axis("off")

    # Draw ribbons largest first so smaller flows remain visible on top.
    flows = [
        (float(shown[i, j]), i, j)
        for i in range(n) for j in range(n) if shown[i, j] > 0
    ]
    for value, i, j in sorted(flows, reverse=True):
        source = source_segments[(i, j)]
        destination = destination_segments[(i, j)]
        color = colors.get(labels[i], "#777777")
        patch = PathPatch(
            _ribbon_path(source, destination),
            facecolor=color,
            edgecolor=color,
            linewidth=0.35,
            alpha=0.48,
            zorder=1,
        )
        ax.add_patch(patch)

        # Arrow marker at the destination end for flows large enough to see.
        if value / total >= 0.006:
            dmid = (destination[0] + destination[1]) / 2
            half = min(abs(destination[0] - destination[1]) * 0.28, 0.020)
            triangle = Polygon(
                [
                    _polar(dmid, 0.905),
                    _polar(dmid - half, 0.825),
                    _polar(dmid + half, 0.825),
                ],
                closed=True,
                facecolor=color,
                edgecolor="none",
                alpha=0.78,
                zorder=2,
            )
            ax.add_patch(triangle)

    # Outer category sectors and active arc portions.
    for i, label in enumerate(labels):
        color = colors.get(label, "#777777")
        s0, s1 = sector_bounds[i]
        u0, u1 = used_bounds[i]
        # Faint full sector keeps zero-volume categories visible in fixed mode.
        if fixed_sectors:
            ax.add_patch(Wedge(
                (0, 0), 1.0, math.degrees(s1), math.degrees(s0), width=0.075,
                facecolor=color, edgecolor=color, linewidth=0.9, alpha=0.18, zorder=3,
            ))
        if touch[i] > 0:
            ax.add_patch(Wedge(
                (0, 0), 1.0, math.degrees(u1), math.degrees(u0), width=0.085,
                facecolor=color, edgecolor="#333333", linewidth=0.55, alpha=0.95, zorder=4,
            ))

        midpoint = (s0 + s1) / 2
        x, y = _polar(midpoint, 1.105)
        angle = math.degrees(midpoint) % 360
        rotation = ((angle - 90 + 180) % 360) - 180
        if rotation > 90:
            rotation -= 180
        elif rotation < -90:
            rotation += 180
        ha = "left" if x >= 0 else "right"
        touch_share = touch[i] / max(touch.sum(), 1.0) * 100
        label_text = f"{label.replace(' ', '\n')}\n{touch_share:.1f}%"
        ax.text(
            x, y, label_text, rotation=rotation, rotation_mode="anchor",
            ha="center", va="center", fontsize=18, color="#111111", zorder=5,
        )

    def compact_number(value: float) -> str:
        for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(value) >= divisor:
                return f"{value / divisor:.2f}".rstrip("0").rstrip(".") + suffix
        return f"{value:,.0f}"

    ax.text(0, 0.075, compact_number(total), ha="center", va="center", fontsize=22, weight="bold")
    ax.text(0, -0.025, center_unit,
            ha="center", va="center", fontsize=18, color="#555555")
    # ax.text(0, -0.105, "Ribbon color = source\nArrowhead = destination",
            # ha="center", va="center", fontsize=8.5, color="#555555")

    fig.suptitle(title, y=0.975, fontsize=16, weight="bold")
    if subtitle:
        fig.text(0.5, 0.935, subtitle, ha="center", va="top", fontsize=9.5, color="#555555")
    ax.set_xlim(-1.38, 1.38)
    ax.set_ylim(-1.35, 1.35)
    savefig(fig, output)


def plot_row_percent_heatmap(matrix: pd.DataFrame, output: Path, title: str) -> None:
    row_pct = matrix.div(matrix.sum(axis=1).replace(0, np.nan), axis=0) * 100
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    values = row_pct.to_numpy(dtype=float)
    im = ax.imshow(values, cmap="Blues", vmin=0, vmax=np.nanpercentile(values, 95) if np.isfinite(values).any() else 1)
    ax.set_xticks(range(len(row_pct.columns)), row_pct.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(row_pct.index)), row_pct.index)
    ax.set_xlabel("Destination")
    ax.set_ylabel("Source")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Percent of trips leaving source")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if np.isfinite(values[i, j]):
                color = "white" if values[i, j] > np.nanmax(values) * 0.55 else "black"
                ax.text(j, i, f"{values[i, j]:.1f}", ha="center", va="center", fontsize=8, color=color)
    fig.tight_layout()
    savefig(fig, output)


def plot_top_flows(matrix: pd.DataFrame, output: Path, title: str, top_n: int = 15) -> None:
    total = float(matrix.to_numpy().sum())
    rows = []
    for source in matrix.index:
        for destination in matrix.columns:
            value = float(matrix.loc[source, destination])
            if value > 0:
                rows.append((f"{source} → {destination}", value, value / total * 100 if total else 0))
    rows.sort(key=lambda x: x[1], reverse=True)
    rows = rows[:top_n]
    labels = [r[0] for r in rows][::-1]
    shares = [r[2] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(10, max(5.5, 0.38 * len(rows) + 1.5)))
    ax.barh(labels, shares)
    ax.set_xlabel("Share of all trips (%)")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    for y, value in enumerate(shares):
        ax.text(value, y, f" {value:.1f}%", va="center", fontsize=8)
    fig.tight_layout()
    savefig(fig, output)


def plot_entry_exit_balance(matrix: pd.DataFrame, output: Path, title: str) -> None:
    total = float(matrix.to_numpy().sum())
    source_share = matrix.sum(axis=1) / total * 100 if total else matrix.sum(axis=1)
    destination_share = matrix.sum(axis=0) / total * 100 if total else matrix.sum(axis=0)
    balance = destination_share.reindex(matrix.index, fill_value=0) - source_share
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.barh(balance.index, balance.values)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Destination share minus source share (percentage points)")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    savefig(fig, output)


def matrix_insights(matrix: pd.DataFrame, label: str, rate_denominator: float | None = None) -> list[str]:
    total = float(matrix.to_numpy().sum())
    if total <= 0:
        return [f"{label}: no positive flows were found."]
    entries: list[tuple[str, str, float]] = []
    for source in matrix.index:
        for destination in matrix.columns:
            value = float(matrix.loc[source, destination])
            if value > 0:
                entries.append((str(source), str(destination), value))
    entries.sort(key=lambda x: x[2], reverse=True)
    top_source, top_destination, top_value = entries[0]
    home_based = 0.0
    if "Home" in matrix.index:
        home_based = float(matrix.loc["Home"].sum() + matrix["Home"].sum() - matrix.loc["Home", "Home"])
    non_home = total - home_based
    same = float(np.trace(matrix.to_numpy(dtype=float)))
    source_share = matrix.sum(axis=1) / total * 100
    destination_share = matrix.sum(axis=0) / total * 100
    imbalance = (destination_share.reindex(matrix.index) - source_share).abs().sort_values(ascending=False)

    lines = [
        f"{label}: {total:,.1f} total flow units were analyzed.",
        f"Largest flow: {top_source} → {top_destination}, {top_value / total * 100:.2f}% of all trips.",
        f"Trips touching Home: {home_based / total * 100:.2f}%; non-home-to-non-home trips: {non_home / total * 100:.2f}%.",
        f"Same-category trips: {same / total * 100:.2f}% of all trips.",
        f"Largest source/destination marginal imbalance: {imbalance.index[0]} at {imbalance.iloc[0]:.2f} percentage points.",
    ]
    if rate_denominator and rate_denominator > 0:
        lines.append(f"Overall rate: {total / rate_denominator:.3f} trips per agent-day.")
    return lines


def write_summary(path: Path, metadata: Mapping[str, object], insights: Sequence[str]) -> None:
    payload = {"metadata": dict(metadata), "insights": list(insights)}
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def write_matrix_products(matrix: pd.DataFrame, out: Path, stem: str) -> None:
    matrix.to_csv(out / f"{stem}_counts.csv")
    total = matrix.to_numpy(dtype=float).sum()
    (matrix / total * 100 if total else matrix).to_csv(out / f"{stem}_all_trip_share_pct.csv")
    matrix.div(matrix.sum(axis=1).replace(0, np.nan), axis=0).mul(100).to_csv(
        out / f"{stem}_source_conditional_pct.csv"
    )
