#!/usr/bin/env python3
"""Create directed source-destination flow visuals from NHTS DAYV2PUB.

Designed for the full 2009 NHTS public-use trip file. The file is read in
chunks and may be supplied either as DAYV2PUB.CSV or as the original Ascii.zip.
By default, Georgia trips are selected to make comparison with an Atlanta-area
simulation meaningful. Use --state-fips 0 for the full United States.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
import zipfile

import numpy as np
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

USECOLS = ["WHYFROM", "WHYTO", "WTTRDFIN", "HHSTFIPS"]


def detailed_activity(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    tens = np.floor(values / 10) * 10
    result = pd.Series(pd.NA, index=series.index, dtype="string")
    result.loc[values.eq(1)] = "Home"
    result.loc[tens.eq(10)] = "Work"
    result.loc[tens.eq(20)] = "School"
    result.loc[tens.eq(30)] = "Medical"
    result.loc[tens.eq(40)] = "Shopping"
    result.loc[tens.eq(50)] = "Recreation"
    result.loc[tens.eq(60)] = "Personal business"
    result.loc[tens.eq(70)] = "Escort"
    result.loc[tens.eq(80)] = "Restaurant"
    result.loc[values.eq(97)] = "Other"
    return result


def comparable_activity(detailed: pd.Series) -> pd.Series:
    collapsed = detailed.copy()
    collapsed = collapsed.replace({
        "Medical": "Other",
        "Shopping": "Other",
        "Personal business": "Other",
        "Escort": "Other",
    })
    return collapsed


def find_member(archive: zipfile.ZipFile, requested: str | None) -> str:
    if requested:
        if requested not in archive.namelist():
            raise FileNotFoundError(f"Archive member not found: {requested}")
        return requested
    matches = [name for name in archive.namelist() if name.upper().endswith("DAYV2PUB.CSV")]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one DAYV2PUB.CSV in archive, found {matches}")
    return matches[0]


def iter_chunks(path: Path, member: str | None, chunksize: int):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            selected = find_member(archive, member)
            with archive.open(selected) as handle:
                yield from pd.read_csv(handle, usecols=USECOLS, chunksize=chunksize, low_memory=False)
    else:
        yield from pd.read_csv(path, usecols=USECOLS, chunksize=chunksize, low_memory=False)


def add_weighted_flows(matrix: pd.DataFrame, source: pd.Series, destination: pd.Series, weight: pd.Series) -> float:
    frame = pd.DataFrame({"source": source, "destination": destination, "weight": weight}).dropna()
    frame = frame[frame["weight"].gt(0)]
    grouped = frame.groupby(["source", "destination"], observed=True)["weight"].sum()
    for (src, dst), value in grouped.items():
        if src in matrix.index and dst in matrix.columns:
            matrix.loc[src, dst] += float(value)
    return float(frame["weight"].sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="DAYV2PUB.CSV or Ascii.zip")
    parser.add_argument("--member", help="ZIP member path; usually auto-detected")
    parser.add_argument("--out", type=Path, default=Path("figs/dayv2pub_source_destination"))
    parser.add_argument("--state-fips", type=int, default=13,
                        help="Household state FIPS; default 13 (Georgia), 0 means all states")
    parser.add_argument("--chunksize", type=int, default=150_000)
    parser.add_argument("--min-flow-share", type=float, default=0.08,
                        help="Omit ribbons smaller than this percent of total flow")
    args = parser.parse_args()

    out = ensure_dir(args.out)
    detailed = pd.DataFrame(0.0, index=DETAILED_ORDER, columns=DETAILED_ORDER)
    comparable = pd.DataFrame(0.0, index=COMPARABLE_ORDER, columns=COMPARABLE_ORDER)
    raw_rows = selected_rows = valid_rows = 0

    for chunk in iter_chunks(args.input, args.member, args.chunksize):
        raw_rows += len(chunk)
        if args.state_fips:
            state = pd.to_numeric(chunk["HHSTFIPS"], errors="coerce")
            chunk = chunk[state.eq(args.state_fips)]
        selected_rows += len(chunk)
        if chunk.empty:
            continue

        weight = pd.to_numeric(chunk["WTTRDFIN"], errors="coerce")
        src_detailed = detailed_activity(chunk["WHYFROM"])
        dst_detailed = detailed_activity(chunk["WHYTO"])
        valid_rows += int(pd.DataFrame({"s": src_detailed, "d": dst_detailed, "w": weight}).dropna().query("w > 0").shape[0])
        add_weighted_flows(detailed, src_detailed, dst_detailed, weight)
        add_weighted_flows(
            comparable,
            comparable_activity(src_detailed),
            comparable_activity(dst_detailed),
            weight,
        )

    if comparable.to_numpy().sum() <= 0:
        raise RuntimeError("No valid weighted trips remained after filtering")

    region = "United States" if args.state_fips == 0 else f"state FIPS {args.state_fips}"
    if args.state_fips == 13:
        region = "Georgia"

    plot_directed_chord(
        detailed,
        out / "01_dayv2pub_detailed_source_destination_chord.png",
        f"NHTS DAYV2PUB source → destination flows, {region}",
        DETAILED_COLORS,
        fixed_sectors=False,
        min_flow_share_pct=args.min_flow_share,
        subtitle="Survey-weighted trips; detailed NHTS activity categories",
        center_unit="weighted trips",
    )
    plot_directed_chord(
        comparable,
        out / "02_dayv2pub_comparable_source_destination_chord.png",
        f"NHTS source → destination flows, {region}",
        COMPARABLE_COLORS,
        fixed_sectors=True,
        min_flow_share_pct=args.min_flow_share,
        subtitle="Fixed sectors and six shared categories for simulation comparison",
        center_unit="weighted trips",
    )
    plot_row_percent_heatmap(
        comparable,
        out / "03_dayv2pub_source_conditional_heatmap.png",
        f"NHTS destination conditional on source, {region}",
    )
    plot_top_flows(
        comparable,
        out / "04_dayv2pub_top_flows.png",
        f"Largest NHTS activity flows, {region}",
        top_n=18,
    )
    plot_entry_exit_balance(
        comparable,
        out / "05_dayv2pub_entry_exit_balance.png",
        f"NHTS destination versus source balance, {region}",
    )

    write_matrix_products(detailed, out, "dayv2pub_detailed_flow")
    write_matrix_products(comparable, out, "dayv2pub_comparable_flow")
    insights = matrix_insights(comparable, f"NHTS DAYV2PUB ({region})")
    insights.extend([
        "NHTS flows use WTTRDFIN survey weights.",
        "For direct comparison, Medical, Shopping, Personal business, and Escort are combined into Other.",
        "The fixed-sector chord uses identical category positions and colors as the simulation chord; ribbon width, not sector size, carries the flow magnitude.",
    ])
    write_summary(
        out / "dayv2pub_flow_summary.json",
        {
            "input": str(args.input),
            "region": region,
            "state_fips": args.state_fips,
            "raw_rows": raw_rows,
            "selected_rows": selected_rows,
            "valid_rows": valid_rows,
            "weighted_trip_total": float(comparable.to_numpy().sum()),
            "minimum_ribbon_share_pct": args.min_flow_share,
        },
        insights,
    )
    (out / "INSIGHTS.txt").write_text("\n".join(f"- {line}" for line in insights) + "\n", encoding="utf-8")
    print(f"Wrote DAYV2PUB flow products to {out}")


if __name__ == "__main__":
    main()
