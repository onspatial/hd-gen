#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from viz_common import (
    INCOME_LABELS, LIFECYCLE_LABELS, STATE_FIPS, barh, code_to_label, ensure_dir,
    heatmap, numeric, positive_weight, savefig, weighted_counts, weighted_crosstab,
    write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2017 NHTS HHPUB household file.")
    ap.add_argument("input", type=Path, help="Path to hhpub.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/hhpub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = [
        "HOUSEID", "WTHHFIN", "HHSIZE", "HHVEHCNT", "DRVRCNT", "WRKCOUNT",
        "NUMADLT", "HHFAMINC", "LIF_CYC", "URBRUR", "HOMEOWN", "CNTTDHH",
        "HHSTFIPS", "TRAVDAY",
    ]
    df = pd.read_csv(args.input, usecols=cols, low_memory=False)
    df["weight"] = positive_weight(df["WTHHFIN"])
    figures: list[str] = []

    household_size = numeric(df["HHSIZE"]).clip(upper=8).astype("Int64").astype("string").replace("8", "8+")
    barh(weighted_counts(household_size, df["weight"]), "Household size distribution",
         "Percent of weighted households", out, "01_household_size.png", percent=True)
    figures.append("01_household_size.png")

    vehicle_count = numeric(df["HHVEHCNT"]).clip(upper=6).astype("Int64").astype("string").replace("6", "6+")
    barh(weighted_counts(vehicle_count, df["weight"]), "Vehicles available per household",
         "Percent of weighted households", out, "02_vehicle_count.png", percent=True)
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

    income_code = numeric(df["HHFAMINC"])
    income_band = pd.cut(
        income_code,
        bins=[0, 3, 5, 6, 7, 11],
        labels=["<$25k", "$25-49k", "$50-74k", "$75-99k", "$100k+"],
    )
    vehicle_band = pd.cut(
        numeric(df["HHVEHCNT"]),
        bins=[-0.1, 0.1, 1.1, 2.1, np.inf],
        labels=["0 vehicles", "1 vehicle", "2 vehicles", "3+ vehicles"],
    )
    table = weighted_crosstab(income_band, vehicle_band, df["weight"], normalize="row")
    table = table.reindex(
        index=["<$25k", "$25-49k", "$50-74k", "$75-99k", "$100k+"],
        columns=["0 vehicles", "1 vehicle", "2 vehicles", "3+ vehicles"],
    )
    heatmap(table, "Vehicle availability within household income groups", out,
            "04_vehicles_by_income.png", "Vehicles", "Income group", fmt=".0f")
    figures.append("04_vehicles_by_income.png")

    lifecycle = code_to_label(df["LIF_CYC"], LIFECYCLE_LABELS)
    barh(weighted_counts(lifecycle, df["weight"], drop_unknown=True), "Household life-cycle composition",
         "Percent of weighted households", out, "05_lifecycle.png", percent=True)
    figures.append("05_lifecycle.png")

    urban = numeric(df["URBRUR"]).map({1: "Urban", 2: "Rural"}).fillna("Unknown")
    barh(weighted_counts(urban, df["weight"], drop_unknown=True), "Urban and rural household share",
         "Percent of weighted households", out, "06_urban_rural.png", percent=True)
    figures.append("06_urban_rural.png")

    df["vehicle_group"] = pd.cut(numeric(df["HHVEHCNT"]), [-0.1, 0.1, 1.1, 2.1, np.inf], labels=["0", "1", "2", "3+"])
    df["size_group"] = pd.cut(numeric(df["HHSIZE"]), [0, 1, 2, 3, 4, np.inf], labels=["1", "2", "3", "4", "5+"])
    trips = df[["vehicle_group", "size_group", "CNTTDHH", "weight"]].copy()
    trips["CNTTDHH"] = numeric(trips["CNTTDHH"])
    trips = trips.dropna()
    trips = trips[trips["CNTTDHH"].between(0, 100)]
    trips["weighted_trips"] = trips["CNTTDHH"] * trips["weight"]
    grouped = trips.groupby(["size_group", "vehicle_group"], observed=True)
    average = (grouped["weighted_trips"].sum() / grouped["weight"].sum()).unstack()
    heatmap(average, "Average household travel-day trips by household and fleet size", out,
            "07_trips_by_household_and_vehicle_size.png", "Vehicles", "Household members", fmt=".1f")
    figures.append("07_trips_by_household_and_vehicle_size.png")

    drivers = numeric(df["DRVRCNT"])
    vehicles = numeric(df["HHVEHCNT"])
    ratio = (vehicles / drivers.replace(0, np.nan)).clip(0, 4)
    valid = pd.DataFrame({"ratio": ratio, "weight": df["weight"]}).dropna()
    bins = np.linspace(0, 4, 17)
    indexes = np.digitize(valid["ratio"], bins, right=False)
    histogram = valid.groupby(indexes)["weight"].sum()
    centers = (bins[:-1] + bins[1:]) / 2
    values = np.zeros(len(centers))
    for key, value in histogram.items():
        if 1 <= key <= len(centers):
            values[key - 1] = value
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(centers, values / values.sum() * 100, width=np.diff(bins) * 0.9)
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

    write_summary(out, "HHPUB", len(df), figures, [
        "Survey weights use WTHHFIN.",
        "Income categories use the 11-category 2017 HHFAMINC coding.",
    ])


if __name__ == "__main__":
    main()
