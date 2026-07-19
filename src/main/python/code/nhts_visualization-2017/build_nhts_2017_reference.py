#!/usr/bin/env python3
"""Build national and state simulation benchmarks from 2017 NHTS public files."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import json
import zipfile

import numpy as np
import pandas as pd

from flow_chord_common import COMPARABLE_ORDER, NHTS_2017_DETAILED_ACTIVITY_MAP


def iter_public_file(path: Path, filename: str, usecols: list[str], chunksize: int):
    if path.is_dir():
        candidates = [p for p in path.rglob("*.csv") if p.name.lower() == filename.lower()]
        if not candidates:
            raise FileNotFoundError(f"Could not find {filename} under {path}")
        yield from pd.read_csv(candidates[0], usecols=usecols, chunksize=chunksize, low_memory=False)
        return
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if Path(name).name.lower() == filename.lower()]
            if not members:
                raise FileNotFoundError(f"Could not find {filename} in {path}")
            with archive.open(members[0]) as stream:
                yield from pd.read_csv(stream, usecols=usecols, chunksize=chunksize, low_memory=False)
        return
    if path.name.lower() != filename.lower():
        raise ValueError(f"A single CSV input must be {filename}; use csv.zip or a directory for both public files")
    yield from pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False)


def hour_from_hhmm(series: pd.Series) -> pd.Series:
    raw = series.astype("string").str.replace(":", "", regex=False).str.extract(r"(\d{1,4})", expand=False)
    number = pd.to_numeric(raw, errors="coerce")
    hour = np.floor(number / 100)
    minute = number % 100
    return hour.where(hour.between(0, 23) & minute.between(0, 59))


def normalize(values: dict, keys) -> dict[str, float]:
    selected = {str(key): float(values.get(key, 0.0)) for key in keys}
    total = sum(selected.values())
    return {key: value / total * 100 if total else 0.0 for key, value in selected.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="csv.zip or directory containing trippub.csv and perpub.csv")
    parser.add_argument("--out", type=Path, default=Path("realworld_reference.json"))
    parser.add_argument("--state-fips", type=int, default=13)
    parser.add_argument("--state-name", default="georgia")
    parser.add_argument("--chunksize", type=int, default=150_000)
    args = parser.parse_args()

    regions = {"national": None, args.state_name.lower(): args.state_fips}
    person_weight = defaultdict(float)
    for chunk in iter_public_file(args.input, "perpub.csv", ["HHSTFIPS", "WTPERFIN"], args.chunksize):
        state = pd.to_numeric(chunk["HHSTFIPS"], errors="coerce")
        weight = pd.to_numeric(chunk["WTPERFIN"], errors="coerce").where(lambda value: value > 0)
        for name, fips in regions.items():
            mask = weight.notna() if fips is None else weight.notna() & state.eq(fips)
            person_weight[name] += float(weight.loc[mask].sum())

    accumulator = {
        name: {
            "trip_weight": 0.0,
            "recognized_weight": 0.0,
            "comparable_destination_weight": 0.0,
            "comparable_od_weight": 0.0,
            "destination": defaultdict(float),
            "od": defaultdict(float),
            "hour": defaultdict(float),
            "minute_weighted_sum": 0.0,
            "minute_weight": 0.0,
            "mile_weighted_sum": 0.0,
            "mile_weight": 0.0,
        }
        for name in regions
    }

    columns = ["HHSTFIPS", "WTTRDFIN", "WHYFROM", "WHYTO", "STRTTIME", "TRVLCMIN", "TRPMILES"]
    for chunk in iter_public_file(args.input, "trippub.csv", columns, args.chunksize):
        state = pd.to_numeric(chunk["HHSTFIPS"], errors="coerce")
        weight = pd.to_numeric(chunk["WTTRDFIN"], errors="coerce").where(lambda value: value > 0)
        origin = pd.to_numeric(chunk["WHYFROM"], errors="coerce").map(NHTS_2017_DETAILED_ACTIVITY_MAP)
        destination = pd.to_numeric(chunk["WHYTO"], errors="coerce").map(NHTS_2017_DETAILED_ACTIVITY_MAP)
        hour = hour_from_hhmm(chunk["STRTTIME"])
        minutes = pd.to_numeric(chunk["TRVLCMIN"], errors="coerce")
        miles = pd.to_numeric(chunk["TRPMILES"], errors="coerce")

        for name, fips in regions.items():
            region = weight.notna() if fips is None else weight.notna() & state.eq(fips)
            if not region.any():
                continue
            a = accumulator[name]
            w = weight.loc[region]
            a["trip_weight"] += float(w.sum())

            recognized = region & origin.notna() & destination.notna()
            a["recognized_weight"] += float(weight.loc[recognized].sum())

            comparable_destination = region & destination.isin(COMPARABLE_ORDER)
            a["comparable_destination_weight"] += float(weight.loc[comparable_destination].sum())
            destination_frame = pd.DataFrame({
                "destination": destination.loc[comparable_destination],
                "weight": weight.loc[comparable_destination],
            })
            for label, value in destination_frame.groupby("destination", observed=True)["weight"].sum().items():
                a["destination"][str(label)] += float(value)

            comparable_od = region & origin.isin(COMPARABLE_ORDER) & destination.isin(COMPARABLE_ORDER)
            a["comparable_od_weight"] += float(weight.loc[comparable_od].sum())
            od_frame = pd.DataFrame({
                "origin": origin.loc[comparable_od],
                "destination": destination.loc[comparable_od],
                "weight": weight.loc[comparable_od],
            })
            for (source, target), value in od_frame.groupby(["origin", "destination"], observed=True)["weight"].sum().items():
                a["od"][f"{source}->{target}"] += float(value)

            valid_hour = region & hour.notna()
            hour_frame = pd.DataFrame({"hour": hour.loc[valid_hour].astype(int), "weight": weight.loc[valid_hour]})
            for h, value in hour_frame.groupby("hour", observed=True)["weight"].sum().items():
                a["hour"][int(h)] += float(value)

            valid_minutes = region & minutes.between(0, 600)
            a["minute_weighted_sum"] += float((minutes.loc[valid_minutes] * weight.loc[valid_minutes]).sum())
            a["minute_weight"] += float(weight.loc[valid_minutes].sum())

            valid_miles = region & miles.between(0, 500)
            a["mile_weighted_sum"] += float((miles.loc[valid_miles] * weight.loc[valid_miles]).sum())
            a["mile_weight"] += float(weight.loc[valid_miles].sum())

    result: dict[str, dict] = {}
    od_keys = [f"{source}->{target}" for source in COMPARABLE_ORDER for target in COMPARABLE_ORDER]
    for name, a in accumulator.items():
        trip_weight = float(a["trip_weight"])
        result[name] = {
            "survey_year": 2017,
            "survey": "2017 National Household Travel Survey",
            "region": name,
            "state_fips": regions[name],
            "benchmark_scope": "Destination and OD shares use Home, Work, Restaurant, and Recreation; level, time, distance, and departure-hour benchmarks use all valid trips.",
            "destination_share_pct": normalize(a["destination"], COMPARABLE_ORDER),
            "od_share_pct": normalize(a["od"], od_keys),
            "departure_hour_share_pct": normalize(a["hour"], range(24)),
            "weighted_trips_per_person_day": trip_weight / person_weight[name] / 365.0 if person_weight[name] else None,
            "trip_weight_annualization_days": 365,
            "mean_trip_minutes": a["minute_weighted_sum"] / a["minute_weight"] if a["minute_weight"] else None,
            "mean_trip_miles": a["mile_weighted_sum"] / a["mile_weight"] if a["mile_weight"] else None,
            "person_weight_denominator": person_weight[name],
            "trip_weight_total": trip_weight,
            "recognized_activity_trip_share_pct": a["recognized_weight"] / trip_weight * 100 if trip_weight else 0.0,
            "comparable_destination_trip_share_pct": a["comparable_destination_weight"] / trip_weight * 100 if trip_weight else 0.0,
            "comparable_od_trip_share_pct": a["comparable_od_weight"] / trip_weight * 100 if trip_weight else 0.0,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote 2017 NHTS reference benchmarks to {args.out}")


if __name__ == "__main__":
    main()
