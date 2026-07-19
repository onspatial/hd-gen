#!/usr/bin/env python3
"""Build source-destination products from a Patterns of Life TravelJournal file."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
import zipfile

import pandas as pd

from flow_chord_common import (
    COMPARABLE_COLORS,
    COMPARABLE_ORDER,
    DETAILED_COLORS,
    DETAILED_ORDER,
    ensure_dir,
    matrix_insights,
    plot_directed_chord,
    plot_entry_exit_balance,
    plot_row_percent_heatmap,
    plot_top_flows,
    write_matrix_products,
    write_summary,
)
from simviz_common import PLACE_MAP, TRAVEL_COLUMNS


@contextmanager
def open_travel_journal(path: Path):
    if path.is_dir():
        candidates = [p for p in path.rglob("*") if p.is_file() and p.name.lower() == "traveljournal.csv"]
        if not candidates:
            raise FileNotFoundError(f"Could not find TravelJournal.csv under {path}")
        with candidates[0].open("rb") as stream:
            yield stream
        return
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if Path(name).name.lower() == "traveljournal.csv"]
            if not members:
                raise FileNotFoundError(f"Could not find TravelJournal.csv in {path}")
            with archive.open(members[0]) as stream:
                yield stream
        return
    with path.open("rb") as stream:
        yield stream


def iter_chunks(path: Path, usecols: list[str], chunksize: int):
    with open_travel_journal(path) as stream:
        yield from pd.read_csv(
            stream,
            header=None,
            names=TRAVEL_COLUMNS,
            usecols=usecols,
            chunksize=chunksize,
            low_memory=False,
        )


def activity(series: pd.Series) -> pd.Series:
    return series.astype("string").map(PLACE_MAP).fillna("Other")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("simulation", type=Path, help="TravelJournal.csv, simulation.zip, or simulation directory")
    parser.add_argument("--out", type=Path, default=Path("figs/source_destination/simulation"))
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--chunksize", type=int, default=250_000)
    args = parser.parse_args()
    out = ensure_dir(args.out)

    start = None
    end = None
    for chunk in iter_chunks(args.simulation, ["travelStartTime"], args.chunksize):
        times = pd.to_datetime(chunk["travelStartTime"], errors="coerce").dropna()
        if times.empty:
            continue
        chunk_start, chunk_end = times.min(), times.max()
        start = chunk_start if start is None else min(start, chunk_start)
        end = chunk_end if end is None else max(end, chunk_end)
    if start is None or end is None:
        raise ValueError("No valid travelStartTime values were found in the simulation input")

    span_days = max((end - start).total_seconds() / 86400.0, 0.0)
    warmup_applied = args.warmup_days > 0 and span_days > args.warmup_days + 2
    cutoff = start + pd.Timedelta(days=args.warmup_days) if warmup_applied else start

    detailed = pd.DataFrame(0.0, index=DETAILED_ORDER, columns=DETAILED_ORDER)
    rows_read = 0
    rows_selected = 0
    agents: set[int] = set()
    dates: set[str] = set()

    columns = ["agentId", "travelStartTime", "travelStartPlaceType", "travelEndPlaceType"]
    for chunk in iter_chunks(args.simulation, columns, args.chunksize):
        rows_read += len(chunk)
        time = pd.to_datetime(chunk["travelStartTime"], errors="coerce")
        chunk = chunk.loc[time.ge(cutoff)].copy()
        if chunk.empty:
            continue
        time = time.loc[chunk.index]
        rows_selected += len(chunk)
        origin = activity(chunk["travelStartPlaceType"])
        destination = activity(chunk["travelEndPlaceType"])
        grouped = pd.crosstab(origin, destination)
        detailed = detailed.add(grouped.reindex(index=DETAILED_ORDER, columns=DETAILED_ORDER, fill_value=0), fill_value=0)
        agent = pd.to_numeric(chunk["agentId"], errors="coerce").dropna()
        agents.update(agent.astype(int).unique().tolist())
        dates.update(time.dt.strftime("%Y-%m-%d").dropna().unique().tolist())

    detailed = detailed.astype(float)
    comparable = detailed.reindex(index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER, fill_value=0)
    if comparable.to_numpy(dtype=float).sum() <= 0:
        raise ValueError("No comparable simulation flows were found after warm-up filtering")

    write_matrix_products(detailed, out, "simulation_detailed_flow")
    write_matrix_products(comparable, out, "simulation_comparable_flow")

    plot_directed_chord(
        detailed,
        out / "01_simulation_detailed_chord.png",
        "Simulation detailed activity flows",
        DETAILED_COLORS,
        fixed_sectors=True,
        min_flow_share_pct=0.25,
        center_unit="trips",
    )
    plot_directed_chord(
        comparable,
        out / "02_simulation_comparable_chord.png",
        "Simulation comparable activity flows",
        COMPARABLE_COLORS,
        fixed_sectors=True,
        min_flow_share_pct=0.10,
        center_unit="trips",
    )
    plot_row_percent_heatmap(
        comparable,
        out / "03_simulation_source_conditional.png",
        "Simulation destination mix within each source",
    )
    plot_top_flows(
        comparable,
        out / "04_simulation_top_comparable_flows.png",
        "Largest simulation comparable flows",
        top_n=16,
    )
    plot_entry_exit_balance(
        comparable,
        out / "05_simulation_entry_exit_balance.png",
        "Simulation source and destination balance",
    )

    denominator = len(agents) * len(dates)
    insights = matrix_insights(comparable, "Simulation comparable flows", float(denominator) if denominator else None)
    insights.append(f"Warm-up exclusion was {'applied' if warmup_applied else 'not applied'}; analysis starts at {cutoff}.")
    write_summary(out / "simulation_source_destination_summary.json", {
        "input": str(args.simulation),
        "rows_read": rows_read,
        "rows_selected": rows_selected,
        "start": str(start),
        "end": str(end),
        "analysis_start": str(cutoff),
        "warmup_days": args.warmup_days,
        "warmup_applied": warmup_applied,
        "unique_agents": len(agents),
        "unique_dates": len(dates),
        "comparable_categories": COMPARABLE_ORDER,
    }, insights)
    print(f"Wrote simulation source-destination products to {out}")


if __name__ == "__main__":
    main()
