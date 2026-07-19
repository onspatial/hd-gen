#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import (
    FUEL_TYPE, VEHICLE_TYPE, barh, code_to_label, ensure_dir, heatmap, numeric,
    positive_weight, savefig, weighted_counts, weighted_crosstab, weighted_mean_by,
    write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS VEHV2PUB vehicle file.")
    ap.add_argument("input", type=Path, help="Path to VEHV2PUB.CSV")
    ap.add_argument("--out", type=Path, default=Path("figs/vehv2pub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = ["HOUSEID", "VEHID", "WTHHFIN", "VEHTYPE", "VEHAGE", "VEHYEAR", "FUELTYPE",
            "HYBRID", "ANNMILES", "EPATMPG", "EIADMPG", "GSTOTCST", "GSYRGAL", "GSCOST",
            "HHVEHCNT", "HHFAMINC", "URBRUR", "BEST_FLG"]
    df = pd.read_csv(args.input, usecols=lambda c: c in cols, low_memory=False)
    df["weight"] = positive_weight(df["WTHHFIN"])
    df["vehicle_type"] = code_to_label(df["VEHTYPE"], VEHICLE_TYPE)
    figures: list[str] = []

    vehicle_counts = weighted_counts(df["vehicle_type"], df["weight"], drop_unknown=True)
    barh(vehicle_counts, "Vehicle fleet composition", "Percent of weighted vehicles", out,
         "01_vehicle_type_share.png", percent=True)
    figures.append("01_vehicle_type_share.png")

    age = numeric(df["VEHAGE"])
    age_labels = ["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "25+"]
    age_band = pd.cut(age, bins=[0, 2, 5, 10, 15, 20, 25, np.inf], labels=age_labels)
    age_counts = weighted_counts(age_band.astype("string"), df["weight"]).reindex(age_labels).dropna()
    barh(age_counts, "Vehicle age distribution",
         "Percent of weighted vehicles", out, "02_vehicle_age.png", percent=True)
    figures.append("02_vehicle_age.png")

    fuel = code_to_label(df["FUELTYPE"], FUEL_TYPE)
    barh(weighted_counts(fuel, df["weight"], drop_unknown=True), "Vehicle fuel type",
         "Percent of weighted vehicles", out, "03_fuel_type.png", percent=True)
    figures.append("03_fuel_type.png")

    # Annual miles by vehicle type.
    df["ANNMILES"] = numeric(df["ANNMILES"])
    miles = weighted_mean_by(df[(df["vehicle_type"] != "Unknown") & df["ANNMILES"].between(0, 100000)], "vehicle_type", "ANNMILES", "weight")
    barh(miles, "Average annual miles by vehicle type", "Weighted mean annual miles", out,
         "04_annual_miles_by_vehicle_type.png")
    figures.append("04_annual_miles_by_vehicle_type.png")

    # MPG by vehicle type.
    df["EPATMPG"] = numeric(df["EPATMPG"])
    mpg = weighted_mean_by(df[(df["vehicle_type"] != "Unknown") & df["EPATMPG"].between(5, 100)], "vehicle_type", "EPATMPG", "weight")
    barh(mpg, "Average EPA fuel economy by vehicle type", "Weighted mean MPG", out,
         "05_mpg_by_vehicle_type.png")
    figures.append("05_mpg_by_vehicle_type.png")

    # Annual fuel cost by vehicle type.
    df["GSTOTCST"] = numeric(df["GSTOTCST"])
    cost = weighted_mean_by(df[(df["vehicle_type"] != "Unknown") & df["GSTOTCST"].between(0, 20000)], "vehicle_type", "GSTOTCST", "weight")
    barh(cost, "Average annual fuel expenditure by vehicle type", "Weighted mean nominal dollars", out,
         "06_fuel_cost_by_vehicle_type.png")
    figures.append("06_fuel_cost_by_vehicle_type.png")

    # Vehicle age vs annual miles.
    d = df.assign(vehicle_age=age)
    d = d[d["vehicle_age"].between(1, 35) & d["ANNMILES"].between(0, 60000)]
    if len(d) > 120000:
        d = d.sample(120000, random_state=42)
    fig, ax = plt.subplots(figsize=(9, 6))
    hb = ax.hexbin(d["vehicle_age"], d["ANNMILES"], gridsize=45, bins="log", mincnt=1, cmap="viridis")
   #  ax.set_title("Vehicle age and annual mileage")
    ax.set_xlabel("Vehicle age, years")
    ax.set_ylabel("Annual miles")
    fig.colorbar(hb, ax=ax, label="log10 observations")
    savefig(fig, out, "07_vehicle_age_vs_miles.png")
    figures.append("07_vehicle_age_vs_miles.png")

    # Type mix by household fleet size.
    fleet = pd.cut(numeric(df["HHVEHCNT"]), bins=[0, 1, 2, 3, np.inf], labels=["1", "2", "3", "4+"])
    t = weighted_crosstab(fleet, df["vehicle_type"], df["weight"], normalize="row")
    top_types = vehicle_counts.head(7).index
    t = t.reindex(columns=[x for x in top_types if x in t.columns])
    heatmap(t, "Vehicle type mix within household fleet size", out, "08_type_by_fleet_size.png",
            "Vehicle type", "Vehicles in household", fmt=".0f")
    figures.append("08_type_by_fleet_size.png")

    # MPG evolution by vehicle age.
    d = df.assign(vehicle_age=age)
    d = d[d["vehicle_age"].between(1, 35) & d["EPATMPG"].between(5, 100)]
    d["age_band"] = pd.cut(d["vehicle_age"], bins=[0, 2, 5, 10, 15, 20, 25, 35],
                           labels=["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-35"])
    mpg_age = weighted_mean_by(d, "age_band", "EPATMPG", "weight")
    age_order = ["1-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-35"]
    mpg_age = mpg_age.reindex(age_order).dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(mpg_age.index.astype(str), mpg_age.values, marker="o")
   #  ax.set_title("Fuel economy by vehicle age")
    ax.set_xlabel("Vehicle age group")
    ax.set_ylabel("Weighted mean MPG")
    ax.grid(alpha=0.25)
    savefig(fig, out, "09_mpg_by_vehicle_age.png")
    figures.append("09_mpg_by_vehicle_age.png")

    write_summary(out, "VEHV2PUB", len(df), figures, [
        "Survey weights use household weight WTHHFIN, as supplied on the vehicle file.",
        "Invalid and extreme engineering values are removed before averages.",
    ])


if __name__ == "__main__":
    main()
