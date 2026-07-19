#!/usr/bin/env python3
"""Run 2017 NHTS, simulation, and source-destination comparison analyses."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def default_output(simulation: Path) -> Path:
    root = simulation.parent.parent if simulation.parent.name in {"logs", "qois"} else simulation.parent
    return root / "figs" / "source_destination"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trippub", type=Path, help="2017 trippub.csv, csv.zip, or directory containing trippub.csv")
    parser.add_argument("simulation", type=Path, help="TravelJournal.csv, simulation.zip, or simulation directory")
    parser.add_argument("--out", type=Path, default=None, help="Output directory; defaults beside the simulation data")
    parser.add_argument("--state-fips", type=int, default=13, help="NHTS household-state FIPS code; default 13 is Georgia")
    parser.add_argument("--national", action="store_true", help="Use national 2017 NHTS data instead of one state")
    parser.add_argument("--warmup-days", type=int, default=30)
    parser.add_argument("--nhts-chunksize", type=int, default=150_000)
    parser.add_argument("--simulation-chunksize", type=int, default=250_000)
    args = parser.parse_args()

    output = args.out or default_output(args.simulation)
    output.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    nhts_out = output / "nhts_2017"
    simulation_out = output / "simulation"
    comparison_out = output / "comparison"

    nhts_command = [
        sys.executable,
        str(here / "visualize_trippub_source_destination.py"),
        str(args.trippub),
        "--out", str(nhts_out),
        "--chunksize", str(args.nhts_chunksize),
    ]
    if args.national:
        nhts_command.append("--national")
    else:
        nhts_command.extend(["--state-fips", str(args.state_fips)])
    run(nhts_command)

    run([
        sys.executable,
        str(here / "visualize_simulation_source_destination.py"),
        str(args.simulation),
        "--out", str(simulation_out),
        "--warmup-days", str(args.warmup_days),
        "--chunksize", str(args.simulation_chunksize),
    ])
    run([
        sys.executable,
        str(here / "compare_nhts_simulation_flows.py"),
        str(nhts_out / "trippub_comparable_flow_counts.csv"),
        str(simulation_out / "simulation_comparable_flow_counts.csv"),
        "--out", str(comparison_out),
    ])


if __name__ == "__main__":
    main()
