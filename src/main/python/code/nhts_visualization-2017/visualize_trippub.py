#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from viz_common import (
    MODE_GROUPS, MODE_LABELS, PURPOSE_SUMMARY, STATE_FIPS, activity_purpose_group,
    age_group, barh, code_to_label, ensure_dir, heatmap, numeric, parse_hhmm,
    positive_weight, savefig, write_summary,
)

PURPOSE_ORDER = [
    "Home", "Work", "School/daycare/religious", "Medical/dental",
    "Shopping/errands", "Social/recreational", "Transport someone", "Meals", "Other",
]
ACTIVITY_COLORS = {
    "Home": "#1f77b4",
    "Work": "#ff7f0e",
    "School/daycare/religious": "#7f7f7f",
    "Medical/dental": "#8c564b",
    "Shopping/errands": "#9467bd",
    "Social/recreational": "#d62728",
    "Transport someone": "#e377c2",
    "Meals": "#2ca02c",
    "Other": "#bcbd22",
}
AGE_ORDER = ["0-4", "5-15", "16-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-89", "90+"]
MAJOR_MODES = ["Car", "SUV", "Pickup truck", "Public / commuter bus", "Bicycle", "Walk"]


def add_series(target: defaultdict, s: pd.Series) -> None:
    for key, value in s.items():
        target[str(key)] += float(value)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2017 NHTS TRIPPUB trip file.")
    ap.add_argument("input", type=Path, help="Path to trippub.csv")
    ap.add_argument("--out", type=Path, default=Path("figs/trippub"))
    ap.add_argument("--chunksize", type=int, default=100_000)
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = [
        "WTTRDFIN", "WHYFROM", "WHYTO", "WHYTRP1S", "TRPTRANS", "TRPMILES",
        "TRVLCMIN", "STRTTIME", "HHSTFIPS", "R_AGE",
    ]
    purpose_counts = defaultdict(float)
    mode_counts = defaultdict(float)
    state_counts = defaultdict(float)
    od_counts = defaultdict(float)
    mode_purpose_counts = defaultdict(float)
    hourly_counts = defaultdict(float)
    metric = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    age_metric = defaultdict(lambda: [0.0, 0.0])
    distance_samples = {mode: [] for mode in MAJOR_MODES}
    rng = np.random.default_rng(42)
    nrows = 0

    for chunk in pd.read_csv(args.input, usecols=cols, chunksize=args.chunksize, low_memory=False):
        nrows += len(chunk)
        weight = positive_weight(chunk["WTTRDFIN"])
        origin = activity_purpose_group(chunk["WHYFROM"])
        destination = activity_purpose_group(chunk["WHYTO"])
        purpose = code_to_label(chunk["WHYTRP1S"], PURPOSE_SUMMARY)
        mode = code_to_label(chunk["TRPTRANS"], MODE_LABELS)
        mode_group = numeric(chunk["TRPTRANS"]).map(MODE_GROUPS).fillna("Unknown")

        d = pd.DataFrame({"purpose": purpose, "mode": mode, "weight": weight}).dropna()
        add_series(purpose_counts, d[d["purpose"] != "Unknown"].groupby("purpose")["weight"].sum())
        add_series(mode_counts, d[d["mode"] != "Unknown"].groupby("mode")["weight"].sum())

        flow = pd.DataFrame({"origin": origin, "destination": destination, "weight": weight}).dropna()
        flow = flow[(flow["origin"] != "Unknown") & (flow["destination"] != "Unknown")]
        for (a, b), value in flow.groupby(["origin", "destination"])["weight"].sum().items():
            od_counts[(str(a), str(b))] += float(value)

        mix = pd.DataFrame({"purpose": purpose, "mode": mode_group, "weight": weight}).dropna()
        mix = mix[(mix["purpose"] != "Unknown") & (mix["mode"] != "Unknown")]
        for (a, b), value in mix.groupby(["purpose", "mode"])["weight"].sum().items():
            mode_purpose_counts[(str(a), str(b))] += float(value)

        hour = np.floor(parse_hhmm(chunk["STRTTIME"]) % 24)
        hourly = pd.DataFrame({"purpose": purpose, "hour": hour, "weight": weight}).dropna()
        hourly = hourly[(hourly["purpose"] != "Unknown") & hourly["hour"].between(0, 23)]
        for (p, h), value in hourly.groupby(["purpose", "hour"])["weight"].sum().items():
            hourly_counts[(str(p), int(h))] += float(value)

        miles = numeric(chunk["TRPMILES"])
        minutes = numeric(chunk["TRVLCMIN"])
        metrics = pd.DataFrame({"purpose": purpose, "miles": miles, "minutes": minutes, "weight": weight})
        for p, group in metrics.groupby("purpose"):
            if p == "Unknown":
                continue
            good_distance = group[group["miles"].between(0, 500) & group["weight"].notna()]
            good_time = group[group["minutes"].between(0, 600) & group["weight"].notna()]
            metric[str(p)][0] += float((good_distance["miles"] * good_distance["weight"]).sum())
            metric[str(p)][1] += float(good_distance["weight"].sum())
            metric[str(p)][2] += float((good_time["minutes"] * good_time["weight"]).sum())
            metric[str(p)][3] += float(good_time["weight"].sum())

        ages = age_group(chunk["R_AGE"]).astype("string")
        age_data = pd.DataFrame({"age": ages, "miles": miles, "weight": weight}).dropna()
        age_data = age_data[age_data["miles"].between(0, 500)]
        for age, group in age_data.groupby("age"):
            age_metric[str(age)][0] += float((group["miles"] * group["weight"]).sum())
            age_metric[str(age)][1] += float(group["weight"].sum())

        states = numeric(chunk["HHSTFIPS"]).map(STATE_FIPS).fillna("Unknown")
        state_data = pd.DataFrame({"state": states, "weight": weight}).dropna()
        add_series(state_counts, state_data[state_data["state"] != "Unknown"].groupby("state")["weight"].sum())

        sample_frame = pd.DataFrame({"mode": mode, "miles": miles})
        for major_mode in MAJOR_MODES:
            values = sample_frame.loc[
                (sample_frame["mode"] == major_mode) & sample_frame["miles"].between(0.01, 100), "miles"
            ].dropna().to_numpy()
            if len(values) and len(distance_samples[major_mode]) < 30_000:
                take = min(1_500, len(values), 30_000 - len(distance_samples[major_mode]))
                distance_samples[major_mode].extend(rng.choice(values, size=take, replace=False).tolist())

    figures: list[str] = []

    od = pd.DataFrame(0.0, index=PURPOSE_ORDER, columns=PURPOSE_ORDER)
    for (a, b), value in od_counts.items():
        if a in od.index and b in od.columns:
            od.loc[a, b] = value
    od = od.div(od.sum(axis=1).replace(0, np.nan), axis=0) * 100
    heatmap(od, "Destination purpose conditional on origin purpose", out,
            "01_origin_destination_purpose_flow.png", "Destination purpose", "Origin purpose", fmt=".0f")
    figures.append("01_origin_destination_purpose_flow.png")

    purpose_series = pd.Series(purpose_counts).sort_values(ascending=False)
    barh(purpose_series, "Weighted trip share by destination purpose", "Percent of weighted trips", out,
         "02_trip_purpose_share.png", percent=True)
    figures.append("02_trip_purpose_share.png")

    mode_series = pd.Series(mode_counts).sort_values(ascending=False)
    barh(mode_series, "Weighted trip share by travel mode", "Percent of weighted trips", out,
         "03_mode_share.png", top=18, percent=True)
    figures.append("03_mode_share.png")

    rows = sorted({a for a, _ in mode_purpose_counts})
    columns = sorted({b for _, b in mode_purpose_counts})
    mode_purpose = pd.DataFrame(0.0, index=rows, columns=columns)
    for (a, b), value in mode_purpose_counts.items():
        mode_purpose.loc[a, b] = value
    mode_purpose = mode_purpose.div(mode_purpose.sum(axis=1).replace(0, np.nan), axis=0) * 100
    mode_purpose = mode_purpose.reindex([x for x in PURPOSE_ORDER if x in mode_purpose.index])
    heatmap(mode_purpose, "Mode mix within each trip purpose", out, "04_mode_by_purpose.png",
            "Mode group", "Destination purpose", fmt=".0f")
    figures.append("04_mode_by_purpose.png")

    top_purposes = purpose_series.head(6).index
    hourly = pd.DataFrame(0.0, index=range(24), columns=top_purposes)
    for (purpose_name, hour), value in hourly_counts.items():
        if purpose_name in hourly.columns:
            hourly.loc[hour, purpose_name] = value
    hourly = hourly.div(hourly.sum(axis=0).replace(0, np.nan), axis=1) * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    for column in hourly.columns:
        ax.plot(hourly.index, hourly[column], marker="o", markersize=3, label=column, color=ACTIVITY_COLORS.get(column, None))
    # ax.set_title("Trip departure time by purpose")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Purpose of Daily Trips (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)
    savefig(fig, out, "05_departure_time_by_purpose.png")
    figures.append("05_departure_time_by_purpose.png")

    summary = pd.DataFrame(index=[p for p in PURPOSE_ORDER if p in metric], columns=["Miles", "Minutes"], dtype=float)
    for purpose_name in summary.index:
        value = metric[purpose_name]
        summary.loc[purpose_name] = [
            value[0] / value[1] if value[1] else np.nan,
            value[2] / value[3] if value[3] else np.nan,
        ]
    x = np.arange(len(summary))
    width = 0.42
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width / 2, summary["Miles"], width, label="Average miles")
    ax.bar(x + width / 2, summary["Minutes"], width, label="Average minutes")
    ax.set_xticks(x, summary.index, rotation=40, ha="right")
    ax.set_title("Average trip distance and duration by purpose")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    savefig(fig, out, "06_distance_duration_by_purpose.png")
    figures.append("06_distance_duration_by_purpose.png")

    labels = [mode for mode in MAJOR_MODES if distance_samples[mode]]
    samples = [distance_samples[mode] for mode in labels]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(samples, tick_labels=labels, showfliers=False)
    ax.set_yscale("log")
    ax.set_title("Trip distance distribution by major mode")
    ax.set_ylabel("Miles, log scale")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "07_distance_distribution_by_mode.png")
    figures.append("07_distance_distribution_by_mode.png")

    state_series = pd.Series(state_counts).sort_values(ascending=False)
    barh(state_series, "Top household states by weighted trip volume", "Weighted trips", out,
         "08_weighted_trip_volume_by_state.png", top=20)
    figures.append("08_weighted_trip_volume_by_state.png")

    age_values = pd.Series({k: v[0] / v[1] for k, v in age_metric.items() if v[1] > 0}).reindex(AGE_ORDER).dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(age_values.index, age_values.values, marker="o")
    ax.set_title("Average trip distance by traveler age")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Miles")
    ax.grid(alpha=0.25)
    savefig(fig, out, "09_distance_by_age.png")
    figures.append("09_distance_by_age.png")

    write_summary(out, "TRIPPUB", nrows, figures, [
        "Survey weights use WTTRDFIN.",
        "Trip duration uses the 2017 TRVLCMIN field.",
        "WHYFROM and WHYTO use the detailed 2017 activity-purpose codes.",
        "The file is processed in chunks to keep memory use bounded.",
    ])


if __name__ == "__main__":
    main()
