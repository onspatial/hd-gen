#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def run(script_dir: Path, script: str, input_path: Path, out: Path) -> None:
    cmd = [sys.executable, str(script_dir / script), str(input_path), "--out", str(out)]
    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run all NHTS visualization scripts.")
    ap.add_argument("--ascii-dir", type=Path, required=True,
                    help="Directory containing DAYV2PUB.CSV, HHV2PUB.CSV, PERV2PUB.CSV, VEHV2PUB.CSV")
    ap.add_argument("--replicates-dir", type=Path, required=True,
                    help="Directory containing hh50wt.csv and per50wt.csv")
    ap.add_argument("--roster-file", type=Path, required=True, help="Path to pvarpub.sas7bdat")
    ap.add_argument("--trip-dir", type=Path, required=True, help="Directory containing chntrp09.csv and tour09.csv")
    ap.add_argument("--out", type=Path, default=Path("figs"))
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    jobs = [
        ("visualize_dayv2pub.py", args.ascii_dir / "DAYV2PUB.CSV", args.out / "dayv2pub"),
        ("visualize_hhv2pub.py", args.ascii_dir / "HHV2PUB.CSV", args.out / "hhv2pub"),
        ("visualize_perv2pub.py", args.ascii_dir / "PERV2PUB.CSV", args.out / "perv2pub"),
        ("visualize_vehv2pub.py", args.ascii_dir / "VEHV2PUB.CSV", args.out / "vehv2pub"),
        ("visualize_hh50wt.py", args.replicates_dir / "hh50wt.csv", args.out / "hh50wt"),
        ("visualize_per50wt.py", args.replicates_dir / "per50wt.csv", args.out / "per50wt"),
        ("visualize_roster.py", args.roster_file, args.out / "roster"),
        ("visualize_chntrp09.py", args.trip_dir / "chntrp09.csv", args.out / "chntrp09"),
        ("visualize_tour09.py", args.trip_dir / "tour09.csv", args.out / "tour09"),
    ]
    for script, input_path, out in jobs:
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        run(script_dir, script, input_path, out)
    print(f"All figures written under {args.out.resolve()}")


if __name__ == "__main__":
    main()
