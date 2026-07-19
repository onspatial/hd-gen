#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import (
    MODE_GROUPS, MODE_LABELS, barh, code_to_label, ensure_dir, heatmap, numeric,
    parse_hhmm, positive_weight, savefig, weighted_counts, weighted_crosstab,
    weighted_mean_by, write_summary,
)

ANCHOR = {"H": "Home", "W": "Work", "O": "Other"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS tour-level file TOUR09.")
    ap.add_argument("input", type=Path, help="Path to tour09.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/tour09"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    df = pd.read_csv(args.input, low_memory=False)
    df["weight"] = positive_weight(df["WTTRDFIN"])
    tt = df["TOURTYPE"].astype("string").str.strip()
    df["tour_type"] = tt.str[0].map(ANCHOR).fillna("Unknown") + " to " + tt.str[-1].map(ANCHOR).fillna("Unknown")
    df["origin"] = tt.str[0].map(ANCHOR).fillna("Unknown")
    df["destination"] = tt.str[-1].map(ANCHOR).fillna("Unknown")
    df["mode"] = code_to_label(df["MODE_D"], MODE_LABELS)
    df["mode_group"] = numeric(df["MODE_D"]).map(MODE_GROUPS).fillna("Unknown")
    figures: list[str] = []

    order = ["Home", "Work", "Other"]
    od = weighted_crosstab(df["origin"], df["destination"], df["weight"], normalize="all")
    od = od.reindex(index=order, columns=order)
    heatmap(od, "Where tours start and end", out, "01_tour_anchor_flow.png",
            "Destination anchor", "Origin anchor", fmt=".1f")
    figures.append("01_tour_anchor_flow.png")

    tour_counts = weighted_counts(df["tour_type"], df["weight"], drop_unknown=True)
    barh(tour_counts, "Tour type share", "Percent of weighted tours", out,
         "02_tour_type_share.png", percent=True)
    figures.append("02_tour_type_share.png")

    # Time-of-day start pattern by tour type.
    df["start_hour"] = np.floor(parse_hhmm(df["BEGNTIME"]) % 24)
    d = df[df["start_hour"].between(0, 23) & (df["tour_type"] != "Unknown to Unknown")].copy()
    start = d.pivot_table(index="tour_type", columns="start_hour", values="weight", aggfunc="sum", fill_value=0)
    start = start.div(start.sum(axis=1), axis=0) * 100
    heatmap(start, "When tours begin within each tour type", out, "03_start_time_by_tour_type.png",
            "Hour of day", "Tour type", fmt=".0f", annotate=False)
    figures.append("03_start_time_by_tour_type.png")

    mode_counts = weighted_counts(df["mode"], df["weight"], drop_unknown=True)
    barh(mode_counts, "Mode of the longest-distance tour segment", "Percent of weighted tours", out,
         "04_longest_segment_mode.png", top=18, percent=True)
    figures.append("04_longest_segment_mode.png")

    # Average distance and travel time by tour type.
    df["TOT_MILS"] = numeric(df["TOT_MILS"])
    df["TOT_CMIN"] = numeric(df["TOT_CMIN"])
    valid = df[df["TOT_MILS"].between(0, 1000) & df["TOT_CMIN"].between(0, 1440)].copy()
    md = weighted_mean_by(valid, "tour_type", "TOT_MILS", "weight")
    mt = weighted_mean_by(valid, "tour_type", "TOT_CMIN", "weight")
    avg = pd.concat([md.rename("Miles"), mt.rename("Minutes")], axis=1).dropna().sort_index()
    x = np.arange(len(avg))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x - 0.2, avg["Miles"], 0.4, label="Average miles")
    ax.bar(x + 0.2, avg["Minutes"], 0.4, label="Average travel minutes")
    ax.set_xticks(x, avg.index, rotation=35, ha="right")
   #  ax.set_title("Tour distance and travel time by tour type")
    ax.set_ylabel("Weighted mean")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "05_distance_time_by_tour_type.png")
    figures.append("05_distance_time_by_tour_type.png")

    # Distance-duration relationship.
    d = valid[valid["TOT_MILS"].between(0.1, 250) & valid["TOT_CMIN"].between(1, 600)]
    if len(d) > 150000:
        d = d.sample(150000, random_state=42)
    fig, ax = plt.subplots(figsize=(8.5, 6))
    hb = ax.hexbin(d["TOT_MILS"], d["TOT_CMIN"], gridsize=50, bins="log", mincnt=1, cmap="viridis")
   #  ax.set_title("Tour distance and travel time")
    ax.set_xlabel("Total tour miles")
    ax.set_ylabel("Total travel minutes")
    fig.colorbar(hb, ax=ax, label="log10 observations")
    savefig(fig, out, "06_distance_vs_time.png")
    figures.append("06_distance_vs_time.png")

    # Complexity: stops and trip burden.
    df["STOPS"] = numeric(df["STOPS"])
    stop_group = df["STOPS"].clip(upper=5).astype("Int64").astype("string").replace("5", "5+")
    df["stop_group"] = stop_group
    stop_dist = weighted_mean_by(valid.assign(stop_group=stop_group), "stop_group", "TOT_MILS", "weight")
    stop_time = weighted_mean_by(valid.assign(stop_group=stop_group), "stop_group", "TOT_CMIN", "weight")
    complexity = pd.concat([stop_dist.rename("Miles"), stop_time.rename("Minutes")], axis=1).dropna()
    desired = ["0", "1", "2", "3", "4", "5+"]
    complexity = complexity.reindex([x for x in desired if x in complexity.index])
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(complexity.index, complexity["Miles"], marker="o", label="Miles")
    ax.plot(complexity.index, complexity["Minutes"], marker="o", label="Travel minutes")
   #  ax.set_title("Tour burden increases with intermediate stops")
    ax.set_xlabel("Stops")
    ax.set_ylabel("Weighted mean")
    ax.legend()
    ax.grid(alpha=0.25)
    savefig(fig, out, "07_distance_time_by_stops.png")
    figures.append("07_distance_time_by_stops.png")

    # Passenger-miles composition by tour type.
    pmt_cols = ["PMT_POV", "PMT_TRAN", "PMT_WALK", "PMT_OTHR"]
    pmt_labels = ["Private vehicle", "Transit", "Walk", "Other"]
    d = df[["tour_type", "weight"] + pmt_cols].copy()
    for c in pmt_cols:
        d[c] = numeric(d[c]).where(lambda x: x >= 0, 0)
    rows = []
    for name, g in d.groupby("tour_type"):
        total = np.array([(g[c] * g["weight"]).sum() for c in pmt_cols], dtype=float)
        if total.sum() > 0:
            rows.append(pd.Series(total / total.sum() * 100, index=pmt_labels, name=name))
    pmt = pd.DataFrame(rows).sort_index()
    heatmap(pmt, "Passenger-mile composition within tour types", out, "08_pmt_composition.png",
            "Mode category", "Tour type", fmt=".0f")
    figures.append("08_pmt_composition.png")

    # Dwell time by tour type.
    df["TOT_DWEL2"] = numeric(df["TOT_DWEL2"])
    dwell = weighted_mean_by(df[df["TOT_DWEL2"].between(0, 1440)], "tour_type", "TOT_DWEL2", "weight")
    barh(dwell, "Average total dwell time by tour type", "Weighted mean minutes", out,
         "09_dwell_time_by_tour_type.png")
    figures.append("09_dwell_time_by_tour_type.png")

    # Number of tours per person.
    per = df.groupby(["HOUSEID", "PERSONID"]).size().clip(upper=8).astype(str).replace("8", "8+").value_counts()
    barh(per, "Number of tours per person in the travel day", "Persons in sample", out,
         "10_tours_per_person.png")
    figures.append("10_tours_per_person.png")

    write_summary(out, "TOUR09", len(df), figures, [
        "Survey weights use WTTRDFIN.",
        "Tour types use H=Home, W=Work, and O=Other anchors.",
        "Distance/time plots exclude invalid or extreme values for legibility.",
    ])


if __name__ == "__main__":
    main()
