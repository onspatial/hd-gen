#!/usr/bin/env python3
"""Run the NHTS, simulation, and comparison source-destination analyses."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dayv2pub", type=Path, help="DAYV2PUB.CSV or Ascii.zip")
    parser.add_argument("simulation", type=Path, help="TravelJournal.csv or simulation.zip")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for figures; defaults to data_root/figs/source_destination")
    parser.add_argument("--state-fips", type=int, default=13, help="FIPS code of state to analyze; default 13=Georgia")
    parser.add_argument("--warmup-days", type=int, default=30)
    args = parser.parse_args()
    if args.out is None:
        args.out=args.simulation.parent.parent/"figs/source_destination"
    
    args.out.mkdir(parents=True,exist_ok=True)
    here = Path(__file__).resolve().parent
    day_out = args.out / "dayv2pub"
    sim_out = args.out / "simulation"
    comparison_out = args.out / "comparison"

    run([
        sys.executable, str(here / "visualize_dayv2pub_source_destination.py"),
        str(args.dayv2pub), "--out", str(day_out), "--state-fips", str(args.state_fips),
    ])
    run([
        sys.executable, str(here / "visualize_simulation_source_destination.py"),
        str(args.simulation), "--out", str(sim_out), "--warmup-days", str(args.warmup_days),
    ])
    run([
        sys.executable, str(here / "compare_nhts_simulation_flows.py"),
        str(day_out / "dayv2pub_comparable_flow_counts.csv"),
        str(sim_out / "simulation_comparable_flow_counts.csv"),
        "--out", str(comparison_out),
    ])


if __name__ == "__main__":
    main()
