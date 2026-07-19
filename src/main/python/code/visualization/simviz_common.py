from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shlex
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 170,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
})

ACTIVITY_ORDER = ["Home", "Work", "Restaurant", "Recreation"]
ACTIVITY_COLORS = {
    "Home": "#1f77b4", "Work": "#ff7f0e", "Restaurant": "#2ca02c", "Recreation": "#d62728",
}

PLACE_MAP = {
    "AtHome": "Home", "Apartment": "Home",
    "AtWork": "Work", "Workplace": "Work",
    "AtRestaurant": "Restaurant", "Restaurant": "Restaurant",
    "AtRecreation": "Recreation", "Pub": "Recreation",
    "Classroom": "Other",
}
TRAVEL_COLUMNS = [
    "step", "agentId", "travelStartTime", "travelStartPlaceType", "travelStartLocationId",
    "travelEndTime", "travelEndLocationId", "travelEndPlaceType",
    "intendedTravelEndLocationId", "intendedTravelEndPlaceType", "purpose",
    "checkInTime", "checkOutTime", "maxPeople", "minPeople",
    "moneyBalanceBefore", "moneyBalanceAfter", "moneyOffset", "eventSummary1", "eventSummary2",
]
FINANCIAL_COLUMNS = ["step", "agentId", "simulationTime", "transactionType", "amount", "location"]
FIN_ATTR_COLUMNS = [
    "step", "agentId", "simulationTime", "age", "homeLocation", "workLocation",
    "hourlyRate", "shelterCost", "balance", "employed", "hasFamily", "educationLevel",
]
INTERVENTION_COLUMNS = ["step", "agentId", "simulationTime", "interventionType", "value", "location", "rate"]
VISITOR_COLUMNS = ["step", "simulationTime", "venueId", "visitorAgeMean", "visitorAgeMax", "interestSet"]
TRAJECTORY_COLUMNS = ["fromAgent", "toAgent", "simulationTime", "pathNodes"]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def savefig(fig: plt.Figure, out: Path, name: str) -> str:
    fig.tight_layout()
    fig.savefig(out / name, bbox_inches="tight")
    plt.close(fig)
    return name


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def parse_point_series(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    ex = s.astype("string").str.extract(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
    return pd.to_numeric(ex[0], errors="coerce"), pd.to_numeric(ex[1], errors="coerce")


def polygon_centroid_approx(value: object) -> tuple[float, float]:
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", str(value))
    if len(nums) < 4:
        return (math.nan, math.nan)
    arr = np.asarray([float(x) for x in nums], dtype=float).reshape(-1, 2)
    return float(np.nanmean(arr[:, 0])), float(np.nanmean(arr[:, 1]))


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df.loc[:, ~df.columns.str.match(r"^Unnamed")]


def read_tsv_with_trailing_delimiter(path: Path, **kwargs) -> pd.DataFrame:
    """Read model TSVs that sometimes end every row with an extra tab.

    Without ``index_col=False``, pandas can silently promote the first field to
    the index when data rows have one more trailing empty field than the header.
    """
    return clean_columns(pd.read_csv(path, sep="\t", index_col=False, **kwargs))


def infer_time_window(times: pd.Series, warmup_days: int) -> tuple[pd.Series, dict]:
    t = pd.to_datetime(times, errors="coerce")
    valid = t.dropna()
    if valid.empty:
        return pd.Series(True, index=times.index), {"start": None, "end": None, "days": None, "warmup_applied": False}
    start, end = valid.min(), valid.max()
    span_days = max((end - start).total_seconds() / 86400.0, 0.0)
    apply = warmup_days > 0 and span_days > warmup_days + 2
    cutoff = start + pd.Timedelta(days=warmup_days) if apply else start
    mask = t.ge(cutoff)
    return mask.fillna(False), {
        "start": str(start), "end": str(end), "days": span_days,
        "warmup_applied": bool(apply), "analysis_start": str(cutoff), "warmup_days": warmup_days,
    }


def load_reference(path: Path | None = None) -> dict:
    p = path or Path(__file__).with_name("realworld_reference.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def activity_label(s: pd.Series) -> pd.Series:
    return s.astype("string").map(PLACE_MAP).fillna("Other")


def line_plot(series: pd.Series, title: str, ylabel: str, out: Path, name: str, xlabel: str = "") -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(series.index, series.values, marker="o", markersize=3)
   #  ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.grid(alpha=0.25)
    if len(series) > 12:
        ax.tick_params(axis="x", rotation=35)
    return savefig(fig, out, name)


def bar_plot(series: pd.Series, title: str, ylabel: str, out: Path, name: str, horizontal: bool = False, percent: bool = False, top: int | None = None) -> str:
    s = series.dropna().copy()
    if top:
        s = s.sort_values(ascending=False).head(top)
    if percent and s.sum() != 0:
        s = s / s.sum() * 100
    fig, ax = plt.subplots(figsize=(10, max(4.5, 0.38 * len(s) + 1.8) if horizontal else 5.5))
    if horizontal:
        s = s.sort_values()
        ax.barh(s.index.astype(str), s.values)
        ax.set_xlabel(ylabel)
    else:
        ax.bar(s.index.astype(str), s.values)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=35)
   #  ax.set_title(title); ax.grid(axis="x" if horizontal else "y", alpha=0.25)
    return savefig(fig, out, name)


def heatmap(table: pd.DataFrame, title: str, out: Path, name: str, xlabel: str = "", ylabel: str = "", fmt: str = ".1f") -> str:
    if table.empty:
        return ""
    fig, ax = plt.subplots(figsize=(max(7, 0.75 * len(table.columns) + 3), max(5, 0.48 * len(table.index) + 2.5)))
    a = table.to_numpy(dtype=float)
    im = ax.imshow(a, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(table.columns)), table.columns.astype(str), rotation=45, ha="right")
    ax.set_yticks(range(len(table.index)), table.index.astype(str))
   #  ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    fig.colorbar(im, ax=ax, shrink=0.8)
    if a.size <= 120 and np.isfinite(a).any():
        threshold = np.nanmax(a) * 0.55
        for i in range(a.shape[0]):
            for j in range(a.shape[1]):
                if np.isfinite(a[i, j]):
                    ax.text(j, i, format(a[i, j], fmt), ha="center", va="center", fontsize=7,
                            color="white" if a[i, j] > threshold else "black")
    return savefig(fig, out, name)


def histogram(values: pd.Series | np.ndarray, title: str, xlabel: str, out: Path, name: str, bins: int = 40, logx: bool = False) -> str:
    a = pd.to_numeric(pd.Series(values), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if a.empty:
        return ""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(a, bins=bins)
    if logx:
        ax.set_xscale("log")
   #  ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel("Records"); ax.grid(axis="y", alpha=0.25)
    return savefig(fig, out, name)


def scatter(x: pd.Series, y: pd.Series, title: str, xlabel: str, ylabel: str, out: Path, name: str, sample: int = 20000) -> str:
    d = pd.DataFrame({"x": numeric(x), "y": numeric(y)}).dropna()
    if d.empty:
        return ""
    if len(d) > sample:
        d = d.sample(sample, random_state=42)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(d.x, d.y, s=8, alpha=0.35)
   #  ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.grid(alpha=0.2)
    return savefig(fig, out, name)


def spatial_scatter(x: pd.Series, y: pd.Series, title: str, out: Path, name: str, c: pd.Series | None = None, sample: int = 50000) -> str:
    d = pd.DataFrame({"x": numeric(x), "y": numeric(y)})
    if c is not None:
        d["c"] = c.astype("string")
    d = d.dropna(subset=["x", "y"])
    if len(d) > sample:
        d = d.sample(sample, random_state=42)
    fig, ax = plt.subplots(figsize=(8, 8))
    if c is None:
        ax.hexbin(d.x, d.y, gridsize=70, mincnt=1, bins="log")
    else:
        for label, g in d.groupby("c", observed=True):
            ax.scatter(g.x, g.y, s=8, alpha=0.45, label=str(label))
        ax.legend(markerscale=2)
    ax.set_aspect("equal", adjustable="box");#  ax.set_title(title); ax.set_xlabel("Projected X"); ax.set_ylabel("Projected Y")
    return savefig(fig, out, name)


def write_dataset_summary(out: Path, dataset: str, figures: Sequence[str], insights: Sequence[str], meta: dict | None = None) -> None:
    write_text(out / "insights.txt", "\n".join(f"- {x}" for x in insights if x))
    payload = {"dataset": dataset, "figures": [x for x in figures if x], "insights": list(insights), "meta": meta or {}}
    (out / "summary.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def companion_root(input_path: Path, data_root: Path | None) -> Path:
    if data_root:
        return data_root
    return input_path.parent.parent if input_path.parent.name in {"logs", "qois"} else input_path.parent


def resolve_input(root: Path, relative: str) -> Path:
    p = root / relative
    if p.exists():
        return p
    p2 = root / Path(relative).name
    if p2.exists():
        return p2
    raise FileNotFoundError(f"Could not find {relative} under {root}")


def read_headerless(path: Path, names: Sequence[str], sep: str = ",", **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, sep=sep, header=None, names=list(names), **kwargs)


def analyze_agent_characteristics(path: Path, out: Path, **_: object) -> None:
    df = clean_columns(pd.read_csv(path, sep="\t"))
    figs: list[str] = []
    figs.append(bar_plot(df["family:numberOfPeople"].value_counts().sort_index(), "Household size assigned to agents", "Agents", out, "01_family_size.png"))
    education_cencus =  {
      "Low": 10.8,
      "HighSchoolOrCollege": 54.3,
      "Bachelors": 21.2,
      "Graduate": 13.7
    }
    figs.append(bar_plot(pd.Series(education_cencus), "Education distribution (Census)", "Percent", out, "02_education_census.png", horizontal=True))
    figs.append(bar_plot(df["educationLevel"].value_counts(), "Education distribution", "Agents", out, "02_education.png", horizontal=True, percent=True))
    
    education_simulation = df["educationLevel"].value_counts().to_dict()
    # make it percent
    total = sum(education_simulation.values())
    education_simulation = {k: round(v / total * 100, 4) for k, v in education_simulation.items()}
    both = {k: (education_simulation.get(k, 0), education_cencus.get(k, 0)) for k in set(education_simulation) | set(education_cencus)}




    figs.append(bar_plot(df["interest"].value_counts().sort_index(), "Primary interest distribution", "Agents", out, "03_interest.png", percent=True))
    figs.append(histogram(df["joviality"], "Joviality distribution", "Joviality", out, "04_joviality.png"))
    j = df.groupby("educationLevel")["joviality"].mean().sort_values()
    figs.append(bar_plot(j, "Mean joviality by education", "Mean joviality", out, "05_joviality_by_education.png", horizontal=True))
    cols = [c for c in df.columns if c.startswith("foodNeed:")]
    corr = df[cols].apply(pd.to_numeric, errors="coerce").corr()
    figs.append(heatmap(corr, "Food-need parameter correlations", out, "06_food_need_correlations.png"))
    kids = df["family:haveKids"].astype(str).str.lower().eq("true").mean() * 100
    insights = [
        f"{kids:.1f}% of agents are assigned to families with children.",
        f"The median assigned family size is {numeric(df['family:numberOfPeople']).median():.0f}.",
        "Large differences across education or interest groups can reveal initialization bias before dynamic behavior begins.",
    ]
    write_dataset_summary(out, path.name, figs, insights, {"rows": len(df)})


def analyze_agent_state(path: Path, out: Path, warmup_days: int = 30, chunksize: int = 500000, **_: object) -> None:
    first = pd.read_csv(path, sep="\t", nrows=1)
    start = pd.to_datetime(first["simulationTime"].iloc[0])
    with path.open("rb") as f:
        f.seek(0, 2); pos = max(f.tell() - 2, 0)
        while pos > 0:
            f.seek(pos)
            if f.read(1) == b"\n": break
            pos -= 1
        last_line = f.readline().decode("utf-8", errors="replace")
    last_parts = last_line.rstrip("\n\t").split("\t")
    end = pd.to_datetime(last_parts[1]) if len(last_parts) > 1 else start
    span = (end - start).total_seconds() / 86400
    cutoff = start + pd.Timedelta(days=warmup_days) if warmup_days and span > warmup_days + 2 else start

    last_pos: dict[int, tuple[float, float]] = {}
    daily_frames: list[pd.DataFrame] = []
    hourly_frames: list[pd.DataFrame] = []
    dow_frames: list[pd.DataFrame] = []
    stat_frames: list[pd.DataFrame] = []
    samples: list[pd.DataFrame] = []
    representative = set(range(0, 1000, 100))
    rep_tracks = defaultdict(list)
    rows = 0

    for ch in pd.read_csv(path, sep="\t", chunksize=chunksize, usecols=["simulationTime", "location", "agentId"]):
        ch["time"] = pd.to_datetime(ch.simulationTime, errors="coerce")
        ch = ch[ch.time.ge(cutoff)].copy()
        if ch.empty:
            continue
        ch["x"], ch["y"] = parse_point_series(ch.location)
        ch["agentId"] = numeric(ch.agentId)
        ch = ch.dropna(subset=["x", "y", "time", "agentId"])
        ch["agentId"] = ch.agentId.astype(int)
        rows += len(ch)

        prev_x = ch.groupby("agentId", sort=False).x.shift()
        prev_y = ch.groupby("agentId", sort=False).y.shift()
        first_mask = prev_x.isna()
        if first_mask.any():
            aids = ch.loc[first_mask, "agentId"]
            prev_x.loc[first_mask] = [last_pos.get(int(a), (math.nan, math.nan))[0] for a in aids]
            prev_y.loc[first_mask] = [last_pos.get(int(a), (math.nan, math.nan))[1] for a in aids]
        dist_m = np.hypot(ch.x.to_numpy() - prev_x.to_numpy(), ch.y.to_numpy() - prev_y.to_numpy())
        dist_m = np.where(np.isfinite(dist_m), dist_m, 0.0)
        ch["dist_km"] = dist_m / 1000.0
        ch["moved"] = dist_m > 10.0
        ch["date"] = ch.time.dt.strftime("%Y-%m-%d")
        ch["hour"] = ch.time.dt.hour
        ch["dow"] = ch.time.dt.day_name().str[:3]

        daily_frames.append(ch.groupby(["date", "agentId"], observed=True).dist_km.sum().rename("km").reset_index())
        hourly_frames.append(ch.groupby("hour", observed=True).agg(distance_km=("dist_km", "sum"), moves=("moved", "sum"), observations=("moved", "size")).reset_index())
        dow_frames.append(ch.groupby(["dow", "hour"], observed=True).agg(moves=("moved", "sum"), observations=("moved", "size")).reset_index())
        tmp = ch.assign(x2=ch.x * ch.x, y2=ch.y * ch.y).groupby("agentId", observed=True).agg(sx=("x", "sum"), sy=("y", "sum"), sx2=("x2", "sum"), sy2=("y2", "sum"), n=("x", "size")).reset_index()
        stat_frames.append(tmp)

        stride = max(1, len(ch) // 5000)
        samples.append(ch.iloc[::stride][["x", "y"]].head(5000))
        for aid, g in ch[ch.agentId.isin(representative)].groupby("agentId", observed=True):
            remain = 5000 - len(rep_tracks[int(aid)])
            if remain > 0:
                rep_tracks[int(aid)].extend(g[["x", "y"]].iloc[::max(1, len(g)//max(remain,1))].head(remain).itertuples(index=False, name=None))
        tails = ch.groupby("agentId", sort=False).tail(1)
        last_pos.update({int(a): (float(x), float(y)) for a, x, y in tails[["agentId", "x", "y"]].itertuples(index=False, name=None)})

    figs: list[str] = []
    if samples:
        pts = pd.concat(samples, ignore_index=True)
        figs.append(spatial_scatter(pts.x, pts.y, "Agent location density", out, "01_location_density.png"))

    if daily_frames:
        da = pd.concat(daily_frames, ignore_index=True).groupby(["date", "agentId"], observed=True).km.sum().reset_index()
        daily_mean = da.groupby("date").km.mean()
        figs.append(line_plot(daily_mean, "Mean movement distance per agent-day", "Kilometers", out, "02_daily_distance_per_agent.png", "Date"))
        figs.append(histogram(da.km, "Distribution of movement distance per agent-day", "Kilometers per day", out, "03_agent_day_distance_distribution.png", bins=50))
    else:
        da = pd.DataFrame(columns=["date", "agentId", "km"])

    hourly = pd.concat(hourly_frames, ignore_index=True).groupby("hour").sum() if hourly_frames else pd.DataFrame()
    if not hourly.empty:
        moving = 100 * hourly.moves / hourly.observations
        figs.append(line_plot(moving, "Share of five-minute observations with movement", "Moving observations (%)", out, "04_hourly_mobility_profile.png", "Hour"))

    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if dow_frames:
        dg = pd.concat(dow_frames, ignore_index=True).groupby(["dow", "hour"]).sum()
        table = pd.DataFrame(index=order, columns=range(24), dtype=float)
        for (d, h), r in dg.iterrows():
            table.loc[d, int(h)] = 100 * r.moves / r.observations if r.observations else np.nan
        figs.append(heatmap(table, "Mobility by weekday and hour", out, "05_weekday_hour_mobility.png", "Hour", "Day", ".0f"))

    rg = pd.Series(dtype=float)
    if stat_frames:
        st = pd.concat(stat_frames, ignore_index=True).groupby("agentId").sum()
        var = (st.sx2 / st.n - (st.sx / st.n) ** 2).clip(lower=0) + (st.sy2 / st.n - (st.sy / st.n) ** 2).clip(lower=0)
        rg = np.sqrt(var) / 1000.0
        figs.append(histogram(rg, "Radius of gyration across agents", "Kilometers", out, "06_radius_of_gyration.png", bins=40))

    if rep_tracks:
        fig, ax = plt.subplots(figsize=(8, 8))
        for aid, arr in rep_tracks.items():
            a = np.asarray(arr)
            if len(a): ax.plot(a[:, 0], a[:, 1], linewidth=0.8, alpha=0.7, label=str(aid))
        ax.set_aspect("equal", adjustable="box");#  ax.set_title("Representative agent trajectories"); ax.set_xlabel("Projected X"); ax.set_ylabel("Projected Y"); ax.legend(ncol=2)
        figs.append(savefig(fig, out, "07_representative_trajectories.png"))

    mean_km = float(da.km.mean()) if len(da) else math.nan
    med_rg = float(rg.median()) if len(rg) else math.nan
    insights = [
        f"The analyzed period spans {span:.1f} days; warm-up exclusion was {'applied' if cutoff > start else 'not applied because the sample is shorter than the requested warm-up'}.",
        f"Mean observed movement is {mean_km:.2f} km per agent-day, based on straight-line displacement between five-minute points.",
        f"The typical radius of gyration is {med_rg:.2f} km, a compact measure of each agent's activity space.",
        "For yearly runs, the weekday-hour heatmap and daily rate chart reveal seasonality without inflating totals by run length.",
    ]
    write_dataset_summary(out, path.name, figs, insights, {"rows_analyzed": rows, "start": str(start), "end": str(end), "analysis_start": str(cutoff)})

def load_location_lookup(root: Path) -> dict[tuple[str, int], tuple[float, float]]:
    specs = {
        "Home": "logs/ApartmentTable.tsv", "Work": "logs/WorkplaceTable.tsv",
        "Restaurant": "logs/RestaurantTable.tsv", "Recreation": "logs/PubTable.tsv",
        "Other": "logs/ClassroomTable.tsv",
    }
    lookup = {}
    for typ, rel in specs.items():
        p = root / rel
        if not p.exists(): continue
        d = pd.read_csv(p, sep="\t")
        x,y=parse_point_series(d["location"])
        for i,xx,yy in zip(numeric(d["id"]),x,y):
            if pd.notna(i) and pd.notna(xx) and pd.notna(yy): lookup[(typ,int(i))]=(float(xx),float(yy))
    return lookup


def analyze_travel_journal(path: Path, out: Path, warmup_days: int = 30, data_root: Path | None = None, reference_region: str = "georgia", chunksize: int = 250000, **_: object) -> None:
    """Analyze trips with bounded memory, including year-long journals."""
    read_kwargs = dict(header=None, names=TRAVEL_COLUMNS, low_memory=False, chunksize=chunksize)
    start = end = None
    for ch in pd.read_csv(path, usecols=["travelStartTime"], **read_kwargs):
        t = pd.to_datetime(ch["travelStartTime"], errors="coerce").dropna()
        if t.empty:
            continue
        cmin, cmax = t.min(), t.max()
        start = cmin if start is None else min(start, cmin)
        end = cmax if end is None else max(end, cmax)
    if start is None or end is None:
        write_dataset_summary(out, path.name, [], ["No valid travel timestamps were found."], {"rows": 0})
        return
    span_days = max((end - start).total_seconds() / 86400.0, 0.0)
    warmup_applied = warmup_days > 0 and span_days > warmup_days + 2
    cutoff = start + pd.Timedelta(days=warmup_days) if warmup_applied else start
    meta = {"start": str(start), "end": str(end), "days": span_days, "warmup_applied": warmup_applied,
            "analysis_start": str(cutoff), "warmup_days": warmup_days}

    root = companion_root(path, data_root)
    lookup = load_location_lookup(root)
    od = pd.DataFrame(0, index=ACTIVITY_ORDER, columns=ACTIVITY_ORDER, dtype=np.int64)
    hour_dest = pd.DataFrame(0, index=range(24), columns=ACTIVITY_ORDER, dtype=np.int64)
    dest_counts: Counter[str] = Counter()
    purpose_counts: Counter[str] = Counter()
    hour_counts: Counter[int] = Counter()
    daily_agent_frames: list[pd.DataFrame] = []
    samples: list[pd.DataFrame] = []
    distance_sum: Counter[str] = Counter()
    distance_n: Counter[str] = Counter()
    distance_total = 0.0
    distance_total_n = 0
    duration_total = 0.0
    duration_n = 0
    agents: set[int] = set()
    dates: set[str] = set()
    rows = 0

    for chunk_idx, df in enumerate(pd.read_csv(path, **read_kwargs)):
        for c in ["travelStartTime", "travelEndTime", "checkInTime", "checkOutTime"]:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        df = df[df.travelStartTime.ge(cutoff)].copy()
        if df.empty:
            continue
        df["origin"] = activity_label(df.travelStartPlaceType)
        df["destination"] = activity_label(df.travelEndPlaceType)
        df["date"] = df.travelStartTime.dt.strftime("%Y-%m-%d")
        df["hour"] = df.travelStartTime.dt.hour
        df["tripMinutes"] = (df.travelEndTime - df.travelStartTime).dt.total_seconds() / 60
        df["dwellMinutes"] = (df.checkOutTime - df.checkInTime).dt.total_seconds() / 60
        df["agentId"] = numeric(df.agentId)
        rows += len(df)
        agents.update(df.agentId.dropna().astype(int).unique().tolist())
        dates.update(df.date.dropna().unique().tolist())

        od = od.add(pd.crosstab(df.origin, df.destination).reindex(index=ACTIVITY_ORDER, columns=ACTIVITY_ORDER, fill_value=0), fill_value=0).astype(np.int64)
        hour_dest = hour_dest.add(pd.crosstab(df.hour, df.destination).reindex(index=range(24), columns=ACTIVITY_ORDER, fill_value=0), fill_value=0).astype(np.int64)
        dest_counts.update(df.destination.value_counts().to_dict())
        purpose_counts.update(df.purpose.dropna().astype(str).value_counts().to_dict())
        hour_counts.update(df.hour.dropna().astype(int).value_counts().to_dict())
        daily_agent_frames.append(df.dropna(subset=["agentId"]).groupby(["date", "agentId"]).size().rename("trips").reset_index())

        valid_duration = df.tripMinutes.replace([np.inf, -np.inf], np.nan).dropna()
        duration_total += float(valid_duration.sum()); duration_n += int(valid_duration.size)

        start_ids = numeric(df.travelStartLocationId)
        end_ids = numeric(df.travelEndLocationId)
        start_coords = [lookup.get((typ, int(i))) if pd.notna(i) else None for typ, i in zip(df.origin, start_ids)]
        end_coords = [lookup.get((typ, int(i))) if pd.notna(i) else None for typ, i in zip(df.destination, end_ids)]
        dist = np.fromiter((math.hypot(a[0]-b[0], a[1]-b[1]) / 1609.344 if a and b else math.nan for a, b in zip(start_coords, end_coords)), dtype=float, count=len(df))
        df["straightLineMiles"] = dist
        valid_dist = np.isfinite(dist)
        if valid_dist.any():
            distance_total += float(np.nansum(dist)); distance_total_n += int(valid_dist.sum())
            for dest, g in df.loc[valid_dist].groupby("destination"):
                vals = g.straightLineMiles.dropna()
                distance_sum[str(dest)] += float(vals.sum()); distance_n[str(dest)] += int(vals.size)

        take = min(len(df), max(3000, min(20000, 200000 // max(1, math.ceil(max(rows, 1) / chunksize)))))
        if take > 0:
            samples.append(df.sample(n=take, random_state=42 + chunk_idx)[["destination", "tripMinutes", "dwellMinutes", "straightLineMiles"]])

    figs: list[str] = []
    od_pct = od.div(od.sum(axis=1).replace(0, np.nan), axis=0) * 100
    figs.append(heatmap(od_pct, "Simulation destination conditional on origin", out, "01_origin_destination_flow.png", "Destination", "Origin", ".0f"))
    dest_series = pd.Series(dest_counts, dtype=float).reindex(ACTIVITY_ORDER).fillna(0)
    figs.append(bar_plot(dest_series, "Destination activity share", "Trips", out, "02_destination_share.png", percent=True))
    figs.append(bar_plot(pd.Series(purpose_counts, dtype=float), "Travel purpose share", "Trips", out, "03_purpose_share.png", horizontal=True, percent=True))
    hp = hour_dest.div(hour_dest.sum(axis=0).replace(0, np.nan), axis=1) * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    for c in hp.columns:
        ax.plot(hp.index, hp[c], marker="o", markersize=3, label=c, color=ACTIVITY_COLORS.get(c, None))
    ax.set_title(""); ax.set_xlabel("Hour of day"); ax.set_ylabel("Purpose of Daily Trips (%)"); ax.grid(alpha=.25); ax.legend()
    figs.append(savefig(fig, out, "04_departure_time_by_destination.png"))

    if daily_agent_frames:
        apd = pd.concat(daily_agent_frames, ignore_index=True).groupby(["date", "agentId"]).trips.sum().reset_index()
        daily_agents = apd.groupby("date").trips.mean()
        figs.append(line_plot(daily_agents, "Mean trips per active agent-day", "Trips", out, "05_trips_per_agent_day.png", "Date"))
        figs.append(histogram(apd.trips, "Distribution of trips per active agent-day", "Trips", out, "06_trips_per_agent_day_distribution.png", bins=20))
    else:
        apd = pd.DataFrame(columns=["date", "agentId", "trips"])

    sample = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame(columns=["destination", "tripMinutes", "dwellMinutes", "straightLineMiles"])
    med = sample.groupby("destination").tripMinutes.median().reindex(ACTIVITY_ORDER).dropna()
    figs.append(bar_plot(med, "Median trip duration by destination (sampled for scale)", "Minutes", out, "07_trip_duration_by_destination.png"))
    dwell = sample.groupby("destination").dwellMinutes.median().reindex(ACTIVITY_ORDER).dropna()
    figs.append(bar_plot(dwell, "Median activity duration at destination (sampled for scale)", "Minutes", out, "08_dwell_duration_by_destination.png"))
    if sample.straightLineMiles.notna().any():
        figs.append(histogram(sample.loc[sample.straightLineMiles > 0, "straightLineMiles"], "Straight-line trip distance (sampled for scale)", "Miles", out, "09_trip_distance_distribution.png", bins=45))
    mean_dist_dest = pd.Series({k: distance_sum[k] / distance_n[k] for k in distance_n if distance_n[k]})
    if not mean_dist_dest.empty:
        figs.append(bar_plot(mean_dist_dest.reindex(ACTIVITY_ORDER).dropna(), "Mean straight-line distance by destination", "Miles", out, "10_distance_by_destination.png"))

    ref = load_reference().get(reference_region, {})
    reference_year = int(ref.get("survey_year", 2017)) if ref else 2017
    sim_share = dest_series / max(dest_series.sum(), 1) * 100
    sim_trips = rows / (max(len(agents), 1) * max(len(dates), 1))
    mean_trip_minutes = duration_total / max(duration_n, 1)
    mean_trip_miles = distance_total / max(distance_total_n, 1) if distance_total_n else math.nan
    
    if ref:
        real = pd.Series(ref["destination_share_pct"]).reindex(ACTIVITY_ORDER)
        comp = pd.DataFrame({"Simulation": sim_share, f"NHTS {reference_year}": real})
        fig, ax = plt.subplots(figsize=(10, 5)); comp.plot(kind="bar", ax=ax);#  ax.set_title(f"Destination share: simulation vs {reference_year} NHTS ({reference_region.title()})"); ax.set_ylabel("Trips (%)"); ax.tick_params(axis="x", rotation=25); ax.grid(axis="y", alpha=.25)
        figs.append(savefig(fig, out, "11_destination_share_vs_nhts.png"))
        sim_global = od / max(od.to_numpy().sum(), 1) * 100
        real_od = pd.DataFrame(0.0, index=ACTIVITY_ORDER, columns=ACTIVITY_ORDER)
        for i in ACTIVITY_ORDER:
            for j in ACTIVITY_ORDER:
                real_od.loc[i, j] = ref["od_share_pct"].get(f"{i}->{j}", 0)
        figs.append(heatmap(sim_global - real_od, "Simulation minus NHTS origin-destination share (percentage points)", out, "12_od_difference_vs_nhts.png", "Destination", "Origin", "+.1f"))
        sim_h = pd.Series(hour_counts, dtype=float).reindex(range(24), fill_value=0); sim_h = sim_h / max(sim_h.sum(), 1) * 100
        real_h = pd.Series({int(k): v for k, v in ref["departure_hour_share_pct"].items()}).reindex(range(24), fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 5)); ax.plot(sim_h.index, sim_h, label="Simulation", marker="o"); ax.plot(real_h.index, real_h, label=f"NHTS {reference_year}", marker="o");#  ax.set_title("Departure-time profile vs NHTS"); ax.set_xlabel("Hour"); ax.set_ylabel("Trips (%)"); ax.legend(); ax.grid(alpha=.25)
        figs.append(savefig(fig, out, "13_departure_time_vs_nhts.png"))
        benchmark = pd.Series({"Trips/person-day": sim_trips, "Mean trip minutes": mean_trip_minutes, "Mean trip miles": mean_trip_miles})
        real_benchmark = pd.Series({"Trips/person-day": ref.get("weighted_trips_per_person_day", np.nan), "Mean trip minutes": ref.get("mean_trip_minutes", np.nan), "Mean trip miles": ref.get("mean_trip_miles", np.nan)})
        ratio = (benchmark / real_benchmark * 100).dropna()
        figs.append(bar_plot(ratio, f"Simulation level relative to {reference_year} NHTS benchmark", f"{reference_year} NHTS = 100", out, "14_level_relative_to_nhts.png"))
   
        

    insights = [
        f"The simulation produces {sim_trips:.2f} trips per agent-day when all agents and analyzed dates are used as the denominator.",
        f"Restaurants account for {sim_share.get('Restaurant', 0):.1f}% of simulated destinations and recreation accounts for {sim_share.get('Recreation', 0):.1f}%.",
        f"Mean simulated travel time is {mean_trip_minutes:.1f} minutes; the {reference_year} NHTS {reference_region} mean benchmark is {ref.get('mean_trip_minutes', float('nan')):.1f} minutes." if ref else "Trip-duration comparison was unavailable because no reference file was found.",
        "The simulation has no shopping, school, medical, or escort activity classes, so NHTS 'Other' should be treated as a structural gap rather than a calibration failure.",
    ]
    if distance_total_n and ref:
        insights.append(f"Mean straight-line distance is {mean_trip_miles:.2f} miles versus {ref['mean_trip_miles']:.2f} miles in the {reference_year} NHTS; straight-line distance is expected to be lower than network distance.")
    write_dataset_summary(out, path.name, figs, insights, {**meta, "rows": rows, "reference_region": reference_region,
                                                          "sample_rows": len(sample), "unique_agents": len(agents), "unique_dates": len(dates)})

def analyze_checkin(path: Path, out: Path, warmup_days: int = 30, reference_region: str = "georgia", **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    mask,meta=infer_time_window(df.CheckinTime,warmup_days); df=df[mask].copy(); df['time']=pd.to_datetime(df.CheckinTime,errors='coerce')
    df['activity']=activity_label(df.VenueType); df['date']=df.time.dt.date.astype(str); df['hour']=df.time.dt.hour; df['dow']=df.time.dt.day_name().str[:3]
    figs=[]
    figs.append(bar_plot(df.activity.value_counts().reindex(ACTIVITY_ORDER).fillna(0),"Check-in share by venue activity","Check-ins",out,"01_activity_share.png",percent=True))
    daily=df.groupby('date').size()/max(df.UserId.nunique(),1)
    figs.append(line_plot(daily,"Check-ins per agent by day","Check-ins per agent",out,"02_daily_checkins_per_agent.png","Date"))
    ht=pd.crosstab(df.hour,df.activity).reindex(index=range(24),columns=ACTIVITY_ORDER,fill_value=0)
    fig,ax=plt.subplots(figsize=(11,6));
    for c in ht.columns: ax.plot(ht.index,ht[c]/max(ht[c].sum(),1)*100,marker='o',markersize=3,label=c)
   #  ax.set_title('Check-in time by activity'); ax.set_xlabel('Hour'); ax.set_ylabel('Within-activity share (%)'); ax.legend(); ax.grid(alpha=.25)
    figs.append(savefig(fig,out,'03_hourly_activity_profile.png'))
    # sequence flows
    d=df.sort_values(['UserId','time']).copy(); d['next_activity']=d.groupby('UserId').activity.shift(-1)
    flow=pd.crosstab(d.activity,d.next_activity).reindex(index=ACTIVITY_ORDER,columns=ACTIVITY_ORDER,fill_value=0)
    flow=flow.div(flow.sum(axis=1).replace(0,np.nan),axis=0)*100
    figs.append(heatmap(flow,'Next check-in activity conditional on current activity',out,'04_activity_transition_flow.png','Next activity','Current activity','.0f'))
    figs.append(spatial_scatter(df.X,df.Y,'Spatial density of check-ins',out,'05_checkin_density.png'))
    figs.append(bar_plot(df.VenueId.value_counts(),"Most visited venues","Check-ins",out,"06_top_venues.png",horizontal=True,top=20))
    visits=df.groupby(['date','UserId']).size()
    figs.append(histogram(visits,'Check-ins per agent-day','Check-ins',out,'07_checkins_per_agent_day_distribution.png',bins=25))
    unique=df.groupby('UserId').VenueId.nunique()
    figs.append(histogram(unique,'Unique venues visited per agent','Venues',out,'08_unique_venues_per_agent.png',bins=35))
    ref=load_reference().get(reference_region,{})
    if ref:
        sim=(df.activity.value_counts(normalize=True)*100).reindex(ACTIVITY_ORDER).fillna(0)
        real=pd.Series(ref['destination_share_pct']).reindex(ACTIVITY_ORDER)
        comp=pd.DataFrame({'Simulation check-ins':sim,'NHTS trip destinations':real})
        fig,ax=plt.subplots(figsize=(10,5)); comp.plot(kind='bar',ax=ax);
        #  ax.set_title('Check-in activity mix vs NHTS destination mix'); 
        ax.set_ylabel('Percent'); ax.tick_params(axis='x',rotation=25); ax.grid(axis='y',alpha=.25)
        figs.append(savefig(fig,out,'09_activity_share_vs_nhts.png'))
    top_share=df.VenueId.value_counts(normalize=True).head(10).sum()*100
    insights=[
        f"Agents average {len(df)/(max(df.UserId.nunique(),1)*max(df.date.nunique(),1)):.2f} check-ins per agent-day.",
        f"The ten busiest venues receive {top_share:.1f}% of all check-ins, indicating the degree of place concentration.",
        "Activity-transition flows are the closest check-in analogue to survey origin-destination purpose flows.",
        "Check-ins and NHTS trips are not identical: check-ins record arrival at modeled venues, while NHTS includes all reported trips and more activity types.",
    ]
    write_dataset_summary(out,path.name,figs,insights,{**meta,"rows":len(df)})


def analyze_social_network(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=read_tsv_with_trailing_delimiter(path,skip_blank_lines=True)
    mask,meta=infer_time_window(df['time'],warmup_days); df=df[mask].copy(); df['time']=pd.to_datetime(df['time'],errors='coerce'); df['date']=df['time'].dt.date.astype(str)
    figs=[]
    e=df.assign(a=np.minimum(numeric(df['from']),numeric(df['to'])),b=np.maximum(numeric(df['from']),numeric(df['to']))).dropna(subset=['a','b']).sort_values('time')
    e['edge']=e.a.astype(int).astype(str)+'-'+e.b.astype(int).astype(str)
    snapshots=e.drop_duplicates(['date','edge'])
    population=int(max(e[['a','b']].max())+1) if not e.empty else 0
    daily=snapshots.groupby('date').size()
    figs.append(line_plot(daily,'Unique social ties in each daily snapshot','Undirected ties',out,'01_daily_links.png','Date'))
    daily_degree=2*daily/max(population,1)
    figs.append(line_plot(daily_degree,'Mean network degree by daily snapshot','Mean degree',out,'02_daily_mean_degree.png','Date'))
    final_date=snapshots['date'].max(); final=snapshots[snapshots.date.eq(final_date)]
    endpoints=pd.concat([final.a.astype(int),final.b.astype(int)],ignore_index=True)
    degree=endpoints.value_counts().reindex(range(population),fill_value=0)
    figs.append(histogram(degree,'Final-snapshot degree distribution','Undirected degree',out,'03_degree_distribution.png',bins=35))
    figs.append(bar_plot(degree,"Highest-degree agents in final snapshot","Degree",out,"04_top_agents_by_degree.png",horizontal=True,top=20))
    first=e.drop_duplicates('edge').groupby('date').size().cumsum()
    figs.append(line_plot(first,'Cumulative ties ever observed','Unique ties',out,'05_cumulative_unique_ties.png','Date'))
    mean_deg=2*len(final)/max(population,1)
    insights=[f"The final daily snapshot contains {len(final):,} undirected ties across a {population:,}-agent population, for mean degree {mean_deg:.3f}.",f"Daily mean degree ranges from {daily_degree.min():.3f} to {daily_degree.max():.3f}, indicating strong day-to-day network turnover rather than monotonic growth.","The cumulative-ever-observed curve measures turnover and exposure opportunity; it should not be interpreted as the active graph size."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,"rows":len(df)})


def analyze_financial_journal(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=read_headerless(path,FINANCIAL_COLUMNS,low_memory=False)
    mask,meta=infer_time_window(df.simulationTime,warmup_days); df=df[mask].copy(); df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df['date']=df.time.dt.date.astype(str); df['amount']=numeric(df.amount)
    # Step 0 records initialize balances and recurring obligations. Exclude
    # the complete initialization snapshot from transaction-flow summaries.
    flow=df[numeric(df.step)>0].copy()
    figs=[]
    sums=flow.groupby('transactionType').amount.sum().sort_values()
    figs.append(bar_plot(sums,'Net financial flow by transaction type, excluding initialization','Amount',out,'01_net_flow_by_type.png',horizontal=True))
    counts=flow.transactionType.value_counts(); figs.append(bar_plot(counts,'Transaction count by type, excluding initialization','Transactions',out,'02_transaction_count.png',horizontal=True,percent=True))
    daily=flow.groupby(['date','transactionType']).amount.sum().unstack(fill_value=0)
    fig,ax=plt.subplots(figsize=(11,6)); daily.plot(ax=ax);#  ax.set_title('Daily financial flows'); ax.set_ylabel('Amount'); ax.tick_params(axis='x',rotation=35); ax.grid(alpha=.25)
    figs.append(savefig(fig,out,'03_daily_flows.png'))
    agent=flow.groupby('agentId').amount.sum(); figs.append(histogram(agent,'Net financial change per agent, excluding initialization','Amount',out,'04_agent_net_change.png',bins=45))
    figs.append(histogram(flow.amount.abs().replace(0,np.nan),'Transaction magnitude, excluding initialization','Absolute amount',out,'05_transaction_magnitude.png',bins=50,logx=True))
    per_agent_day=flow.groupby(['date','agentId']).amount.sum().groupby('date').mean()
    figs.append(line_plot(per_agent_day,'Mean net financial flow per agent-day','Amount',out,'06_net_flow_per_agent_day.png','Date'))
    inflow=flow.loc[flow.amount>0,'amount'].sum(); outflow=-flow.loc[flow.amount<0,'amount'].sum()
    initial=df.loc[numeric(df.step)==0,'amount']
    insights=[f"After excluding {len(initial):,} step-0 initialization records, inflow is {inflow:,.0f}, outflow is {outflow:,.0f}, and net flow is {inflow-outflow:,.0f}.",f"The median agent's post-initialization net recorded change is {agent.median():,.1f}.","Rates per agent-day are more comparable across 10-day and yearly runs than raw transaction totals."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,"rows":len(df),"flow_rows":len(flow),"initialization_rows":len(initial)})


def analyze_financial_attributes(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=read_headerless(path,FIN_ATTR_COLUMNS,low_memory=False)
    mask,meta=infer_time_window(df.simulationTime,warmup_days); df=df[mask].copy(); df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df['date']=df.time.dt.date.astype(str)
    for c in ['age','hourlyRate','shelterCost','balance','hasFamily']: df[c]=numeric(df[c])
    figs=[]
    daily=df.groupby('date').balance.mean(); figs.append(line_plot(daily,'Mean agent balance over time','Balance',out,'01_mean_balance.png','Date'))
    figs.append(histogram(df.groupby('agentId').balance.last(),'Final balance distribution','Balance',out,'02_final_balance_distribution.png',bins=45))
    figs.append(bar_plot(df.groupby('educationLevel').hourlyRate.mean().sort_values(),'Mean hourly rate by education','Hourly rate',out,'03_rate_by_education.png',horizontal=True))
    figs.append(scatter(df.hourlyRate,df.balance,'Hourly rate versus balance','Hourly rate','Balance',out,'04_rate_vs_balance.png'))
    figs.append(histogram(df.shelterCost.dropna(),'Shelter cost distribution','Cost',out,'05_shelter_cost.png',bins=35))
    final=df.sort_values('time').groupby('agentId').tail(1)
    emp=final.employed.astype(str).str.lower().eq('yes').mean()*100
    insights=[f"At the final snapshot, {emp:.1f}% of agents are marked employed.",f"Mean balance changed from {daily.iloc[0]:,.1f} to {daily.iloc[-1]:,.1f} across the analyzed snapshots.","Education-rate differences should be checked against initialization rules before interpreting them as emergent inequality."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,"rows":len(df)})


def analyze_intervention(path: Path, out: Path, warmup_days: int = 30, chunksize: int = 250000, **_: object) -> None:
    read_kwargs=dict(header=None,names=INTERVENTION_COLUMNS,low_memory=False,chunksize=chunksize)
    start=end=None
    for ch in pd.read_csv(path,usecols=['simulationTime'],**read_kwargs):
        t=pd.to_datetime(ch.simulationTime,errors='coerce').dropna()
        if t.empty: continue
        start=t.min() if start is None else min(start,t.min()); end=t.max() if end is None else max(end,t.max())
    if start is None or end is None:
        write_dataset_summary(out,path.name,[],['No valid intervention timestamps were found.'],{'rows':0}); return
    span=max((end-start).total_seconds()/86400,0); apply=warmup_days>0 and span>warmup_days+2
    cutoff=start+pd.Timedelta(days=warmup_days) if apply else start
    meta={'start':str(start),'end':str(end),'days':span,'warmup_applied':apply,'analysis_start':str(cutoff),'warmup_days':warmup_days}
    type_counts=Counter(); agent_counts=Counter(); daily_parts=[]; rate_samples=[]; loc_samples=[]; rows=0
    for idx,df in enumerate(pd.read_csv(path,**read_kwargs)):
        df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df=df[df.time.ge(cutoff)].copy()
        if df.empty: continue
        df['date']=df.time.dt.strftime('%Y-%m-%d'); df['rate']=numeric(df.rate); rows+=len(df)
        type_counts.update(df.interventionType.dropna().astype(str).value_counts().to_dict())
        agent_counts.update(numeric(df.agentId).dropna().astype(int).value_counts().to_dict())
        daily_parts.append(df.groupby(['date','interventionType']).size().rename('n').reset_index())
        r=df.rate.dropna()
        if len(r): rate_samples.append(r.sample(n=min(len(r),5000),random_state=200+idx))
        take=min(len(df),5000)
        if take:
            sm=df.sample(n=take,random_state=400+idx); x,y=parse_point_series(sm.location)
            loc_samples.append(pd.DataFrame({'x':x,'y':y,'type':sm.interventionType.astype('string')}))
    figs=[]
    counts=pd.Series(type_counts,dtype=float).sort_values(ascending=False)
    figs.append(bar_plot(counts,'Intervention events by type','Events',out,'01_event_types.png',horizontal=True,percent=True))
    if daily_parts:
        daily=pd.concat(daily_parts,ignore_index=True).groupby(['date','interventionType']).n.sum().unstack(fill_value=0)
        fig,ax=plt.subplots(figsize=(11,6)); daily.plot(ax=ax);#  ax.set_title('Intervention events by day'); ax.set_ylabel('Events'); ax.tick_params(axis='x',rotation=35); ax.grid(alpha=.25)
        figs.append(savefig(fig,out,'02_daily_events.png'))
    agent=pd.Series(agent_counts,dtype=float)
    figs.append(histogram(agent,'Interventions per agent','Events',out,'03_events_per_agent.png',bins=40,logx=True))
    if rate_samples: figs.append(histogram(pd.concat(rate_samples,ignore_index=True),'Rate associated with interventions (sampled)','Rate',out,'04_rate_distribution.png',bins=35))
    if loc_samples:
        loc=pd.concat(loc_samples,ignore_index=True); figs.append(spatial_scatter(loc.x,loc.y,'Spatial distribution of interventions (sampled)',out,'05_intervention_locations.png',loc.type))
    dominant=counts.iloc[0]/max(counts.sum(),1)*100 if len(counts) else 0
    insights=[f"The dominant intervention type represents {dominant:.1f}% of intervention records.","Very frequent repeated job interventions can indicate search churn or a logging event emitted for unsuccessful attempts, so compare unique agents and final jobs as well as raw event counts.","Spatial clustering can identify neighborhoods where housing or employment mechanisms repeatedly trigger."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,'rows':rows,'unique_agents':len(agent_counts),'sampled_locations':sum(len(x) for x in loc_samples)})

def analyze_open_state(path: Path, out: Path, warmup_days: int = 30, chunksize: int = 500000, **_: object) -> None:
    start=end=None
    for ch in pd.read_csv(path,sep='\t',index_col=False,usecols=['simulationTime'],chunksize=chunksize):
        t=pd.to_datetime(ch.simulationTime,errors='coerce').dropna()
        if t.empty: continue
        start=t.min() if start is None else min(start,t.min()); end=t.max() if end is None else max(end,t.max())
    if start is None or end is None:
        write_dataset_summary(out,path.name,[],['No valid venue-state timestamps were found.'],{'rows':0}); return
    span=max((end-start).total_seconds()/86400,0); apply=warmup_days>0 and span>warmup_days+2
    cutoff=start+pd.Timedelta(days=warmup_days) if apply else start
    meta={'start':str(start),'end':str(end),'days':span,'warmup_applied':apply,'analysis_start':str(cutoff),'warmup_days':warmup_days}
    open_parts=[]; id_counts=Counter(); time_points=set(); rows=0
    for df in pd.read_csv(path,sep='\t',index_col=False,usecols=['simulationTime','id'],chunksize=chunksize):
        df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df=df[df.time.ge(cutoff)].dropna(subset=['time','id'])
        if df.empty: continue
        rows+=len(df); time_points.update(df.time.unique().tolist()); id_counts.update(numeric(df.id).dropna().astype(int).value_counts().to_dict())
        open_parts.append(df.groupby('time').size().rename('n'))
    figs=[]
    if open_parts:
        open_count=pd.concat(open_parts).groupby(level=0).sum().sort_index()
        by_hour=open_count.groupby(open_count.index.hour).mean().reindex(range(24))
        figs.append(line_plot(by_hour,'Mean number of open venues by hour','Open venues',out,'01_open_by_hour.png','Hour'))
        daily=open_count.groupby(open_count.index.date).mean(); daily.index=daily.index.astype(str)
        figs.append(line_plot(daily,'Mean open venues by day','Open venues',out,'02_open_by_day.png','Date'))
    availability=pd.Series(id_counts,dtype=float)/max(len(time_points),1)*100
    figs.append(histogram(availability,'Venue availability across logged time points','Time open (%)',out,'03_venue_availability.png',bins=30))
    insights=[f"A typical venue is logged open for {availability.median():.1f}% of observed time points.","The hourly profile is useful for checking whether simulated activity demand is constrained by venue schedules.","For yearly output, day-level availability can expose seasonal closures or drift in the usable-venue pool."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,'rows':rows,'time_points':len(time_points),'venues':len(id_counts)})

def analyze_location_table(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    figs=[]
    x,y=parse_point_series(df.location)
    label=path.stem.replace('Table','')
    figs.append(spatial_scatter(x,y,f'{label} locations',out,'01_spatial_distribution.png'))
    numeric_cols=[c for c in ['rentalCost','foodCost','hourlyCost','monthlyCost','personCapacity','numberOfRooms','attractiveness'] if c in df]
    for i,c in enumerate(numeric_cols[:5],start=2):
        figs.append(histogram(df[c],f'{label}: {c} distribution',c,out,f'{i:02d}_{c}.png',bins=35))
    if 'attractiveness' in df and any(c in df for c in ['rentalCost','foodCost','hourlyCost','monthlyCost']):
        cost=next(c for c in ['rentalCost','foodCost','hourlyCost','monthlyCost'] if c in df)
        figs.append(scatter(df.attractiveness,df[cost],f'{label}: attractiveness versus cost','Attractiveness',cost,out,'07_attractiveness_vs_cost.png'))
    insights=[f"The table contains {len(df):,} {label.lower()} records."]
    if 'personCapacity' in df: insights.append(f"Total listed capacity is {numeric(df.personCapacity).sum():,.0f}, with a median of {numeric(df.personCapacity).median():.0f} per venue.")
    if 'attractiveness' in df: insights.append(f"Median attractiveness is {numeric(df.attractiveness).median():.2f}; spatial clustering of high-attractiveness venues can shape trip concentration.")
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_building(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    cent=np.array([polygon_centroid_approx(v) for v in df.location]); x=pd.Series(cent[:,0]); y=pd.Series(cent[:,1])
    figs=[]
    figs.append(bar_plot(df.buildingType.value_counts(),'Building count by type','Buildings',out,'01_building_types.png',horizontal=True,percent=True,top=20))
    figs.append(spatial_scatter(x,y,'Building centroid distribution',out,'02_building_centroids.png',df.buildingType))
    if 'totalPersonCapacity' in df:
        cap=df.groupby('buildingType').totalPersonCapacity.sum().sort_values(ascending=False).head(15)
        figs.append(bar_plot(cap,'Total person capacity by building type','Capacity',out,'03_capacity_by_type.png',horizontal=True))
        figs.append(histogram(df.totalPersonCapacity,'Building person-capacity distribution','Capacity',out,'04_capacity_distribution.png',bins=40,logx=True))
    figs.append(scatter(df.attractiveness,df.totalPersonCapacity,'Attractiveness versus capacity','Attractiveness','Person capacity',out,'05_attractiveness_vs_capacity.png'))
    insights=[f"There are {len(df):,} buildings across {df.buildingType.nunique()} logged types.","Capacity-weighted building composition is often more informative for exposure and accessibility than raw building counts.","The centroid map can be overlaid conceptually with check-in density to identify underused or overloaded areas."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_job_table(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    df['hourlyRate']=numeric(df.hourlyRate)
    start=pd.to_datetime(df.startTime.astype(str),errors='coerce'); end=pd.to_datetime(df.endTime.astype(str),errors='coerce')
    df['startHour']=start.dt.hour+start.dt.minute/60; df['durationHours']=(end-start).dt.total_seconds()/3600
    df.loc[df.durationHours<0,'durationHours']+=24
    figs=[]
    figs.append(histogram(df.hourlyRate,'Job hourly-rate distribution','Hourly rate',out,'01_hourly_rate.png',bins=45))
    figs.append(bar_plot(df.educationRequirement.value_counts(),'Jobs by education requirement','Jobs',out,'02_education_requirement.png',horizontal=True,percent=True))
    figs.append(histogram(df.startHour,'Job start-time distribution','Hour',out,'03_start_time.png',bins=24))
    figs.append(histogram(df.durationHours,'Scheduled daily work duration','Hours',out,'04_work_duration.png',bins=30))
    figs.append(bar_plot(df.groupby('educationRequirement').hourlyRate.mean().sort_values(),'Mean rate by education requirement','Hourly rate',out,'05_rate_by_education.png',horizontal=True))
    figs.append(bar_plot(df.workplace.value_counts(),'Jobs per workplace','Jobs',out,'06_jobs_per_workplace.png',horizontal=True,top=20))
    insights=[f"The job table contains {len(df):,} positions across {df.workplace.nunique():,} workplaces.",f"Median hourly rate is {df.hourlyRate.median():.2f} and median scheduled duration is {df.durationHours.median():.1f} hours.","Compare jobs per workplace with workplace capacity and agent employment to detect excess job supply or bottlenecks."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_census(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    row=df.iloc[-1]
    figs=[]
    housing=pd.Series({'Occupied':numeric(pd.Series([row.get('occpuiedUnits')])).iloc[0],'Vacant':numeric(pd.Series([row.get('vacantUnits')])).iloc[0]})
    figs.append(bar_plot(housing,'Housing-unit status','Units',out,'01_housing_status.png'))
    metrics=pd.Series({k:pd.to_numeric(row.get(k),errors='coerce') for k in ['population','numOfHouseholds','medianFamilyIncome','averageTravelTime']}).dropna()
    figs.append(bar_plot(metrics,'Census summary metrics','Value',out,'02_census_metrics.png',horizontal=True))
    vacancy=100*housing['Vacant']/max(housing.sum(),1)
    insights=[f"The logged population is {row.get('population')} and the reported housing vacancy rate is {vacancy:.1f}%.","Because this file is a run-level census snapshot, compare it with model initialization targets and external census data rather than with NHTS trip records.","The field named averageTravelTime should be validated for units before direct real-world comparison."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_instance(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t')); row=df.iloc[0]
    numeric_vals=pd.to_numeric(row,errors='coerce').dropna()
    figs=[]
    key=[k for k in ['numOfAgents','oneStepTime','maxSimulationSteps','agentWalkingSpeed','workHoursPerDay','warmupPeriodEndTime'] if k in row.index]
    metrics=pd.Series({k:pd.to_numeric(row[k],errors='coerce') for k in key}).dropna()
    if not metrics.empty: figs.append(bar_plot(metrics,'Key simulation parameters','Value',out,'01_key_parameters.png',horizontal=True))
    top=numeric_vals.sort_values(ascending=False).head(20)
    figs.append(bar_plot(top,'Largest numeric parameter values','Value',out,'02_numeric_parameters.png',horizontal=True))
    write_text(out/'parameters.txt','\n'.join(f'{k}={v}' for k,v in row.items()))
    insights=[f"The run is configured for {row.get('numOfAgents','unknown')} agents and {row.get('maxSimulationSteps','unknown')} maximum steps.",f"The declared warm-up end is {row.get('warmupPeriodEndTime','not provided')}; yearly analyses should normally exclude data before this point.","Keep this parameter snapshot with every figure set so differences between runs are attributable to explicit configuration changes."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_moving_or_jobchange(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=read_tsv_with_trailing_delimiter(path)
    step=numeric(df['step']); cutoff=warmup_days*288 if step.max()>warmup_days*288+576 else 0
    df=df[step>=cutoff].copy(); df['day']=numeric(df.step)/288
    initial=df[numeric(df.step)==0].copy() if cutoff==0 else df.iloc[0:0].copy()
    events=df[numeric(df.step)>max(cutoff,0)].copy() if cutoff==0 else df.copy()
    figs=[]
    daily=events.groupby(np.floor(events.day)).size(); figs.append(line_plot(daily,'Changes by simulation day','Changes',out,'01_daily_events.png','Simulation day'))
    per_agent=events.groupby('agentId').size()
    figs.append(histogram(per_agent,'Changes per affected agent','Changes',out,'02_events_per_agent.png',bins=40,logx=True))
    state_col=[c for c in df.columns if c not in ['step','agentId','day']][0]
    parsed=events[state_col].astype(str).str.strip('[]').str.split(',')
    length=parsed.str.len(); figs.append(histogram(length,'Number of identifiers in logged state','Identifiers',out,'03_state_size.png',bins=20))
    days=max((numeric(df.step).max()-max(cutoff,0))/288,1/288)
    population=max(int(numeric(df.agentId).max()+1),1)
    rate=len(events)/(population*days)*1000
    label='job changes' if 'JobChange' in path.name else 'moves'
    insights=[f"After separating {len(initial):,} step-0 initialization records, the file contains {len(events):,} {label} affecting {events.agentId.nunique():,} agents.",f"The normalized rate is {rate:,.1f} {label} per 1,000 agent-days over the observed period.","For yearly runs, the normalized rate and daily series are more comparable across scenarios than raw totals."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df),"dynamic_events":len(events),"initialization_rows":len(initial),"step_cutoff":cutoff})


def parse_dgs(path: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Parse dynamic DGS add/delete events and reconstruct the final graph."""
    active_nodes:set[str]=set(); active_edges:dict[str,tuple[str,str]]={}
    edge_event_counts: Counter[tuple[float,str]] = Counter(); timeline=[]; current_step=0.0; have_step=False

    def snapshot() -> None:
        timeline.append((current_step,len(active_nodes),len(active_edges)))

    with path.open(encoding='utf-8',errors='replace') as f:
        for raw in f:
            line=raw.strip()
            if not line: continue
            try: parts=shlex.split(line)
            except ValueError: parts=line.split()
            if not parts: continue
            op=parts[0]
            if op=='st':
                if have_step: snapshot()
                try: current_step=float(parts[1])
                except (IndexError,ValueError): pass
                have_step=True
            elif op=='an' and len(parts)>=2:
                active_nodes.add(parts[1])
            elif op=='dn' and len(parts)>=2:
                node=parts[1]; active_nodes.discard(node)
            elif op=='ae' and len(parts)>=4:
                edge_id=parts[1]; src=parts[2]; tgt=parts[-1]
                active_edges[edge_id]=(src,tgt)
                edge_event_counts[(current_step,'add')] += 1
            elif op=='de' and len(parts)>=2:
                edge_id=parts[1]; src,tgt=active_edges.pop(edge_id,('',''))
                edge_event_counts[(current_step,'delete')] += 1
    if have_step: snapshot()
    nodes=pd.DataFrame({'node':sorted(active_nodes)})
    final_edges=pd.DataFrame(
        [(eid,src,tgt) for eid,(src,tgt) in active_edges.items() if src in active_nodes and tgt in active_nodes],
        columns=['edge','source','target']
    )
    events=pd.DataFrame([(step,action,n) for (step,action),n in edge_event_counts.items()],columns=['step','action','n'])
    timeline_df=pd.DataFrame(timeline,columns=['step','active_nodes','active_edges']).drop_duplicates('step',keep='last')
    return nodes,final_edges,events,timeline_df


def analyze_dgs(path: Path, out: Path, **_: object) -> None:
    nodes,edges,events,timeline=parse_dgs(path); figs=[]
    if not edges.empty:
        pairs=pd.DataFrame({
            'a':np.minimum(edges.source.astype(int),edges.target.astype(int)),
            'b':np.maximum(edges.source.astype(int),edges.target.astype(int)),
        }).drop_duplicates()
        endpoints=pd.concat([pairs.a,pairs.b],ignore_index=True)
    else:
        pairs=pd.DataFrame(columns=['a','b']); endpoints=pd.Series(dtype=int)
    degree=endpoints.value_counts().reindex([int(x) for x in nodes.node],fill_value=0) if not nodes.empty else endpoints.value_counts()
    figs.append(histogram(degree,'Graph degree distribution','Degree',out,'01_degree_distribution.png',bins=50,logx=True))
    figs.append(bar_plot(degree,'Highest-degree nodes','Degree',out,'02_top_nodes.png',horizontal=True,top=20))
    if not timeline.empty:
        figs.append(line_plot(timeline.set_index('step').active_edges,'Active edges over simulation time','Active edges',out,'03_active_edges_by_step.png','Step'))
        figs.append(line_plot(timeline.set_index('step').active_nodes,'Active nodes over simulation time','Active nodes',out,'04_active_nodes_by_step.png','Step'))
    if not events.empty:
        event_counts=events.pivot_table(index='step',columns='action',values='n',aggfunc='sum',fill_value=0)
        fig,ax=plt.subplots(figsize=(11,6)); event_counts.plot(ax=ax);#  ax.set_title('Graph edge events by step'); ax.set_ylabel('Events'); ax.set_xlabel('Step'); ax.grid(alpha=.25)
        figs.append(savefig(fig,out,'05_edge_events_by_step.png'))
    unique=len(pairs)
    mean=2*unique/max(len(nodes),1)
    adds=int(events.loc[events.action.eq('add'),'n'].sum()) if not events.empty else 0
    deletes=int(events.loc[events.action.eq('delete'),'n'].sum()) if not events.empty else 0
    insights=[f"The final reconstructed graph contains {len(nodes):,} active nodes, {len(edges):,} directed edges, and {unique:,} undirected pairs; mean undirected degree is {mean:.3f}.",f"The log records {adds:,} edge additions and {deletes:,} deletions, so raw DGS event counts should not be interpreted as final graph size.","Compare FriendFamilyGraph and WorkGraph degree distributions to see whether workplace structure overwhelms voluntary social structure."]
    write_dataset_summary(out,path.name,figs,insights,{"final_nodes":len(nodes),"final_edges":len(edges),"edge_additions":adds,"edge_deletions":deletes})


def analyze_trajectory(path: Path, out: Path, **_: object) -> None:
    df=read_headerless(path,TRAJECTORY_COLUMNS,sep='\t',low_memory=False)
    df['pathLength']=df.pathNodes.astype(str).str.strip('{}').str.split(',').str.len()
    df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df['hour']=df.time.dt.hour
    figs=[]
    figs.append(histogram(df.pathLength,'Path length in network nodes','Nodes',out,'01_path_length.png',bins=25))
    figs.append(bar_plot(df.hour.value_counts().sort_index(),'Trajectory requests by hour','Requests',out,'02_requests_by_hour.png'))
    figs.append(scatter(df.hour,df.pathLength,'Path length by departure hour','Hour','Network nodes',out,'03_path_length_by_hour.png'))
    insights=[f"Only {len(df)} trajectory records are present, so conclusions are diagnostic rather than population-level.",f"Median logged path length is {df.pathLength.median():.0f} network nodes.","Join network-node coordinates or link lengths when available to convert path-node count into distance for stronger NHTS comparison."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_visitor(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=read_headerless(path,VISITOR_COLUMNS,sep='\t',low_memory=False)
    mask,meta=infer_time_window(df.simulationTime,warmup_days); df=df[mask].copy(); df['time']=pd.to_datetime(df.simulationTime,errors='coerce'); df['date']=df.time.dt.date.astype(str)
    figs=[]
    figs.append(histogram(df.visitorAgeMean,'Mean visitor age by venue-day','Age',out,'01_mean_visitor_age.png',bins=35))
    figs.append(histogram(df.visitorAgeMax,'Maximum visitor age by venue-day','Age',out,'02_max_visitor_age.png',bins=35))
    daily=df.groupby('date').visitorAgeMean.mean(); figs.append(line_plot(daily,'Mean venue visitor age by day','Age',out,'03_daily_visitor_age.png','Date'))
    interests=df.interestSet.astype(str).str.strip('{}').str.get_dummies(',').sum().sort_values(ascending=False)
    figs.append(bar_plot(interests,'Interests represented in venue profiles','Venue-day profiles',out,'04_interest_presence.png'))
    insights=[f"The median venue-day mean visitor age is {numeric(df.visitorAgeMean).median():.1f}.","Interest-set diversity can be compared with venue attractiveness and check-in concentration to see whether venues mix or segregate agent types.","The file name appears to contain a typo ('Vistor'); scripts preserve the supplied name for compatibility."]
    write_dataset_summary(out,path.name,figs,insights,{**meta,"rows":len(df)})


def analyze_log(path: Path, out: Path, **_: object) -> None:
    levels=Counter(); components=Counter(); messages=[]
    with path.open(encoding='utf-8',errors='replace') as f:
        for line in f:
            m=re.match(r'\[([^\]]+)\]\s+([^\s]+)',line)
            if m: levels[m.group(1)]+=1; components[m.group(2)]+=1
            messages.append(line.strip())
    figs=[]
    error_lines=[x for x in messages if re.search(r'error|exception|warn',x,re.I)]
    write_text(out/'warnings_and_errors.txt','\n'.join(error_lines) if error_lines else 'No warning/error-like lines found.')
    insights=[f"The run log contains {len(messages):,} lines and {len(error_lines):,} warning/error-like lines.","Initialization counts in the log should agree with the static environment tables; disagreements can reveal partial output or failed initialization.","Review warnings_and_errors.txt before trusting behavioral calibration results."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(messages)})


def analyze_qoi(path: Path, out: Path, warmup_days: int = 30, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    df['Timestep']=numeric(df.Timestep); df['Value']=numeric(df.Value); maxstep=df.Timestep.max(); cutoff=warmup_days*288 if maxstep>warmup_days*288+576 else 0; df=df[df.Timestep>=cutoff].copy(); df['day']=df.Timestep/288
    figs=[]
    for var,g in df.groupby('VariableName'):
        s=g.set_index('day').Value.sort_index(); safe=re.sub(r'[^A-Za-z0-9]+','_',str(var)).strip('_')[:40]
        figs.append(line_plot(s,f'{var} over simulation time','Value',out,f'{len(figs)+1:02d}_{safe}.png','Simulation day'))
    changes={v:(g.sort_values('day').Value.iloc[-1]-g.sort_values('day').Value.iloc[0]) for v,g in df.groupby('VariableName') if len(g)}
    insights=[f"{v} changes by {delta:+.3g} over the analyzed QOI snapshots." for v,delta in changes.items()]
    insights.append("QOI values are already compact run-level indicators; use them to validate trends seen in the detailed journals.")
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df),"step_cutoff":cutoff})


def analyze_relationship(path: Path, out: Path, **_: object) -> None:
    df=clean_columns(pd.read_csv(path,sep='\t'))
    figs=[]
    if 'RelationshipType' in df: figs.append(bar_plot(df.RelationshipType.value_counts(),'Relationship records by type','Records',out,'01_relationship_types.png'))
    insights=[f"Only {len(df)} relationship record is present in this sample.","Use the DGS graph files and SocialNetwork.tsv for actual network structure; this table appears to be a sparse run-level relationship/QOI output."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df)})


def analyze_generic_table(path: Path, out: Path, **_: object) -> None:
    sep='\t' if path.suffix.lower() in {'.tsv','.txt'} else ','
    df=clean_columns(pd.read_csv(path,sep=sep,low_memory=False))
    figs=[]
    num=df.apply(pd.to_numeric,errors='coerce')
    valid=[c for c in num if num[c].notna().mean()>.8]
    for c in valid[:4]: figs.append(histogram(num[c],f'{path.stem}: {c}',c,out,f'{len(figs)+1:02d}_{c}.png',bins=35))
    cat=[c for c in df if c not in valid and df[c].nunique(dropna=True)<=30]
    for c in cat[:3]: figs.append(bar_plot(df[c].value_counts(),f'{path.stem}: {c}', 'Records',out,f'{len(figs)+1:02d}_{c}.png',horizontal=True,top=20))
    insights=[f"The file contains {len(df):,} rows and {len(df.columns)} columns.","This generic profile emphasizes distributions and category composition; use it as a data-quality check before more specialized modeling."]
    write_dataset_summary(out,path.name,figs,insights,{"rows":len(df),"columns":list(df.columns)})


ANALYZERS = {
    'AgentCharacteristicsTable.tsv': analyze_agent_characteristics,
    'AgentStateTable.tsv': analyze_agent_state,
    'TravelJournal.csv': analyze_travel_journal,
    'Checkin.tsv': analyze_checkin,
    'SocialNetwork.tsv': analyze_social_network,
    'FinancialJournal.csv': analyze_financial_journal,
    'FinancialAttributesJournal.csv': analyze_financial_attributes,
    'InterventionJournal.csv': analyze_intervention,
    'OpenPubState.tsv': analyze_open_state,
    'OpenRestaurantState.tsv': analyze_open_state,
    'BuildingTable.tsv': analyze_building,
    'JobTable.tsv': analyze_job_table,
    'CensusTable.tsv': analyze_census,
    'InstanceDataTable.tsv': analyze_instance,
    'MovingJournal.tsv': analyze_moving_or_jobchange,
    'JobChangeJournal.tsv': analyze_moving_or_jobchange,
    'FriendFamilyGraph.dgs': analyze_dgs,
    'WorkGraph.dgs': analyze_dgs,
    'Trajectory.tsv': analyze_trajectory,
    'VistorProfile.tsv': analyze_visitor,
    'pattenrs_of_life.log': analyze_log,
    'RelationshipTable.tsv': analyze_relationship,
    'ApartmentTable.tsv': analyze_location_table,
    'WorkplaceTable.tsv': analyze_location_table,
    'RestaurantTable.tsv': analyze_location_table,
    'PubTable.tsv': analyze_location_table,
    'ClassroomTable.tsv': analyze_location_table,
}


def run_dataset(input_path: Path, out: Path, warmup_days: int = 30, chunksize: int = 500000, data_root: Path | None = None, reference_region: str = 'georgia') -> None:
    ensure_dir(out)
    analyzer = analyze_qoi if input_path.name.startswith('QOI') else ANALYZERS.get(input_path.name, analyze_generic_table)
    analyzer(input_path, out, warmup_days=warmup_days, chunksize=chunksize, data_root=data_root, reference_region=reference_region)


def cli_for(relative_path: str) -> None:
    ap=argparse.ArgumentParser(description=f'Visualize {relative_path} from a Patterns of Life simulation run.')
    ap.add_argument('input',type=Path,nargs='?',help='Path to the dataset file. If omitted, --data-root is used.')
    ap.add_argument('--data-root',type=Path,default=None,help='Simulation root containing logs/ and qois/.')
    ap.add_argument('--out',type=Path,default=None,help='Output directory. Default: figs/<dataset stem>.')
    ap.add_argument('--warmup-days',type=int,default=30,help='Discard this many initial days only when the run is long enough. Default 30.')
    ap.add_argument('--chunksize',type=int,default=500000)
    ap.add_argument('--reference-region',choices=['georgia','national'],default='georgia')
    args=ap.parse_args()
    if args.input is None:
        if args.data_root is None: ap.error('Provide input or --data-root.')
        input_path=resolve_input(args.data_root,relative_path)
    else: input_path=args.input
    out=args.out or Path('figs')/input_path.stem
    run_dataset(input_path,out,args.warmup_days,args.chunksize,args.data_root,args.reference_region)

