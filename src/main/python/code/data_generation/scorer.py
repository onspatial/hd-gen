
import random
import numpy
import utils.geolife as geolife
import utils.pol as pol
import utils.stat as stat
import utils.file as file
import utils.metrics_to_compare as mtc
from utils.stat import save_stat_to_file, get_stat_from_file
from utils.score import get_score_from_stat
from pathlib import Path

import sys
import os
import utils.stdout as stdout
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
   return list(selected_metrics)

if __name__ == "__main__":
    paths = find_checkins()
    print(f"Found {len(paths)} checkin paths.", silence=False, no_log=False)
    
    all_metrics = mtc.selected_metrics
    sample_sizes = [len(all_metrics), len(all_metrics)-1, len(all_metrics)-2, len(all_metrics)-3, len(all_metrics)-4, len(all_metrics)-5]
    score_threshold = 0.5
    results = {}
    print(f"Starting evaluation with sample sizes: {sample_sizes}", silence=False, no_log=False)
    for sample_size in sample_sizes:
        selected_metrics = get_selected_metrics(all_metrics,1000, sample_size)
        for idx, metrics in enumerate(selected_metrics):

            try:
                metrics = list(metrics)
                metrics = metrics + mtc.fixed_metrics
                metrics = list(set(metrics))
                metrics.sort()
                res_id = f"i_{sample_size}_{idx}"
            
                if f"{res_id}" not in results:
                    results[f"{res_id}"] = {}
                results[f"{res_id}"]["metrics"] = metrics
                scores = {}
                for path in paths:
                    score = get_score(path, selected_metrics=metrics,score_threshold=score_threshold)
                    scores[path] = score
                if numpy.max(list(scores.values())) <= score_threshold:
                    print(f"Warning: Max score {numpy.max(list(scores.values()))} not reached for metrics set {idx}.")
                    results[f"{res_id}"]["scores"] = "NP"
                else:
                    print("-------------------------------------------------")
                    print(f"Max score reached for metrics {idx} with sample size {sample_size}: {numpy.max(list(scores.values()))}",silence=False, no_log=False)
                    print(f"Metrics: {metrics}")
                    print("-------------------------------------------------")
                    results[f"{res_id}"]["scores"] = scores
            except Exception as e:
                print(f"Error processing metrics set {idx}: {e}",silence=False, no_log=False)

    print("Final results:", silence=False, no_log=False)
    for key, value in results.items():
        if 'scores' in value and value['scores'] != "NP":
            print(f"{key}: {value['metrics']}",silence=False, no_log=False)
            print(f"{key}: max score {numpy.max(list(value['scores'].values()))}, at path {max(value['scores'], key=value['scores'].get)}",silence=False, no_log=False)
            print("--------------------------------------",silence=False, no_log=False)
    