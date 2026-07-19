#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import (
    barh, ensure_dir, heatmap, numeric, positive_weight, savefig,
    weighted_counts, weighted_crosstab, weighted_mean_by, write_summary,
)

ANCHOR = {"H": "Home", "W": "Work", "O": "Other"}


def tour_origin(s: pd.Series) -> pd.Series:
    return s.astype("string").str[0].map(ANCHOR).fillna("Unknown")


def tour_destination(s: pd.Series) -> pd.Series:
    return s.astype("string").str[-1].map(ANCHOR).fillna("Unknown")


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS chained-trip file CHNTRP09.")
    ap.add_argument("input", type=Path, help="Path to chntrp09.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/chntrp09"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    df = pd.read_csv(args.input, low_memory=False)
    df["weight"] = positive_weight(df["WTTRDFIN"])
    df["origin"] = tour_origin(df["TOURTYPE"])
    df["destination"] = tour_destination(df["TOURTYPE"])
    figures: list[str] = []

    # Each trip record inherits its tour type. This shows how trip segments flow among anchors.
    od = weighted_crosstab(df["origin"], df["destination"], df["weight"], normalize="all")
    order = ["Home", "Work", "Other"]
    od = od.reindex(index=order, columns=order)
    heatmap(od, "Weighted trip segments by tour origin and destination anchor", out,
            "01_anchor_flow.png", "Destination anchor", "Origin anchor", fmt=".1f")
    figures.append("01_anchor_flow.png")

    tour_type = df["origin"] + " to " + df["destination"]
    tours = df.drop_duplicates(["HOUSEID", "PERSONID", "TOUR"]).copy()
    tours["tour_label"] = tours["origin"] + " to " + tours["destination"]
    barh(weighted_counts(tour_type, df["weight"], drop_unknown=True), "Tour-type share across trip segments",
         "Percent of weighted trip segments", out, "02_tour_type_share.png", percent=True)
    figures.append("02_tour_type_share.png")

    trips_per_tour = numeric(tours["TRPCNT"]).clip(upper=8).astype("Int64").astype("string").replace("8", "8+")
    barh(weighted_counts(trips_per_tour, tours["weight"]), "Trips that make up each tour",
         "Percent of weighted tours", out, "03_trips_per_tour.png", percent=True)
    figures.append("03_trips_per_tour.png")

    stops = numeric(tours["STOPS"]).clip(upper=6).astype("Int64").astype("string").replace("6", "6+")
    barh(weighted_counts(stops, tours["weight"]), "Stops within each tour",
         "Percent of weighted tours", out, "04_stops_distribution.png", percent=True)
    figures.append("04_stops_distribution.png")

    tour_flag = numeric(df["TOUR_FLG"]).map({0: "Not part of a multi-stop tour", 1: "Part of a multi-stop tour"}).fillna("Unknown")
    barh(weighted_counts(tour_flag, df["weight"], drop_unknown=True), "Share of trip records flagged as part of a tour",
         "Percent of weighted trip segments", out, "05_tour_flag_share.png", percent=True)
    figures.append("05_tour_flag_share.png")

    # Segment position profile for tours with up to eight trips.
    d = df.copy()
    d["TOUR_SEG"] = numeric(d["TOUR_SEG"])
    d["TRPCNT"] = numeric(d["TRPCNT"])
    d = d[d["TRPCNT"].between(1, 8) & d["TOUR_SEG"].between(1, 8)]
    seg = d.pivot_table(index="TRPCNT", columns="TOUR_SEG", values="weight", aggfunc="sum", fill_value=0)
    seg = seg.div(seg.sum(axis=1), axis=0) * 100
    heatmap(seg, "Position of each trip segment within its tour", out, "06_segment_position.png",
            "Segment position", "Trips in tour", fmt=".0f")
    figures.append("06_segment_position.png")

    # Average trips and stops by tour type, one record per tour.
    d = tours.copy()
    d["TRPCNT"] = numeric(d["TRPCNT"])
    d["STOPS"] = numeric(d["STOPS"])
    avg_trips = weighted_mean_by(d[d["TRPCNT"].between(1, 30)], "tour_label", "TRPCNT", "weight")
    avg_stops = weighted_mean_by(d[d["STOPS"].between(0, 30)], "tour_label", "STOPS", "weight")
    avg = pd.concat([avg_trips.rename("Trips"), avg_stops.rename("Stops")], axis=1).dropna().sort_index()
    x = np.arange(len(avg))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x - 0.2, avg["Trips"], 0.4, label="Trips")
    ax.bar(x + 0.2, avg["Stops"], 0.4, label="Stops")
    ax.set_xticks(x, avg.index, rotation=35, ha="right")
   #  ax.set_title("Average tour complexity by tour type")
    ax.set_ylabel("Weighted mean")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "07_tour_complexity_by_type.png")
    figures.append("07_tour_complexity_by_type.png")

    # Number of tours and trip records per person.
    per = df.groupby(["HOUSEID", "PERSONID"]).agg(tours=("TOUR", "nunique"), trip_records=("TDTRPNUM", "size")).reset_index()
    fig, ax = plt.subplots(figsize=(8, 6))
    max_tours = min(10, int(per["tours"].quantile(0.995)))
    max_trips = min(25, int(per["trip_records"].quantile(0.995)))
    hb = ax.hexbin(per["tours"].clip(upper=max_tours), per["trip_records"].clip(upper=max_trips),
                   gridsize=20, mincnt=1, cmap="viridis")
   #  ax.set_title("Tour count and trip-record count per person")
    ax.set_xlabel("Distinct tours")
    ax.set_ylabel("Trip records")
    fig.colorbar(hb, ax=ax, label="Persons")
    savefig(fig, out, "08_tours_and_trips_per_person.png")
    figures.append("08_tours_and_trips_per_person.png")

    write_summary(out, "CHNTRP09", len(df), figures, [
        "Survey weights use WTTRDFIN.",
        "Tour types use H=Home, W=Work, and O=Other anchors.",
    ])


if __name__ == "__main__":
    main()
