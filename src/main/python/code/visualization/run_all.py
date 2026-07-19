#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from simviz_common import run_dataset, resolve_input
import preprocess

FILES = ['logs/Checkin.tsv', 'logs/TravelJournal.csv', 'logs/pattenrs_of_life.log', 'logs/AgentCharacteristicsTable.tsv',  'logs/JobTable.tsv', 'logs/Checkin.tsv', 'logs/SocialNetwork.tsv', 'logs/CensusTable.tsv', 'logs/InstanceDataTable.tsv', 'logs/BuildingTable.tsv', 'logs/ApartmentTable.tsv', 'logs/WorkplaceTable.tsv', 'logs/RestaurantTable.tsv', 'logs/PubTable.tsv', 'logs/ClassroomTable.tsv', 'logs/OpenPubState.tsv', 'logs/OpenRestaurantState.tsv',  'logs/FinancialJournal.csv', 'logs/FinancialAttributesJournal.csv', 'logs/InterventionJournal.csv', 'logs/VistorProfile.tsv', 'logs/Trajectory.tsv', 'logs/MovingJournal.tsv', 'logs/JobChangeJournal.tsv', 'logs/FriendFamilyGraph.dgs', 'logs/WorkGraph.dgs', 'qois/RelationshipTable.tsv', 'qois/QOI1Table.tsv', 'qois/QOI2Table.tsv', 'qois/QOI3Table.tsv', 'qois/QOI4Table.tsv', 'qois/QOI5Table.tsv', 'qois/QOI6Table.tsv','logs/AgentStateTable.tsv']


def main():
    ap=argparse.ArgumentParser(description="Run every Patterns of Life visualization script.")
    ap.add_argument("data_root",type=Path,help="Root containing logs/ and qois/")
    ap.add_argument("--out",type=Path,default=None, help="Output directory for figures; defaults to data_root/figs")
    ap.add_argument("--warmup-days",type=int,default=30)
    ap.add_argument("--chunksize",type=int,default=500000)
    ap.add_argument("--reference-region",choices=["georgia","national"],default="georgia")
    ap.add_argument("--skip-existing",action="store_true",help="Skip datasets whose output already has summary.json")
    args=ap.parse_args();
    status={}
    preprocess.run(args.data_root)
    if args.out is None:
        args.out=args.data_root/"figs"
    for rel in FILES:
        p=resolve_input(args.data_root,rel); out=args.out/p.stem
        if args.skip_existing and (out/"summary.json").exists():
            print(f"[skip] {rel}",flush=True); status[rel]="ok"; continue
        print(f"[run] {rel}",flush=True)
        try:
            run_dataset(p,out,args.warmup_days,args.chunksize,args.data_root,args.reference_region)
            status[rel]="ok"
        except Exception as e:
            status[rel]=f"ERROR: {type(e).__name__}: {e}"
            print(status[rel],flush=True)
    (args.out/"run_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
    failed=[k for k,v in status.items() if v!="ok"]
    if failed:
        raise SystemExit(f"{len(failed)} datasets failed; see run_status.json")

if __name__=="__main__": 
    
    main()
