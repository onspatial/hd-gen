#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from viz_common import (
    MODE_GROUPS, MODE_LABELS, age_group, barh, code_to_label, ensure_dir, heatmap,
    numeric, positive_weight, savefig, weighted_counts, weighted_crosstab,
    weighted_mean_by, write_summary,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2017 NHTS PERPUB person file.")
    ap.add_argument("input", type=Path, help="Path to perpub.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/perpub"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = [
        "HOUSEID", "PERSONID", "WTPERFIN", "R_AGE", "R_SEX", "WORKER", "DRIVER",
        "PRMACT", "WRKTRANS", "DISTTOWK17", "TIMETOWK", "CNTTDTR", "NWALKTRP",
        "NBIKETRP", "URBRUR", "HHFAMINC", "EDUC", "MEDCOND", "PTUSED", "YEARMILE",
    ]
    df = pd.read_csv(args.input, usecols=cols, low_memory=False)
    df["weight"] = positive_weight(df["WTPERFIN"])
    df["age_group"] = age_group(df["R_AGE"])
    figures: list[str] = []

    age_counts = weighted_counts(df["age_group"].astype("string"), df["weight"])
    order = [str(value) for value in df["age_group"].cat.categories]
    age_counts = age_counts.reindex(order).dropna()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(age_counts.index, age_counts.values / age_counts.sum() * 100)
    ax.set_title("Population age distribution")
    ax.set_ylabel("Percent of weighted persons")
    ax.set_xlabel("Age group")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "01_age_distribution.png")
    figures.append("01_age_distribution.png")

    sex = numeric(df["R_SEX"]).map({1: "Male", 2: "Female"}).fillna("Unknown")
    sex_table = weighted_crosstab(df["age_group"].astype("string"), sex, df["weight"], normalize="row")
    sex_table = sex_table.reindex(order).dropna(how="all")
    heatmap(sex_table.drop(columns="Unknown", errors="ignore"), "Sex composition within age groups", out,
            "02_sex_by_age.png", "Sex", "Age group", fmt=".0f")
    figures.append("02_sex_by_age.png")

    worker = numeric(df["WORKER"]).map({1: "Worker", 2: "Not worker"}).fillna("Unknown")
    driver = numeric(df["DRIVER"]).map({1: "Driver", 2: "Not driver"}).fillna("Unknown")
    worker_table = weighted_crosstab(df["age_group"].astype("string"), worker, df["weight"], normalize="row")
    driver_table = weighted_crosstab(df["age_group"].astype("string"), driver, df["weight"], normalize="row")
    result = pd.DataFrame({
        "Worker %": worker_table.get("Worker", pd.Series(dtype=float)),
        "Driver %": driver_table.get("Driver", pd.Series(dtype=float)),
    }).reindex(order)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(result.index, result["Worker %"], marker="o", label="Worker")
    ax.plot(result.index, result["Driver %"], marker="o", label="Licensed driver")
    ax.set_title("Worker and driver prevalence by age")
    ax.set_ylabel("Percent within age group")
    ax.set_xlabel("Age group")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25)
    ax.legend()
    savefig(fig, out, "03_worker_driver_by_age.png")
    figures.append("03_worker_driver_by_age.png")

    commute_mode = code_to_label(df["WRKTRANS"], MODE_LABELS)
    commute_counts = weighted_counts(commute_mode, df["weight"], drop_unknown=True)
    barh(commute_counts, "Usual commute mode", "Percent of weighted commuters", out,
         "04_commute_mode_share.png", top=16, percent=True)
    figures.append("04_commute_mode_share.png")

    commute_group = numeric(df["WRKTRANS"]).map(MODE_GROUPS).fillna("Unknown")
    urban = numeric(df["URBRUR"]).map({1: "Urban", 2: "Rural"}).fillna("Unknown")
    commute_table = weighted_crosstab(urban, commute_group, df["weight"], normalize="row")
    commute_table = commute_table.drop(index="Unknown", errors="ignore").drop(columns="Unknown", errors="ignore")
    heatmap(commute_table, "Commute mode mix by urban/rural residence", out,
            "05_commute_mode_urban_rural.png", "Mode group", "Residence", fmt=".0f")
    figures.append("05_commute_mode_urban_rural.png")

    distance = numeric(df["DISTTOWK17"])
    time = numeric(df["TIMETOWK"])
    valid = df.assign(distance=distance, minutes=time)
    valid = valid[valid["distance"].between(0.1, 100) & valid["minutes"].between(1, 180)]
    if len(valid) > 100_000:
        valid = valid.sample(100_000, random_state=42)
    fig, ax = plt.subplots(figsize=(8, 6))
    hexbin = ax.hexbin(valid["distance"], valid["minutes"], gridsize=45, bins="log", mincnt=1, cmap="viridis")
    ax.set_title("Commute distance and time")
    ax.set_xlabel("Road-network distance to work, miles")
    ax.set_ylabel("Travel time to work, minutes")
    fig.colorbar(hexbin, ax=ax, label="log10 observations")
    savefig(fig, out, "06_commute_distance_time.png")
    figures.append("06_commute_distance_time.png")

    df["CNTTDTR"] = numeric(df["CNTTDTR"])
    trips_by_age = weighted_mean_by(df[df["CNTTDTR"].between(0, 30)], "age_group", "CNTTDTR", "weight").reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(trips_by_age.index.astype(str), trips_by_age.values, marker="o")
    ax.set_title("Average reported travel-day trips by age")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Weighted mean trips")
    ax.grid(alpha=0.25)
    savefig(fig, out, "07_trips_by_age.png")
    figures.append("07_trips_by_age.png")

    df["NWALKTRP"] = numeric(df["NWALKTRP"])
    df["NBIKETRP"] = numeric(df["NBIKETRP"])
    walk = weighted_mean_by(df[df["NWALKTRP"].between(0, 100)], "age_group", "NWALKTRP", "weight")
    bike = weighted_mean_by(df[df["NBIKETRP"].between(0, 100)], "age_group", "NBIKETRP", "weight")
    active = pd.concat([walk.rename("Walk trips"), bike.rename("Bike trips")], axis=1).reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(active.index.astype(str), active["Walk trips"], marker="o", label="Walk trips")
    ax.plot(active.index.astype(str), active["Bike trips"], marker="o", label="Bicycle trips")
    ax.set_title("Reported walking and bicycling frequency by age")
    ax.set_ylabel("Weighted mean reported trips")
    ax.set_xlabel("Age group")
    ax.grid(alpha=0.25)
    ax.legend()
    savefig(fig, out, "08_walk_bike_by_age.png")
    figures.append("08_walk_bike_by_age.png")

    df["YEARMILE"] = numeric(df["YEARMILE"])
    annual = weighted_mean_by(df[df["YEARMILE"].between(0, 100_000)], "age_group", "YEARMILE", "weight").reindex(df["age_group"].cat.categories)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(annual.index.astype(str), annual.values)
    ax.set_title("Average annual miles personally driven by age")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Weighted mean miles")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "09_annual_miles_by_age.png")
    figures.append("09_annual_miles_by_age.png")

    write_summary(out, "PERPUB", len(df), figures, [
        "Survey weights use WTPERFIN.",
        "Commute distance uses the 2017 DISTTOWK17 road-network field.",
        "Commute plots exclude skip, unknown, and implausible values.",
    ])


if __name__ == "__main__":
    main()
