#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from main.python.code.realism.nhts_visualization.viz_common import (
    MODE_GROUPS, MODE_LABELS, PURPOSE_SUMMARY, STATE_FIPS, age_group, barh,
    code_to_label, ensure_dir, heatmap, numeric, parse_hhmm, positive_weight,
    purpose_group, savefig, write_summary,
)

PURPOSE_ORDER = ["Home", "Work", "School/religious", "Medical/dental", "Shopping/errands",
                 "Social/recreational", "Family/personal business", "Transport someone", "Meals", "Other"]
AGE_ORDER = ["0-4", "5-15", "16-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-89", "89+"]
MAJOR_MODES = ["Car", "SUV", "Pickup", "Local bus", "Bicycle", "Walk"]


def add_series(target: defaultdict, s: pd.Series) -> None:
    for k, v in s.items():
        target[str(k)] += float(v)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS DAYV2PUB trip file.")
    ap.add_argument("input", type=Path, help="Path to DAYV2PUB.CSV")
    ap.add_argument("--out", type=Path, default=Path("figs/dayv2pub"))
    ap.add_argument("--chunksize", type=int, default=100000)
    args = ap.parse_args()
    out = ensure_dir(args.out)

    cols = ["WTTRDFIN", "WHYFROM", "WHYTO", "WHYTRP1S", "TRPTRANS", "TRPMILES",
            "TRVL_MIN", "STRTTIME", "HHSTFIPS", "R_AGE"]
    purpose_counts = defaultdict(float)
    mode_counts = defaultdict(float)
    state_counts = defaultdict(float)
    od_counts = defaultdict(float)
    mp_counts = defaultdict(float)
    hourly_counts = defaultdict(float)
    metric = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # dist*w,w,time*w,w
    age_metric = defaultdict(lambda: [0.0, 0.0])
    distance_samples = {m: [] for m in MAJOR_MODES}
    rng = np.random.default_rng(42)
    nrows = 0

    for chunk in pd.read_csv(args.input, usecols=cols, chunksize=args.chunksize, low_memory=False):
        nrows += len(chunk)
        w = positive_weight(chunk["WTTRDFIN"])
        origin = purpose_group(chunk["WHYFROM"])
        destination = purpose_group(chunk["WHYTO"])
        purpose = code_to_label(chunk["WHYTRP1S"], PURPOSE_SUMMARY)
        mode = code_to_label(chunk["TRPTRANS"], MODE_LABELS)
        mode_group = numeric(chunk["TRPTRANS"]).map(MODE_GROUPS).fillna("Unknown")

        d = pd.DataFrame({"purpose": purpose, "mode": mode, "weight": w}).dropna()
        add_series(purpose_counts, d[d["purpose"] != "Unknown"].groupby("purpose")["weight"].sum())
        add_series(mode_counts, d[d["mode"] != "Unknown"].groupby("mode")["weight"].sum())

        f = pd.DataFrame({"origin": origin, "destination": destination, "weight": w}).dropna()
        f = f[(f["origin"] != "Unknown") & (f["destination"] != "Unknown")]
        for (a, b), v in f.groupby(["origin", "destination"])["weight"].sum().items():
            od_counts[(str(a), str(b))] += float(v)

        m = pd.DataFrame({"purpose": purpose, "mode": mode_group, "weight": w}).dropna()
        m = m[(m["purpose"] != "Unknown") & (m["mode"] != "Unknown")]
        for (a, b), v in m.groupby(["purpose", "mode"])["weight"].sum().items():
            mp_counts[(str(a), str(b))] += float(v)

        hr = np.floor(parse_hhmm(chunk["STRTTIME"]) % 24)
        h = pd.DataFrame({"purpose": purpose, "hour": hr, "weight": w}).dropna()
        h = h[(h["purpose"] != "Unknown") & h["hour"].between(0, 23)]
        for (p, hour), v in h.groupby(["purpose", "hour"])["weight"].sum().items():
            hourly_counts[(str(p), int(hour))] += float(v)

        miles = numeric(chunk["TRPMILES"])
        minutes = numeric(chunk["TRVL_MIN"])
        q = pd.DataFrame({"purpose": purpose, "miles": miles, "minutes": minutes, "weight": w})
        for p, g in q.groupby("purpose"):
            if p == "Unknown":
                continue
            gd = g[g["miles"].between(0, 500) & g["weight"].notna()]
            gt = g[g["minutes"].between(0, 600) & g["weight"].notna()]
            metric[str(p)][0] += float((gd["miles"] * gd["weight"]).sum())
            metric[str(p)][1] += float(gd["weight"].sum())
            metric[str(p)][2] += float((gt["minutes"] * gt["weight"]).sum())
            metric[str(p)][3] += float(gt["weight"].sum())

        ag = age_group(chunk["R_AGE"]).astype("string")
        a = pd.DataFrame({"age": ag, "miles": miles, "weight": w}).dropna()
        a = a[a["miles"].between(0, 500)]
        for p, g in a.groupby("age"):
            age_metric[str(p)][0] += float((g["miles"] * g["weight"]).sum())
            age_metric[str(p)][1] += float(g["weight"].sum())

        states = numeric(chunk["HHSTFIPS"]).map(STATE_FIPS).fillna("Unknown")
        s = pd.DataFrame({"state": states, "weight": w}).dropna()
        add_series(state_counts, s[s["state"] != "Unknown"].groupby("state")["weight"].sum())

        sample_frame = pd.DataFrame({"mode": mode, "miles": miles})
        for md in MAJOR_MODES:
            vals = sample_frame.loc[(sample_frame["mode"] == md) & sample_frame["miles"].between(0.01, 100), "miles"].dropna().to_numpy()
            if len(vals) and len(distance_samples[md]) < 30000:
                take = min(1500, len(vals), 30000 - len(distance_samples[md]))
                distance_samples[md].extend(rng.choice(vals, size=take, replace=False).tolist())

    figures: list[str] = []

    od = pd.DataFrame(0.0, index=PURPOSE_ORDER, columns=PURPOSE_ORDER)
    for (a, b), v in od_counts.items():
        if a in od.index and b in od.columns:
            od.loc[a, b] = v
    od = od.div(od.sum(axis=1).replace(0, np.nan), axis=0) * 100
    heatmap(od, "Where trips go: destination purpose conditional on origin purpose", out,
            "01_origin_destination_purpose_flow.png", "Destination purpose", "Origin purpose", fmt=".0f")
    figures.append("01_origin_destination_purpose_flow.png")

    pc = pd.Series(purpose_counts).sort_values(ascending=False)
    barh(pc, "Weighted trip share by destination purpose", "Percent of weighted trips", out,
         "02_trip_purpose_share.png", percent=True)
    figures.append("02_trip_purpose_share.png")

    mc = pd.Series(mode_counts).sort_values(ascending=False)
    barh(mc, "Weighted trip share by travel mode", "Percent of weighted trips", out,
         "03_mode_share.png", top=18, percent=True)
    figures.append("03_mode_share.png")

    mp_rows = sorted(set(a for a, _ in mp_counts))
    mp_cols = sorted(set(b for _, b in mp_counts))
    mp = pd.DataFrame(0.0, index=mp_rows, columns=mp_cols)
    for (a, b), v in mp_counts.items():
        mp.loc[a, b] = v
    mp = mp.div(mp.sum(axis=1).replace(0, np.nan), axis=0) * 100
    mp = mp.reindex([x for x in PURPOSE_ORDER if x in mp.index])
    heatmap(mp, "Mode mix within each trip purpose", out, "04_mode_by_purpose.png",
            "Mode group", "Destination purpose", fmt=".0f")
    figures.append("04_mode_by_purpose.png")

    top_purposes = pc.head(6).index
    hourly = pd.DataFrame(0.0, index=range(24), columns=top_purposes)
    for (p, h), v in hourly_counts.items():
        if p in hourly.columns:
            hourly.loc[h, p] = v
    hourly = hourly.div(hourly.sum(axis=0).replace(0, np.nan), axis=1) * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    for c in hourly.columns:
        ax.plot(hourly.index, hourly[c], marker="o", markersize=3, label=c)
    ax.set_title("When trips start, by purpose")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Percent of each purpose's daily trips")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)
    savefig(fig, out, "05_departure_time_by_purpose.png")
    figures.append("05_departure_time_by_purpose.png")

    summary = pd.DataFrame(index=[p for p in PURPOSE_ORDER if p in metric], columns=["Miles", "Minutes"], dtype=float)
    for p in summary.index:
        v = metric[p]
        summary.loc[p] = [v[0] / v[1] if v[1] else np.nan, v[2] / v[3] if v[3] else np.nan]
    x = np.arange(len(summary)); width = 0.42
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x-width/2, summary["Miles"], width, label="Average miles")
    ax.bar(x+width/2, summary["Minutes"], width, label="Average minutes")
    ax.set_xticks(x, summary.index, rotation=40, ha="right")
    ax.set_title("Weighted average trip distance and duration by purpose")
    ax.grid(axis="y", alpha=0.25); ax.legend()
    savefig(fig, out, "06_distance_duration_by_purpose.png")
    figures.append("06_distance_duration_by_purpose.png")

    labels = [m for m in MAJOR_MODES if distance_samples[m]]
    samples = [distance_samples[m] for m in labels]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(samples, tick_labels=labels, showfliers=False)
    ax.set_yscale("log"); ax.set_title("Trip distance distribution by major mode")
    ax.set_ylabel("Miles, log scale"); ax.tick_params(axis="x", rotation=30); ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "07_distance_distribution_by_mode.png")
    figures.append("07_distance_distribution_by_mode.png")

    sc = pd.Series(state_counts).sort_values(ascending=False)
    barh(sc, "Top household states by weighted trip volume", "Weighted trips", out,
         "08_weighted_trip_volume_by_state.png", top=20)
    figures.append("08_weighted_trip_volume_by_state.png")

    av = pd.Series({k: v[0] / v[1] for k, v in age_metric.items() if v[1] > 0}).reindex(AGE_ORDER).dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(av.index, av.values, marker="o")
    ax.set_title("Weighted average trip distance by traveler age")
    ax.set_xlabel("Age group"); ax.set_ylabel("Miles"); ax.grid(alpha=0.25)
    savefig(fig, out, "09_distance_by_age.png")
    figures.append("09_distance_by_age.png")

    write_summary(out, "DAYV2PUB", nrows, figures, [
        "Survey weights use WTTRDFIN.",
        "Origin and destination are activity-purpose categories because public-use data do not contain trip coordinates.",
        "The file is processed in chunks to keep memory use bounded.",
    ])


if __name__ == "__main__":
    main()
