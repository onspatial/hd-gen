#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 15})

from main.python.code.realism.nhts_visualization.viz_common import age_group, barh, ensure_dir, heatmap, savefig, write_summary

REL = {"01":"Self", "02":"Spouse", "03":"Child", "04":"Parent", "05":"Sibling",
       "06":"Other relative", "07":"Unmarried partner", "08":"Non-relative"}
SEX = {"01":"Male", "02":"Female"}
DRIVER = {"01":"Driver", "02":"Not driver"}
WORKER = {"01":"Worker", "02":"Not worker"}
STATUS = {
    "C1":"Completed by subject", "C2":"Completed by proxy", "J1":"Age 0-4",
    "LH":"Language/hearing/speech", "LM":"Maximum calls-language", "LP":"Language problem",
    "MC":"Maximum calls", "ML":"Maximum calls-language", "MR":"Maximum calls-refusal",
    "ND":"Deceased", "NG":"Military deployment", "NO":"Other nonresponse",
    "NP":"Not available", "NR":"Non-residential", "NS":"Subject sick", "NW":"Non-working",
    "OE":"Enumeration error", "OO":"Out of scope", "R3":"Final refusal re-release",
    "RB":"Final refusal", "RM":"Maximum calls refusal",
}


def clean_code(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize the 2009 NHTS household roster SAS dataset.")
    ap.add_argument("input", type=Path, help="Path to pvarpub.sas7bdat")
    ap.add_argument("--out", type=Path, default=Path("figs/roster"))
    args = ap.parse_args()
    out = ensure_dir(args.out)

    try:
        import pyreadstat
    except ImportError as exc:
        raise SystemExit("pyreadstat is required: pip install pyreadstat") from exc

    wide, _ = pyreadstat.read_sas7bdat(args.input)
    household_rows = len(wide)
    members = []
    for i in range(1, 15):
        age_all = pd.to_numeric(wide[f"AGE_P{i}"], errors="coerce")
        mask = age_all.notna() & (age_all >= 0)
        if not mask.any():
            continue
        sub = wide.loc[mask, ["HOUSEID", f"DRVR_P{i}", f"REL_P{i}", f"SEX_P{i}", f"STAT_P{i}", f"WKR_P{i}"]]
        d = pd.DataFrame({
            "HOUSEID": sub["HOUSEID"].to_numpy(),
            "position": np.full(mask.sum(), i, dtype=np.int8),
            "age": age_all.loc[mask].to_numpy(),
            "driver": clean_code(sub[f"DRVR_P{i}"]).to_numpy(),
            "relation": clean_code(sub[f"REL_P{i}"]).to_numpy(),
            "sex": clean_code(sub[f"SEX_P{i}"]).to_numpy(),
            "status": sub[f"STAT_P{i}"].astype("string").str.strip().to_numpy(),
            "worker": clean_code(sub[f"WKR_P{i}"]).to_numpy(),
        })
        members.append(d)
    people = pd.concat(members, ignore_index=True)
    del wide, members
    people["age_plot"] = people["age"].replace(92, 89)
    people["age_group"] = age_group(people["age"])
    people["sex_label"] = people["sex"].map(SEX).fillna("Unknown")
    people["relation_label"] = people["relation"].map(REL).fillna("Unknown")
    people["driver_label"] = people["driver"].map(DRIVER).fillna("Unknown")
    people["worker_label"] = people["worker"].map(WORKER).fillna("Unknown")
    people["status_label"] = people["status"].map(STATUS).fillna("Other/unknown")
    figures: list[str] = []

    household_size = people.groupby("HOUSEID").size().clip(upper=8).astype(str).replace("8", "8+").value_counts()
    barh(household_size, "Roster household size", "Households", out, "01_household_size.png")
    figures.append("01_household_size.png")

    bins = np.arange(0, 95, 5)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(people["age_plot"], bins=bins)
   #  ax.set_title("Age distribution of all rostered household members")
    ax.set_xlabel("Age")
    ax.set_ylabel("People")
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out, "02_age_distribution.png")
    figures.append("02_age_distribution.png")

    # Age pyramid.
    age_bin = pd.cut(people["age_plot"], bins=np.arange(0, 95, 5), right=False)
    tab = pd.crosstab(age_bin, people["sex_label"])
    male = -tab.get("Male", pd.Series(0, index=tab.index))
    female = tab.get("Female", pd.Series(0, index=tab.index))
    y = np.arange(len(tab))
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(y, male, label="Male")
    ax.barh(y, female, label="Female")
    ax.set_yticks(y, [str(x) for x in tab.index])
   #  ax.set_title("Roster age pyramid")
    ax.set_xlabel("People, male shown left")
    ax.legend()
    ax.grid(axis="x", alpha=0.2)
    savefig(fig, out, "03_age_pyramid.png")
    figures.append("03_age_pyramid.png")

    rel = people["relation_label"].value_counts().drop("Unknown", errors="ignore")
    barh(rel, "Relationship to household respondent", "Rostered people", out, "04_relationships.png")
    figures.append("04_relationships.png")

    # Driver rate by age and sex.
    d = people[people["driver_label"].isin(["Driver", "Not driver"]) & people["sex_label"].isin(["Male", "Female"])]
    rate = d.assign(is_driver=(d["driver_label"] == "Driver").astype(float)).pivot_table(
        index="age_group", columns="sex_label", values="is_driver", aggfunc="mean") * 100
    heatmap(rate, "Licensed-driver rate by age and sex", out, "05_driver_rate_by_age_sex.png",
            "Sex", "Age group", fmt=".0f")
    figures.append("05_driver_rate_by_age_sex.png")

    # Worker rate by age.
    w = people[people["worker_label"].isin(["Worker", "Not worker"])].copy()
    wr = w.assign(is_worker=(w["worker_label"] == "Worker").astype(float)).groupby("age_group", observed=True)["is_worker"].mean() * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(wr.index.astype(str), wr.values, marker="o")
   #  ax.set_title("Worker rate by age group")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.25)
    savefig(fig, out, "06_worker_rate_by_age.png")
    figures.append("06_worker_rate_by_age.png")

    status = people["status_label"].value_counts()
    barh(status, "Person-interview completion and nonresponse status", "Rostered people", out,
         "07_interview_status.png", top=15)
    figures.append("07_interview_status.png")

    # Completion by roster position.
    people["completed"] = people["status"].isin(["C1", "C2"])
    completion = people.groupby("position")["completed"].agg(["mean", "count"])
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(completion.index, completion["mean"] * 100, marker="o")
    ax1.set_xlabel("Roster position")
    ax1.set_ylabel("Interview completion rate, percent")
    ax1.set_title("Interview completion by household roster position")
    ax1.set_xticks(range(1, 15))
    ax1.set_ylim(0, 105)
    ax1.grid(alpha=0.25)
    savefig(fig, out, "08_completion_by_roster_position.png")
    figures.append("08_completion_by_roster_position.png")

    completed = people[people["status"].isin(["C1", "C2"])]["status"].map({"C1":"Self", "C2":"Proxy"}).value_counts()
    barh(completed, "Who completed the person interview", "Completed interviews", out,
         "09_self_vs_proxy.png")
    figures.append("09_self_vs_proxy.png")

    write_summary(out, "pvarpub roster", household_rows, figures, [
        f"Reshaped {len(people):,} valid household-member records from 14 roster slots.",
        "The roster file has no survey weight, so these plots show unweighted sample counts and rates.",
    ])


if __name__ == "__main__":
    main()
