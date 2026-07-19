#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import (
    MODE_GROUPS, MODE_LABELS, age_group, barh, code_to_label, ensure_dir, heatmap,
    numeric, positive_weight, savefig, weighted_counts, weighted_crosstab,
    weighted_mean_by, write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS PERV2PUB person file.")
    ap.add_argument("input", type=Path, help="Path to PERV2PUB.CSV")
    ap.add_argument("--out", type=Path, default=Path("figs/perv2pub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = ["HOUSEID", "PERSONID", "WTPERFIN", "R_AGE", "R_SEX", "WORKER", "DRIVER",
            "PRMACT", "WRKTRANS", "DISTTOWK", "TIMETOWK", "CNTTDTR", "NWALKTRP",
            "NBIKETRP", "URBRUR", "HHFAMINC", "EDUC", "MEDCOND", "PTUSED", "YEARMILE"]
    df = pd.read_csv(args.input, usecols=lambda c: c in cols, low_memory=False)
    df["weight"] = positive_weight(df["WTPERFIN"])
    df["age_group"] = age_group(df["R_AGE"])
    figures: list[str] = []

    # Age distribution.
    age_counts = weighted_counts(df["age_group"].astype("string"), df["weight"])
    order = [str(x) for x in df["age_group"].cat.categories]
    age_counts = age_counts.reindex(order).dropna()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(age_counts.index, age_counts.values / age_counts.sum() * 100)
   #  ax.set_title("Population age distribution")
    ax.set_ylabel("Percent of weighted persons")
    ax.set_xlabel("Age group")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "01_age_distribution.png")
    figures.append("01_age_distribution.png")

    # Sex composition by age.
    sex = numeric(df["R_SEX"]).map({1: "Male", 2: "Female"}).fillna("Unknown")
    sx = weighted_crosstab(df["age_group"].astype("string"), sex, df["weight"], normalize="row")
    sx = sx.reindex(order).dropna(how="all")
    heatmap(sx.drop(columns="Unknown", errors="ignore"), "Sex composition within age groups", out,
            "02_sex_by_age.png", "Sex", "Age group", fmt=".0f")
    figures.append("02_sex_by_age.png")

    # Worker and driver status by age.
    worker = numeric(df["WORKER"]).map({1: "Worker", 2: "Not worker"}).fillna("Unknown")
    driver = numeric(df["DRIVER"]).map({1: "Driver", 2: "Not driver"}).fillna("Unknown")
    wtab = weighted_crosstab(df["age_group"].astype("string"), worker, df["weight"], normalize="row")
    dtab = weighted_crosstab(df["age_group"].astype("string"), driver, df["weight"], normalize="row")
    result = pd.DataFrame({
        "Worker %": wtab.get("Worker", pd.Series(dtype=float)),
        "Driver %": dtab.get("Driver", pd.Series(dtype=float)),
    }).reindex(order)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(result.index, result["Worker %"], marker="o", label="Worker")
    ax.plot(result.index, result["Driver %"], marker="o", label="Licensed driver")
   #  ax.set_title("Worker and driver prevalence by age")
    ax.set_ylabel("Percent within age group")
    ax.set_xlabel("Age group")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25)
    ax.legend()
    savefig(fig, out, "03_worker_driver_by_age.png")
    figures.append("03_worker_driver_by_age.png")

    # Commute mode share among valid workers.
    commute_mode = code_to_label(df["WRKTRANS"], MODE_LABELS)
    commute_counts = weighted_counts(commute_mode, df["weight"], drop_unknown=True)
    barh(commute_counts, "Usual commute mode", "Percent of weighted commuters", out,
         "04_commute_mode_share.png", top=16, percent=True)
    figures.append("04_commute_mode_share.png")

    # Broad commute mode by urban/rural residence.
    commute_group = numeric(df["WRKTRANS"]).map(MODE_GROUPS).fillna("Unknown")
    urban = numeric(df["URBRUR"]).map({1: "Urban", 2: "Rural"}).fillna("Unknown")
    cm = weighted_crosstab(urban, commute_group, df["weight"], normalize="row")
    cm = cm.drop(index="Unknown", errors="ignore").drop(columns="Unknown", errors="ignore")
    heatmap(cm, "Commute mode mix by urban/rural residence", out, "05_commute_mode_urban_rural.png",
            "Mode group", "Residence", fmt=".0f")
    figures.append("05_commute_mode_urban_rural.png")

    # Commute distance vs time, sampled hexbin.
    dist = numeric(df["DISTTOWK"])
    tm = numeric(df["TIMETOWK"])
    valid = df.assign(distance=dist, minutes=tm)
    valid = valid[valid["distance"].between(0.1, 100) & valid["minutes"].between(1, 180)]
    if len(valid) > 100000:
        valid = valid.sample(100000, random_state=42)
    fig, ax = plt.subplots(figsize=(8, 6))
    hb = ax.hexbin(valid["distance"], valid["minutes"], gridsize=45, bins="log", mincnt=1, cmap="viridis")
   #  ax.set_title("Commute distance and time")
    ax.set_xlabel("Distance to work, miles")
    ax.set_ylabel("Travel time to work, minutes")
    fig.colorbar(hb, ax=ax, label="log10 observations")
    savefig(fig, out, "06_commute_distance_time.png")
    figures.append("06_commute_distance_time.png")

    # Trips per person by age.
    df["CNTTDTR"] = numeric(df["CNTTDTR"])
    trips_age = weighted_mean_by(df[df["CNTTDTR"].between(0, 30)], "age_group", "CNTTDTR", "weight").reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(trips_age.index.astype(str), trips_age.values, marker="o")
   #  ax.set_title("Average reported travel-day trips by age")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Weighted mean trips")
    ax.grid(alpha=0.25)
    savefig(fig, out, "07_trips_by_age.png")
    figures.append("07_trips_by_age.png")

    # Walking and bicycle trip frequency by age.
    df["NWALKTRP"] = numeric(df["NWALKTRP"])
    df["NBIKETRP"] = numeric(df["NBIKETRP"])
    walk = weighted_mean_by(df[df["NWALKTRP"].between(0, 100)], "age_group", "NWALKTRP", "weight")
    bike = weighted_mean_by(df[df["NBIKETRP"].between(0, 100)], "age_group", "NBIKETRP", "weight")
    wb = pd.concat([walk.rename("Walk trips"), bike.rename("Bike trips")], axis=1).reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(wb.index.astype(str), wb["Walk trips"], marker="o", label="Walk trips")
    ax.plot(wb.index.astype(str), wb["Bike trips"], marker="o", label="Bicycle trips")
   #  ax.set_title("Reported walking and bicycling frequency by age")
    ax.set_ylabel("Weighted mean trips in prior period")
    ax.set_xlabel("Age group")
    ax.grid(alpha=0.25)
    ax.legend()
    savefig(fig, out, "08_walk_bike_by_age.png")
    figures.append("08_walk_bike_by_age.png")

    # Annual driving mileage by age for drivers.
    df["YEARMILE"] = numeric(df["YEARMILE"])
    annual = weighted_mean_by(df[df["YEARMILE"].between(0, 100000)], "age_group", "YEARMILE", "weight").reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(annual.index.astype(str), annual.values)
   #  ax.set_title("Average annual miles driven by age")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Weighted mean miles")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "09_annual_miles_by_age.png")
    figures.append("09_annual_miles_by_age.png")

    write_summary(out, "PERV2PUB", len(df), figures, [
        "Survey weights use WTPERFIN.",
        "Commute plots exclude skip, unknown, and implausible values.",
    ])


if __name__ == "__main__":
    main()
