#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from main.python.code.realism.nhts_visualization.viz_common import (
    INCOME_LABELS, LIFECYCLE_LABELS, STATE_FIPS, barh, code_to_label, ensure_dir,
    heatmap, numeric, positive_weight, savefig, weighted_counts, weighted_crosstab,
    weighted_mean_by, write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS HHV2PUB household file.")
    ap.add_argument("input", type=Path, help="Path to HHV2PUB.CSV")
    ap.add_argument("--out", type=Path, default=Path("figs/hhv2pub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = ["HOUSEID", "WTHHFIN", "HHSIZE", "HHVEHCNT", "DRVRCNT", "WRKCOUNT", "NUMADLT",
            "HHFAMINC", "LIF_CYC", "URBRUR", "HOMEOWN", "HOMETYPE", "CNTTDHH",
            "HHSTFIPS", "TRAVDAY", "FLAG100"]
    df = pd.read_csv(args.input, usecols=lambda c: c in cols, low_memory=False)
    df["weight"] = positive_weight(df["WTHHFIN"])
    figures: list[str] = []

    hhsize = numeric(df["HHSIZE"]).clip(upper=8).astype("Int64").astype("string").replace("8", "8+")
    barh(weighted_counts(hhsize, df["weight"]), "Household size distribution", "Percent of weighted households",
         out, "01_household_size.png", percent=True)
    figures.append("01_household_size.png")

    veh = numeric(df["HHVEHCNT"]).clip(upper=6).astype("Int64").astype("string").replace("6", "6+")
    barh(weighted_counts(veh, df["weight"]), "Vehicles available per household", "Percent of weighted households",
         out, "02_vehicle_count.png", percent=True)
    figures.append("02_vehicle_count.png")

    income = code_to_label(df["HHFAMINC"], INCOME_LABELS)
    income_counts = weighted_counts(income, df["weight"], drop_unknown=True).reindex(list(INCOME_LABELS.values())).dropna()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(income_counts.index, income_counts.values / income_counts.sum() * 100)
    ax.set_title("Household income distribution")
    ax.set_ylabel("Percent of weighted households")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "03_income_distribution.png")
    figures.append("03_income_distribution.png")

    # Vehicle availability by income.
    inc_code = numeric(df["HHFAMINC"])
    inc_band = pd.cut(inc_code, bins=[0, 5, 10, 15, 17, 18],
                      labels=["<$25k", "$25-49k", "$50-74k", "$75-99k", "$100k+"])
    veh_band = pd.cut(numeric(df["HHVEHCNT"]), bins=[-0.1, 0.1, 1.1, 2.1, np.inf],
                      labels=["0 vehicles", "1 vehicle", "2 vehicles", "3+ vehicles"])
    t = weighted_crosstab(inc_band, veh_band, df["weight"], normalize="row")
    t = t.reindex(index=["<$25k", "$25-49k", "$50-74k", "$75-99k", "$100k+"],
                  columns=["0 vehicles", "1 vehicle", "2 vehicles", "3+ vehicles"])
    heatmap(t, "Vehicle availability within household income groups", out, "04_vehicles_by_income.png",
            "Vehicles", "Income group", fmt=".0f")
    figures.append("04_vehicles_by_income.png")

    lifecycle = code_to_label(df["LIF_CYC"], LIFECYCLE_LABELS)
    barh(weighted_counts(lifecycle, df["weight"], drop_unknown=True), "Household life-cycle composition",
         "Percent of weighted households", out, "05_lifecycle.png", percent=True)
    figures.append("05_lifecycle.png")

    urban = numeric(df["URBRUR"]).map({1: "Urban", 2: "Rural"}).fillna("Unknown")
    barh(weighted_counts(urban, df["weight"], drop_unknown=True), "Urban and rural household share",
         "Percent of weighted households", out, "06_urban_rural.png", percent=True)
    figures.append("06_urban_rural.png")

    # Average household trip count by vehicle count and household size.
    df["vehicle_group"] = pd.cut(numeric(df["HHVEHCNT"]), [-0.1, 0.1, 1.1, 2.1, np.inf],
                                 labels=["0", "1", "2", "3+"])
    df["size_group"] = pd.cut(numeric(df["HHSIZE"]), [0, 1, 2, 3, 4, np.inf],
                              labels=["1", "2", "3", "4", "5+"])
    d = df[["vehicle_group", "size_group", "CNTTDHH", "weight"]].copy()
    d["CNTTDHH"] = numeric(d["CNTTDHH"])
    d = d.dropna()
    d = d[d["CNTTDHH"].between(0, 100)]
    d["wv"] = d["CNTTDHH"] * d["weight"]
    g = d.groupby(["size_group", "vehicle_group"], observed=True)
    avg = (g["wv"].sum() / g["weight"].sum()).unstack()
    heatmap(avg, "Average household travel-day trips by household and fleet size", out,
            "07_trips_by_household_and_vehicle_size.png", "Vehicles", "Household members", fmt=".1f")
    figures.append("07_trips_by_household_and_vehicle_size.png")

    # Vehicle-to-driver ratio.
    drivers = numeric(df["DRVRCNT"])
    vehicles = numeric(df["HHVEHCNT"])
    ratio = (vehicles / drivers.replace(0, np.nan)).clip(0, 4)
    valid = pd.DataFrame({"ratio": ratio, "weight": df["weight"]}).dropna()
    bins = np.linspace(0, 4, 17)
    idx = np.digitize(valid["ratio"], bins, right=False)
    hist = valid.groupby(idx)["weight"].sum()
    centers = (bins[:-1] + bins[1:]) / 2
    y = np.zeros(len(centers))
    for k, v in hist.items():
        if 1 <= k <= len(centers):
            y[k-1] = v
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(centers, y / y.sum() * 100, width=np.diff(bins) * 0.9)
    ax.axvline(1, linestyle="--", linewidth=1.2, label="One vehicle per driver")
    ax.set_title("Vehicles per licensed driver")
    ax.set_xlabel("Vehicle-to-driver ratio")
    ax.set_ylabel("Percent of weighted households")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "08_vehicles_per_driver.png")
    figures.append("08_vehicles_per_driver.png")

    states = numeric(df["HHSTFIPS"]).map(STATE_FIPS).fillna("Unknown")
    barh(weighted_counts(states, df["weight"], drop_unknown=True), "Top states by weighted household count",
         "Weighted households", out, "09_households_by_state.png", top=20)
    figures.append("09_households_by_state.png")

    write_summary(out, "HHV2PUB", len(df), figures, ["Survey weights use WTHHFIN."])


if __name__ == "__main__":
    main()
