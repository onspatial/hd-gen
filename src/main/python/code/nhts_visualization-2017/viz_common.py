from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.size": 15,
    "figure.dpi": 120,
    "savefig.dpi": 180,
    "axes.titlesize": 13,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
})

# 2017 NHTS public-use codebook mappings.
MODE_LABELS = {
    1: "Walk",
    2: "Bicycle",
    3: "Car",
    4: "SUV",
    5: "Van",
    6: "Pickup truck",
    7: "Golf cart / Segway",
    8: "Motorcycle / Moped",
    9: "RV / ATV / Snowmobile",
    10: "School bus",
    11: "Public / commuter bus",
    12: "Paratransit / Dial-a-ride",
    13: "Private / charter / shuttle bus",
    14: "Intercity bus",
    15: "Amtrak / commuter rail",
    16: "Subway / light rail / streetcar",
    17: "Taxi / rideshare",
    18: "Rental car / carshare",
    19: "Airplane",
    20: "Boat / ferry",
    97: "Other",
}

MODE_GROUPS = {
    1: "Walk",
    2: "Bicycle",
    3: "Private vehicle",
    4: "Private vehicle",
    5: "Private vehicle",
    6: "Private vehicle",
    7: "Private vehicle",
    8: "Private vehicle",
    9: "Private vehicle",
    10: "School bus",
    11: "Bus",
    12: "Paratransit",
    13: "Bus",
    14: "Bus",
    15: "Rail",
    16: "Rail",
    17: "Taxi / rideshare",
    18: "Private vehicle",
    19: "Air",
    20: "Ferry",
    97: "Other",
}

PURPOSE_SUMMARY = {
    1: "Home",
    10: "Work",
    20: "School/daycare/religious",
    30: "Medical/dental",
    40: "Shopping/errands",
    50: "Social/recreational",
    70: "Transport someone",
    80: "Meals",
    97: "Other",
}

# WHYFROM and WHYTO use detailed 2017 activity codes, not the summary codes.
ACTIVITY_PURPOSE_GROUP = {
    1: "Home",
    2: "Home",
    3: "Work",
    4: "Work",
    5: "Work",
    6: "Transport someone",
    7: "Other",
    8: "School/daycare/religious",
    9: "School/daycare/religious",
    10: "School/daycare/religious",
    11: "Shopping/errands",
    12: "Shopping/errands",
    13: "Meals",
    14: "Shopping/errands",
    15: "Social/recreational",
    16: "Social/recreational",
    17: "Social/recreational",
    18: "Medical/dental",
    19: "School/daycare/religious",
    97: "Other",
}

VEHICLE_TYPE = {
    1: "Car / station wagon",
    2: "Van",
    3: "SUV",
    4: "Pickup truck",
    5: "Other truck",
    6: "RV",
    7: "Motorcycle",
    97: "Other",
}

FUEL_TYPE = {
    1: "Gasoline",
    2: "Diesel",
    3: "Hybrid / electric / alternative",
    97: "Other",
}

INCOME_LABELS = {
    1: "< $10k",
    2: "$10-14k",
    3: "$15-24k",
    4: "$25-34k",
    5: "$35-49k",
    6: "$50-74k",
    7: "$75-99k",
    8: "$100-124k",
    9: "$125-149k",
    10: "$150-199k",
    11: "$200k+",
}

LIFECYCLE_LABELS = {
    1: "1 adult, no children",
    2: "2+ adults, no children",
    3: "1 adult, youngest 0-5",
    4: "2+ adults, youngest 0-5",
    5: "1 adult, youngest 6-15",
    6: "2+ adults, youngest 6-15",
    7: "1 adult, youngest 16-21",
    8: "2+ adults, youngest 16-21",
    9: "1 retired adult, no children",
    10: "2+ retired adults, no children",
}

STATE_FIPS = {
    1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT",
    10: "DE", 11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID",
    17: "IL", 18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA",
    23: "ME", 24: "MD", 25: "MA", 26: "MI", 27: "MN", 28: "MS",
    29: "MO", 30: "MT", 31: "NE", 32: "NV", 33: "NH", 34: "NJ",
    35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH", 40: "OK",
    41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD", 47: "TN",
    48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV",
    55: "WI", 56: "WY",
}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def positive_weight(s: pd.Series) -> pd.Series:
    w = numeric(s)
    return w.where(w > 0)


def code_to_label(s: pd.Series, mapping: Mapping[int, str], unknown: str = "Unknown") -> pd.Series:
    return numeric(s).map(mapping).fillna(unknown)


def activity_purpose_group(s: pd.Series) -> pd.Series:
    return code_to_label(s, ACTIVITY_PURPOSE_GROUP)


def weighted_counts(category: pd.Series, weight: pd.Series, drop_unknown: bool = False) -> pd.Series:
    d = pd.DataFrame({"category": category.astype("string"), "weight": positive_weight(weight)}).dropna()
    if drop_unknown:
        d = d[~d["category"].isin(["Unknown", "<NA>"])]
    return d.groupby("category", observed=True)["weight"].sum().sort_values(ascending=False)


def weighted_mean_by(df: pd.DataFrame, group: str, value: str, weight: str) -> pd.Series:
    d = df[[group, value, weight]].copy()
    d[value] = numeric(d[value])
    d[weight] = positive_weight(d[weight])
    d = d.dropna()
    d = d[d[value] >= 0]
    d["wv"] = d[value] * d[weight]
    g = d.groupby(group, observed=True)
    return (g["wv"].sum() / g[weight].sum()).sort_values(ascending=False)


def weighted_crosstab(row: pd.Series, col: pd.Series, weight: pd.Series, normalize: str | None = None) -> pd.DataFrame:
    d = pd.DataFrame({"row": row.astype("string"), "col": col.astype("string"), "weight": positive_weight(weight)}).dropna()
    t = d.pivot_table(index="row", columns="col", values="weight", aggfunc="sum", fill_value=0, observed=True)
    if normalize == "row":
        t = t.div(t.sum(axis=1).replace(0, np.nan), axis=0) * 100
    elif normalize == "all" and t.to_numpy().sum() > 0:
        t = t / t.to_numpy().sum() * 100
    return t


def savefig(fig: plt.Figure, out: Path, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(out / filename, bbox_inches="tight")
    plt.close(fig)


def barh(series: pd.Series, title: str, xlabel: str, out: Path, filename: str,
         top: int | None = None, percent: bool = False) -> None:
    s = series.dropna()
    if top is not None:
        s = s.head(top)
    if percent and s.sum() > 0:
        s = s / s.sum() * 100
    s = s.sort_values()
    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.42 * len(s) + 1.5)))
    ax.barh(s.index.astype(str), s.values)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    savefig(fig, out, filename)


def heatmap(table: pd.DataFrame, title: str, out: Path, filename: str,
            xlabel: str = "", ylabel: str = "", fmt: str = ".1f",
            annotate: bool = True) -> None:
    if table.empty:
        return
    fig_w = max(7, 0.75 * len(table.columns) + 3)
    fig_h = max(5, 0.55 * len(table.index) + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    arr = table.to_numpy(dtype=float)
    im = ax.imshow(arr, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(table.columns)), table.columns.astype(str), rotation=45, ha="right")
    ax.set_yticks(range(len(table.index)), table.index.astype(str))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.8)
    if annotate and arr.size <= 140:
        threshold = np.nanmax(arr) * 0.55 if np.isfinite(arr).any() else 0
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                v = arr[i, j]
                if np.isfinite(v):
                    ax.text(j, i, format(v, fmt), ha="center", va="center", fontsize=7,
                            color="white" if v > threshold else "black")
    savefig(fig, out, filename)


def parse_hhmm(s: pd.Series) -> pd.Series:
    raw = s.astype("string").str.replace(":", "", regex=False).str.extract(r"(\d{1,4})", expand=False)
    n = pd.to_numeric(raw, errors="coerce")
    h = np.floor(n / 100)
    m = n % 100
    valid = (h >= 0) & (h <= 27) & (m >= 0) & (m < 60)
    return (h + m / 60).where(valid)


def age_group(s: pd.Series) -> pd.Series:
    a = numeric(s)
    bins = [-0.1, 4, 15, 24, 34, 44, 54, 64, 74, 89, np.inf]
    labels = ["0-4", "5-15", "16-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-89", "90+"]
    return pd.cut(a, bins=bins, labels=labels)


def write_summary(out: Path, dataset: str, rows: int, figures: Iterable[str], notes: Iterable[str] = ()) -> None:
    lines = [f"Dataset: {dataset}", "Survey year: 2017", f"Rows read: {rows:,}", "", "Figures:"]
    lines.extend(f"- {x}" for x in figures)
    if notes:
        lines += ["", "Notes:"] + [f"- {n}" for n in notes]
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
