#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from viz_common import (
    FUEL_TYPE, VEHICLE_TYPE, barh, code_to_label, ensure_dir, heatmap, numeric,
    positive_weight, savefig, weighted_counts, weighted_crosstab, weighted_mean_by,
    write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2017 NHTS VEHPUB vehicle file.")
    ap.add_argument("input", type=Path, help="Path to vehpub.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/vehpub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = [
        "HOUSEID", "VEHID", "WTHHFIN", "VEHTYPE", "VEHAGE", "VEHYEAR", "FUELTYPE",
        "HYBRID", "ANNMILES", "BESTMILE", "FEGEMPG", "GSTOTCST", "GSYRGAL", "GSCOST",
        "HHVEHCNT", "HHFAMINC", "URBRUR", "BEST_FLG",
    ]
    df = pd.read_csv(args.input, usecols=cols, low_memory=False)
    df["weight"] = positive_weight(df["WTHHFIN"])
    df["vehicle_type"] = code_to_label(df["VEHTYPE"], VEHICLE_TYPE)
    figures: list[str] = []

    vehicle_counts = weighted_counts(df["vehicle_type"], df["weight"], drop_unknown=True)
    barh(vehicle_counts, "Vehicle fleet composition", "Percent of weighted vehicles", out,
         "01_vehicle_type_share.png", percent=True)
    figures.append("01_vehicle_type_share.png")

    age = numeric(df["VEHAGE"])
    age_labels = ["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-35", "36+"]
    age_band = pd.cut(age, bins=[0, 2, 5, 10, 15, 20, 25, 35, np.inf], labels=age_labels)
    age_counts = weighted_counts(age_band.astype("string"), df["weight"]).reindex(age_labels).dropna()
    barh(age_counts, "Vehicle age distribution", "Percent of weighted vehicles", out,
         "02_vehicle_age.png", percent=True)
    figures.append("02_vehicle_age.png")

    fuel = code_to_label(df["FUELTYPE"], FUEL_TYPE)
    barh(weighted_counts(fuel, df["weight"], drop_unknown=True), "Vehicle fuel type",
         "Percent of weighted vehicles", out, "03_fuel_type.png", percent=True)
    figures.append("03_fuel_type.png")

    df["BESTMILE"] = numeric(df["BESTMILE"])
    miles = weighted_mean_by(
        df[(df["vehicle_type"] != "Unknown") & df["BESTMILE"].between(0, 100_000)],
        "vehicle_type", "BESTMILE", "weight",
    )
    barh(miles, "Average annual miles by vehicle type", "Weighted mean annual miles", out,
         "04_annual_miles_by_vehicle_type.png")
    figures.append("04_annual_miles_by_vehicle_type.png")

    df["FEGEMPG"] = numeric(df["FEGEMPG"])
    mpg = weighted_mean_by(
        df[(df["vehicle_type"] != "Unknown") & df["FEGEMPG"].between(5, 150)],
        "vehicle_type", "FEGEMPG", "weight",
    )
    barh(mpg, "Average fuel economy by vehicle type", "Weighted mean MPG", out,
         "05_mpg_by_vehicle_type.png")
    figures.append("05_mpg_by_vehicle_type.png")

    df["GSTOTCST"] = numeric(df["GSTOTCST"])
    cost = weighted_mean_by(
        df[(df["vehicle_type"] != "Unknown") & df["GSTOTCST"].between(0, 20_000)],
        "vehicle_type", "GSTOTCST", "weight",
    )
    barh(cost, "Average annual fuel expenditure by vehicle type", "Weighted mean nominal dollars", out,
         "06_fuel_cost_by_vehicle_type.png")
    figures.append("06_fuel_cost_by_vehicle_type.png")

    mileage_age = df.assign(vehicle_age=age)
    mileage_age = mileage_age[mileage_age["vehicle_age"].between(1, 40) & mileage_age["BESTMILE"].between(0, 60_000)]
    if len(mileage_age) > 120_000:
        mileage_age = mileage_age.sample(120_000, random_state=42)
    fig, ax = plt.subplots(figsize=(9, 6))
    hexbin = ax.hexbin(mileage_age["vehicle_age"], mileage_age["BESTMILE"], gridsize=45, bins="log", mincnt=1, cmap="viridis")
    ax.set_title("Vehicle age and annual mileage")
    ax.set_xlabel("Vehicle age, years")
    ax.set_ylabel("Best estimate of annual miles")
    fig.colorbar(hexbin, ax=ax, label="log10 observations")
    savefig(fig, out, "07_vehicle_age_vs_miles.png")
    figures.append("07_vehicle_age_vs_miles.png")

    fleet = pd.cut(numeric(df["HHVEHCNT"]), bins=[0, 1, 2, 3, np.inf], labels=["1", "2", "3", "4+"])
    type_table = weighted_crosstab(fleet, df["vehicle_type"], df["weight"], normalize="row")
    top_types = vehicle_counts.head(7).index
    type_table = type_table.reindex(columns=[value for value in top_types if value in type_table.columns])
    heatmap(type_table, "Vehicle type mix within household fleet size", out,
            "08_type_by_fleet_size.png", "Vehicle type", "Vehicles in household", fmt=".0f")
    figures.append("08_type_by_fleet_size.png")

    mpg_age = df.assign(vehicle_age=age)
    mpg_age = mpg_age[mpg_age["vehicle_age"].between(1, 40) & mpg_age["FEGEMPG"].between(5, 150)]
    mpg_age["age_band"] = pd.cut(
        mpg_age["vehicle_age"],
        bins=[0, 2, 5, 10, 15, 20, 25, 35, 40],
        labels=["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-35", "36-40"],
    )
    mpg_by_age = weighted_mean_by(mpg_age, "age_band", "FEGEMPG", "weight")
    age_order = ["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-35", "36-40"]
    mpg_by_age = mpg_by_age.reindex(age_order).dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(mpg_by_age.index.astype(str), mpg_by_age.values, marker="o")
    ax.set_title("Fuel economy by vehicle age")
    ax.set_xlabel("Vehicle age group")
    ax.set_ylabel("Weighted mean MPG")
    ax.grid(alpha=0.25)
    savefig(fig, out, "09_mpg_by_vehicle_age.png")
    figures.append("09_mpg_by_vehicle_age.png")

    write_summary(out, "VEHPUB", len(df), figures, [
        "Survey weights use household weight WTHHFIN, as supplied on the vehicle file.",
        "Annual mileage uses the 2017 BESTMILE estimate.",
        "Fuel economy uses the 2017 FEGEMPG field.",
        "Invalid and extreme engineering values are removed before averages.",
    ])


if __name__ == "__main__":
    main()
