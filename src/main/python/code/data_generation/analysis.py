import os
import sys
import json
from data_generation.scorer import get_statistics


def get_children(parent="worlds"):

    sub_folders = []
    for item in os.listdir(parent):
        item_path = os.path.join(parent, item)
        if os.path.isdir(item_path):
            sub_folders.append(item_path)

    return sub_folders


def get_properties_from_file(folder):
    properties_file = os.path.join(folder, "parameters.properties")
    properties = {}
    with open(properties_file, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()
    return properties


def get_float(value):
    try:
        return float(value)
    except ValueError:
        print(f"Error converting value to float: {value}")
        return None


def get_time_from_log(folder):
    log_file = os.path.join(folder, "logs.txt")
    initilization_time = None
    simulation_time = None
    with open(log_file, "r") as file:
        for line in file:
            if "initialize time:" in line:
                initilization_time = get_float(line.split(":")[1].split("ms")[0].strip())
            elif "Total simulation time:" in line:
                simulation_time = get_float(line.split(":")[1].split("ms")[0].strip())
    return initilization_time, simulation_time


def save_json(json_data, file_path):
    with open(file_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

def get_statistics_added(properties_json, folder):
    checkin_path = os.path.join(folder, "checkins.txt")
    statistics = get_statistics(checkin_path, "pol")
    for key, value in statistics.items():
        properties_json[key] = value
    return properties_json

if __name__ == "__main__":
    sub_folders = get_children(parent="/home/amiri/onone/ondell/Research/vanilla-analysis/worlds")
    all_properties = []
    for folder in sub_folders:
        print(f"Processing folder: {folder}")
        properties_json = get_properties_from_file(folder)
        initilization_time, simulation_time = get_time_from_log(folder)
        properties_json["initilization_time_ms"] = initilization_time
        properties_json["simulation_time_ms"] = simulation_time
        properties_json["folder"] = folder
        properties_json = get_statistics_added(properties_json, folder)
        all_properties.append(properties_json)

    save_json(all_properties, "all_properties.json")
