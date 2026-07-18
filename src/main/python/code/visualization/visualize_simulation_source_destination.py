#!/usr/bin/env python3
"""Create directed source-destination flow visuals from simulation TravelJournal.

The journal may be supplied directly or inside simulation.zip. Processing is
chunked and suitable for a year-long run. A 30-day warm-up is removed only when
the available run is long enough, so the provided 10-day sample is retained.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

import pandas as pd

from flow_chord_common import (
    COMPARABLE_COLORS,
    COMPARABLE_ORDER,
    ensure_dir,
    matrix_insights,
    plot_directed_chord,
    plot_entry_exit_balance,
    plot_row_percent_heatmap,
    plot_top_flows,
    write_matrix_products,
    write_summary,
)

TRAVEL_COLUMNS = [
    "step", "agentId", "travelStartTime", "travelStartPlaceType", "travelStartLocationId",
    "travelEndTime", "travelEndLocationId", "travelEndPlaceType",
    "intendedTravelEndLocationId", "intendedTravelEndPlaceType", "purpose",
    "checkInTime", "checkOutTime", "maxPeople", "minPeople",
    "moneyBalanceBefore", "moneyBalanceAfter", "moneyOffset", "eventSummary1", "eventSummary2",
]
USECOLS = ["agentId", "travelStartTime", "travelStartPlaceType", "travelEndPlaceType"]

PLACE_MAP = {
    "AtHome": "Home", "Apartment": "Home", "Home": "Home",
    "AtWork": "Work", "Workplace": "Work", "Work": "Work",
    "AtSchool": "School", "School": "School", "Classroom": "School",
    "AtRestaurant": "Restaurant", "Restaurant": "Restaurant",
    "AtRecreation": "Recreation", "Recreation": "Recreation", "Pub": "Recreation",
}


def activity(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.map(PLACE_MAP).fillna("Other")


def find_member(archive: zipfile.ZipFile, requested: str | None) -> str:
    if requested:
        if requested not in archive.namelist():
            raise FileNotFoundError(f"Archive member not found: {requested}")
        return requested
    matches = [name for name in archive.namelist() if name.endswith("TravelJournal.csv")]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one TravelJournal.csv in archive, found {matches}")
    return matches[0]


def iter_chunks(path: Path, member: str | None, chunksize: int):
    kwargs = dict(header=None, names=TRAVEL_COLUMNS, usecols=USECOLS, chunksize=chunksize, low_memory=False)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            selected = find_member(archive, member)
            with archive.open(selected) as handle:
                yield from pd.read_csv(handle, **kwargs)
    else:
        yield from pd.read_csv(path, **kwargs)


def scan_time_range(path: Path, member: str | None, chunksize: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    first: pd.Timestamp | None = None
    last: pd.Timestamp | None = None
    for chunk in iter_chunks(path, member, chunksize):
        times = pd.to_datetime(chunk["travelStartTime"], errors="coerce").dropna()
        if times.empty:
            continue
        cmin, cmax = times.min(), times.max()
        first = cmin if first is None else min(first, cmin)
        last = cmax if last is None else max(last, cmax)
    if first is None or last is None:
        raise RuntimeError("No valid travelStartTime values were found")
    return first, last


def parse_boundary(value: str | None, end: bool = False) -> pd.Timestamp | None:
    if not value:
        return None
    timestamp = pd.Timestamp(value)
    # Treat a plain date end boundary as inclusive through that date.
    if end and len(value.strip()) <= 10:
        timestamp += pd.Timedelta(days=1)
    return timestamp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="TravelJournal.csv or simulation.zip")
    parser.add_argument("--member", help="ZIP member path; usually auto-detected")
    parser.add_argument("--out", type=Path, default=Path("figs/simulation_source_destination"))
    parser.add_argument("--chunksize", type=int, default=250_000)
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--start-date", help="Optional analysis start timestamp/date")
    parser.add_argument("--end-date", help="Optional inclusive analysis end timestamp/date")
    parser.add_argument("--min-flow-share", type=float, default=0.08,
                        help="Omit ribbons smaller than this percent of total flow")
    args = parser.parse_args()

    out = ensure_dir(args.out)
    first, last = scan_time_range(args.input, args.member, args.chunksize)
    span_days = max((last - first).total_seconds() / 86400.0, 0.0)
    warmup_applied = args.warmup_days > 0 and span_days > args.warmup_days + 2
    analysis_start = first + pd.Timedelta(days=args.warmup_days) if warmup_applied else first
    explicit_start = parse_boundary(args.start_date)
    explicit_end = parse_boundary(args.end_date, end=True)
    if explicit_start is not None:
        analysis_start = max(analysis_start, explicit_start)

    matrix = pd.DataFrame(0, index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER, dtype="int64")
    raw_rows = selected_rows = 0
    agents: set[int] = set()
    agent_days: set[tuple[int, str]] = set()
    dates: set[str] = set()
    observed_start_types: set[str] = set()
    observed_end_types: set[str] = set()

    for chunk in iter_chunks(args.input, args.member, args.chunksize):
        raw_rows += len(chunk)
        time = pd.to_datetime(chunk["travelStartTime"], errors="coerce")
        keep = time.ge(analysis_start)
        if explicit_end is not None:
            keep &= time.lt(explicit_end)
        chunk = chunk[keep].copy()
        time = time[keep]
        if chunk.empty:
            continue
        selected_rows += len(chunk)

        observed_start_types.update(chunk["travelStartPlaceType"].dropna().astype(str).unique())
        observed_end_types.update(chunk["travelEndPlaceType"].dropna().astype(str).unique())
        source = activity(chunk["travelStartPlaceType"])
        destination = activity(chunk["travelEndPlaceType"])
        flow = pd.crosstab(source, destination).reindex(
            index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER, fill_value=0
        )
        matrix = matrix.add(flow, fill_value=0).astype("int64")

        agent = pd.to_numeric(chunk["agentId"], errors="coerce")
        valid_agent = agent.notna()
        agent_int = agent[valid_agent].astype(int)
        date_text = time[valid_agent].dt.strftime("%Y-%m-%d")
        agents.update(agent_int.unique().tolist())
        dates.update(date_text.dropna().unique().tolist())
        agent_days.update(zip(agent_int.tolist(), date_text.tolist()))

    if matrix.to_numpy().sum() <= 0:
        raise RuntimeError("No simulation trips remained after time filtering")

    plot_directed_chord(
        matrix,
        out / "01_simulation_source_destination_chord.png",
        "Simulation source → destination flows",
        COMPARABLE_COLORS,
        fixed_sectors=False,
        min_flow_share_pct=args.min_flow_share,
        subtitle="Observed trip counts after the configured warm-up and date filters",
    )
    plot_directed_chord(
        matrix,
        out / "02_simulation_comparable_fixed_sector_chord.png",
        "Simulation source → destination flows, comparable layout",
        COMPARABLE_COLORS,
        fixed_sectors=True,
        min_flow_share_pct=args.min_flow_share,
        subtitle="Same fixed sectors, category order, and colors as the NHTS comparison chart",
    )
    plot_row_percent_heatmap(
        matrix,
        out / "03_simulation_source_conditional_heatmap.png",
        "Simulation destination conditional on source",
    )
    plot_top_flows(
        matrix,
        out / "04_simulation_top_flows.png",
        "Largest simulation activity flows",
        top_n=18,
    )
    plot_entry_exit_balance(
        matrix,
        out / "05_simulation_entry_exit_balance.png",
        "Simulation destination versus source balance",
    )

    write_matrix_products(matrix, out, "simulation_comparable_flow")
    denominator = float(len(agent_days))
    if denominator > 0:
        (matrix / denominator * 1000).to_csv(out / "simulation_flow_per_1000_agent_days.csv")

    insights = matrix_insights(matrix, "Simulation TravelJournal", rate_denominator=denominator)
    zero_categories = [
        category for category in COMPARABLE_ORDER
        if matrix.loc[category].sum() + matrix[category].sum() == 0
    ]
    if zero_categories:
        insights.append("No observed trip ends for: " + ", ".join(zero_categories) + ".")
    insights.extend([
        "Counts are also exported per 1,000 observed agent-days so a 10-day sample and a full-year run can be compared without annualizing raw totals.",
        "For runs longer than 32 days, the default removes the first 30 days as warm-up; it does not remove warm-up from the 10-day sample.",
        "Large entry/exit marginal imbalances can indicate a truncated observation window or agents whose first/last trip lies outside the analyzed period.",
    ])
    write_summary(
        out / "simulation_flow_summary.json",
        {
            "input": str(args.input),
            "raw_start": str(first),
            "raw_end": str(last),
            "raw_span_days": span_days,
            "analysis_start": str(analysis_start),
            "analysis_end_exclusive": str(explicit_end) if explicit_end is not None else None,
            "warmup_days": args.warmup_days,
            "warmup_applied": warmup_applied,
            "raw_rows": raw_rows,
            "selected_rows": selected_rows,
            "unique_agents": len(agents),
            "unique_dates": len(dates),
            "observed_agent_days": len(agent_days),
            "observed_start_place_types": sorted(observed_start_types),
            "observed_end_place_types": sorted(observed_end_types),
            "minimum_ribbon_share_pct": args.min_flow_share,
        },
        insights,
    )
    (out / "INSIGHTS.txt").write_text("\n".join(f"- {line}" for line in insights) + "\n", encoding="utf-8")
    print(f"Wrote simulation flow products to {out}")


if __name__ == "__main__":
    main()
