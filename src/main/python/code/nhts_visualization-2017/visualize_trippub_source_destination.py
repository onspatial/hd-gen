#!/usr/bin/env python3
"""Build weighted source-destination products from the 2017 NHTS TRIPPUB file."""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from flow_chord_common import (
    COMPARABLE_COLORS,
    COMPARABLE_ORDER,
    DETAILED_COLORS,
    DETAILED_ORDER,
    NHTS_2017_DETAILED_ACTIVITY_MAP,
    ensure_dir,
    matrix_insights,
    plot_directed_chord,
    plot_entry_exit_balance,
    plot_row_percent_heatmap,
    plot_top_flows,
    write_matrix_products,
    write_summary,
)


def iter_trippub(path: Path, chunksize: int):
    usecols = ["WHYFROM", "WHYTO", "WTTRDFIN", "HHSTFIPS"]
    if path.is_dir():
        candidates = [p for p in path.rglob("*.csv") if p.name.lower() == "trippub.csv"]
        if not candidates:
            raise FileNotFoundError(f"Could not find trippub.csv under {path}")
        yield from pd.read_csv(candidates[0], usecols=usecols, chunksize=chunksize, low_memory=False)
        return
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if Path(name).name.lower() == "trippub.csv"]
            if not members:
                raise FileNotFoundError(f"Could not find trippub.csv in {path}")
            with archive.open(members[0]) as stream:
                yield from pd.read_csv(stream, usecols=usecols, chunksize=chunksize, low_memory=False)
        return
    yield from pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trippub", type=Path, help="2017 trippub.csv, csv.zip, or a directory containing trippub.csv")
    parser.add_argument("--out", type=Path, default=Path("figs/source_destination/nhts_2017"))
    parser.add_argument("--state-fips", type=int, default=13, help="Household-state FIPS code; default 13 is Georgia")
    parser.add_argument("--national", action="store_true", help="Use the national sample instead of filtering by state")
    parser.add_argument("--chunksize", type=int, default=150_000)
    args = parser.parse_args()
    out = ensure_dir(args.out)

    detailed = pd.DataFrame(0.0, index=DETAILED_ORDER, columns=DETAILED_ORDER)
    rows_read = 0
    rows_selected = 0
    selected_weight = 0.0

    for chunk in iter_trippub(args.trippub, args.chunksize):
        rows_read += len(chunk)
        if not args.national:
            state = pd.to_numeric(chunk["HHSTFIPS"], errors="coerce")
            chunk = chunk.loc[state.eq(args.state_fips)].copy()
        if chunk.empty:
            continue
        rows_selected += len(chunk)
        weight = pd.to_numeric(chunk["WTTRDFIN"], errors="coerce").where(lambda value: value > 0)
        origin = pd.to_numeric(chunk["WHYFROM"], errors="coerce").map(NHTS_2017_DETAILED_ACTIVITY_MAP)
        destination = pd.to_numeric(chunk["WHYTO"], errors="coerce").map(NHTS_2017_DETAILED_ACTIVITY_MAP)
        flow = pd.DataFrame({"origin": origin, "destination": destination, "weight": weight}).dropna()
        if flow.empty:
            continue
        selected_weight += float(flow["weight"].sum())
        grouped = flow.groupby(["origin", "destination"], observed=True)["weight"].sum()
        for (source, target), value in grouped.items():
            if source in detailed.index and target in detailed.columns:
                detailed.loc[source, target] += float(value)

    comparable = detailed.reindex(index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER, fill_value=0)
    if detailed.to_numpy(dtype=float).sum() <= 0:
        scope = "national" if args.national else f"state FIPS {args.state_fips}"
        raise ValueError(f"No positive 2017 NHTS flows were found for {scope}")
    if comparable.to_numpy(dtype=float).sum() <= 0:
        raise ValueError("No flows remained after restricting both trip ends to comparable activity classes")

    write_matrix_products(detailed, out, "trippub_detailed_flow")
    write_matrix_products(comparable, out, "trippub_comparable_flow")

    scope_label = "United States" if args.national else f"state FIPS {args.state_fips}"
    plot_directed_chord(
        detailed,
        out / "01_nhts_2017_detailed_chord.png",
        f"2017 NHTS detailed activity flows, {scope_label}",
        DETAILED_COLORS,
        min_flow_share_pct=0.25,
        center_unit="weighted trips",
    )
    plot_directed_chord(
        comparable,
        out / "02_nhts_2017_comparable_chord.png",
        f"2017 NHTS comparable activity flows, {scope_label}",
        COMPARABLE_COLORS,
        fixed_sectors=False,
        min_flow_share_pct=0.10,
        center_unit="weighted trips",
    )
    plot_row_percent_heatmap(
        comparable,
        out / "03_nhts_2017_source_conditional.png",
        "2017 NHTS destination mix within each source",
    )
    plot_top_flows(
        comparable,
        out / "04_nhts_2017_top_comparable_flows.png",
        "Largest 2017 NHTS comparable flows",
        top_n=16,
    )
    plot_entry_exit_balance(
        comparable,
        out / "05_nhts_2017_entry_exit_balance.png",
        "2017 NHTS source and destination balance",
    )

    comparable_share = comparable.to_numpy(dtype=float).sum() / detailed.to_numpy(dtype=float).sum() * 100
    insights = matrix_insights(comparable, "2017 NHTS comparable weighted flows")
    insights.append(f"Comparable-to-comparable flows retain {comparable_share:.2f}% of weighted flows with recognized 2017 activity codes.")
    insights.append("The comparison subset includes Home, Work, Restaurant, and Recreation at both trip ends; other NHTS activities are retained only in the detailed matrix.")
    write_summary(out / "nhts_2017_source_destination_summary.json", {
        "survey": "2017 NHTS",
        "input": str(args.trippub),
        "scope": scope_label,
        "state_fips": None if args.national else args.state_fips,
        "rows_read": rows_read,
        "rows_selected": rows_selected,
        "recognized_weighted_trips": selected_weight,
        "weight": "WTTRDFIN",
        "origin_field": "WHYFROM",
        "destination_field": "WHYTO",
        "comparable_categories": COMPARABLE_ORDER,
    }, insights)
    print(f"Wrote 2017 NHTS source-destination products to {out}")


if __name__ == "__main__":
    main()
