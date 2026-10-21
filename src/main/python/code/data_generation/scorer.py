
import random
import numpy
import utils.geolife as geolife
import utils.pol as pol
import utils.stat as stat
import utils.file as file
import utils.stdout as stdout
import utils.metrics_to_compare as mtc
from utils.stat import save_stat_to_file, get_stat_from_file
from utils.score import get_score_from_stat
from pathlib import Path

import sys
import os
stdout.enable_silence()

def find_checkins(city="/home/amiri/onone/onnuc/Research/hd-gen/github/src/main/python/city"):
    return [str(p) for p in Path(city).glob("*/id_*/Checkin.tsv")]

def get_statistics(checkin_path, dataset_type, which="advanced"):
    data = None
    stat_path = file.get_stat_path(checkin_path, which=which)
    statistics = get_stat_from_file(stat_path)
    if statistics:
        return statistics
    
    if dataset_type == "geolife":
        data = geolife.read(checkin_path)
    elif dataset_type == "pol":
        data = pol.read(checkin_path)
    else:
        print("Dataset type not supported")
        return
    statistics = stat.get_stat(data, which=which)
    if not file.exists(stat_path):
        save_stat_to_file(statistics, stat_path)

    return statistics


def get_score(pol_path, which="advanced",selected_metrics=mtc.selected_metrics,score_threshold=0):
    log_file = "results_score.log.txt"
    try:
        geolife_stat = get_statistics(file.get_geolife_path(), "geolife", which=which)
        pol_stat = get_statistics(pol_path, "pol", which=which)
        score, scaled_score = get_score_from_stat(geolife_stat, pol_stat, normalize=geolife_stat, selected_metrics=selected_metrics)
        if scaled_score >= score_threshold:
            file.log_print(f"{pol_path} : {(score, scaled_score)}", log_file)
        
        if scaled_score > 0 and scaled_score <= 1:
            return scaled_score
        else:
            return -1
        
    except Exception as e:
        print(f"Error getting score: {e}")
        file.log_print(f"{pol_path} : 0", log_file)
        return 0
    
def get_random_metrics(all_metrics, size):
    random_set = random.sample(all_metrics, size)
    random_set.sort()
    return random_set

def get_selected_metrics(all_metrics, output_size, sample_size):
   selected_metrics = []
   for _ in range(output_size):
       selected_metrics.append(get_random_metrics(all_metrics, sample_size))

   print(f"Selected metrics before removing duplicates: {len(selected_metrics)}", silence=False, no_log=False)
    # Remove duplicate sets of metrics
   selected_metrics = list(set(tuple(x) for x in selected_metrics))
   print(f"Selected metrics after removing duplicates: {len(selected_metrics)}", silence=False, no_log=False)
   selected_metrics.sort()
   return selected_metrics

if __name__ == "__main__":
    paths = find_checkins()
    
    all_metrics = mtc.selected_metrics
    sample_sizes = [len(all_metrics), len(all_metrics)-1, len(all_metrics)-2, len(all_metrics)-3, len(all_metrics)-4, len(all_metrics)-5]
    score_threshold = 0.1
    results = {}

    for sample_size in sample_sizes:
        selected_metrics = get_selected_metrics(all_metrics,1000, sample_size)
        for idx, metrics in enumerate(selected_metrics):
            res_id = f"i_{sample_size}_{idx}"
            print(f"Processing metrics set {idx}: {metrics}")
        
            if f"{res_id}" not in results:
                results[f"{res_id}"] = {}
            results[f"{res_id}"]["metrics"] = metrics
            scores = []
            for path in paths:
                print(f"Processing {path} with metrics {metrics}")
                score = get_score(path, selected_metrics=metrics,score_threshold=score_threshold)
                scores.append(score)
            if numpy.max(scores) <= score_threshold:
                print(f"Warning: Max score {numpy.max(scores)} not reached for metrics set {idx}.")
                results[f"{res_id}"]["scores"] = "NP"
            else:
                print("-------------------------------------------------")
                print(f"Max score reached for metrics {idx} with sample size {sample_size}: {numpy.max(scores)}",silence=False, no_log=False)
                print(f"Metrics: {metrics}",silence=False, no_log=False)
                print("-------------------------------------------------")
                results[f"{res_id}"]["scores"] = scores

    # print not NP results
    for key, value in results.items():
        if value["scores"] != "NP":
            print(f"{key}: {value['metrics']}",silence=False, no_log=False)
            print(f"{key}: max score {numpy.max(value['scores'])}",silence=False, no_log=False)
            print("--------------------------------------",silence=False, no_log=False)
    