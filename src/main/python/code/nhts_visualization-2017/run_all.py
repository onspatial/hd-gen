#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

FILES = {
    "hhpub.csv": "visualize_hhpub.py",
    "perpub.csv": "visualize_perpub.py",
    "trippub.csv": "visualize_trippub.py",
    "vehpub.csv": "visualize_vehpub.py",
}


def find_case_insensitive(directory: Path, filename: str) -> Path:
    matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == filename.lower()]
    if not matches:
        raise FileNotFoundError(f"Missing {filename} in {directory}")
    return matches[0]


@contextmanager
def data_directory(source: Path):
    if source.is_dir():
        yield source
        return
    if source.is_file() and source.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="nhts2017_") as temp:
            temp_path = Path(temp)
            with zipfile.ZipFile(source) as archive:
                names = {Path(name).name.lower(): name for name in archive.namelist() if not name.endswith("/")}
                for filename in FILES:
                    member = names.get(filename.lower())
                    if member is None:
                        raise FileNotFoundError(f"Missing {filename} in {source}")
                    target = temp_path / filename
                    with archive.open(member) as src, target.open("wb") as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)
            yield temp_path
        return
    raise ValueError("--data must be a directory containing the four CSVs or a ZIP archive containing them")


def run(script_dir: Path, script: str, input_path: Path, output_path: Path) -> None:
    command = [sys.executable, str(script_dir / script), str(input_path), "--out", str(output_path)]
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all 2017 NHTS visualization scripts.")
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Directory containing hhpub.csv, perpub.csv, trippub.csv, and vehpub.csv, or the ZIP containing them.",
    )
    parser.add_argument("--out", type=Path, default=Path("figs"))
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    with data_directory(args.data.resolve()) as directory:
        jobs = [
            (FILES["trippub.csv"], find_case_insensitive(directory, "trippub.csv"), args.out / "trippub"),
            (FILES["hhpub.csv"], find_case_insensitive(directory, "hhpub.csv"), args.out / "hhpub"),
            (FILES["perpub.csv"], find_case_insensitive(directory, "perpub.csv"), args.out / "perpub"),
            (FILES["vehpub.csv"], find_case_insensitive(directory, "vehpub.csv"), args.out / "vehpub"),
        ]
        for script, input_path, output_path in jobs:
            run(script_dir, script, input_path, output_path)

    print(f"All 2017 figures written under {args.out.resolve()}")


if __name__ == "__main__":
    main()
