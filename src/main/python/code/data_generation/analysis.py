import os
import sys
import json
from scorer import get_statistics
from concurrent.futures import ProcessPoolExecutor


def get_children(parent="worlds"):

    sub_folders = []
    for item in os.listdir(parent):
        item_path = os.path.join(parent, item)
        print(f"Checking item: {item_path}", end=" ")
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

def get_time_from_line(line):
    extracted_time = None
    if line.strip().endswith("ms"):
        extracted_time = get_float(line.split(":")[1].split("ms")[0].strip())
    elif line.strip().endswith("s"):
        extracted_time = get_float(line.split(":")[1].split("s")[0].strip()) * 1000
    elif line.strip().endswith("min"):
        extracted_time = get_float(line.split(":")[1].split("min")[0].strip()) * 60 * 1000
    elif line.strip().endswith("hour"):
        extracted_time = get_float(line.split(":")[1].split("hour")[0].strip()) * 60 * 60 * 1000
    return extracted_time

def get_time_from_log(folder):
    log_file = os.path.join(folder, "logs.txt")
    initilization_time = None
    simulation_time = None
    with open(log_file, "r") as file:
        for line in file:
            if "initialize time:" in line:
                initilization_time = get_time_from_line(line)
            elif "Total simulation time:" in line:
                simulation_time = get_time_from_line(line)
    return initilization_time, simulation_time


def save_json(json_data, file_path):
    with open(file_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

def load_json(file_path):
    with open(file_path, "r") as json_file:
        return json.load(json_file)

def get_statistics_added(properties_json, folder):
    checkin_path = os.path.join(folder, "logs/logs/Checkin.tsv")
    statistics = get_statistics(checkin_path, "pol")
    for key, value in statistics.items():
        properties_json[key] = value
    return properties_json


def copy_necessary_files():
    sub_folders = get_children(parent="../vanilla-analysis/worlds")
    print(f"Found {len(sub_folders)} sub-folders to process...\n")
    for folder in sub_folders:
        print(f"Copying files from folder: {folder}", end="\r")
        os.makedirs(os.path.join("worlds", os.path.basename(folder)), exist_ok=True)
        os.makedirs(os.path.join("worlds", os.path.basename(folder), "logs", "logs"), exist_ok=True)
        os.system(f"cp {os.path.join(folder, 'logs.txt')} {os.path.join('worlds', os.path.basename(folder))}")
        os.system(f"cp {os.path.join(folder, 'parameters.properties')} {os.path.join('worlds', os.path.basename(folder))}")
        os.system(f"cp {os.path.join(folder, 'logs/logs/Checkin.tsv')} {os.path.join('worlds', os.path.basename(folder), 'logs/logs')}")
        os.system(f"cp {os.path.join(folder, 'logs/logs/pattenrs_of_life.log')} {os.path.join('worlds', os.path.basename(folder), 'logs/logs')}")
        # testing if the files are copied correctly
        os.system(f"diff {os.path.join(folder, 'logs.txt')} {os.path.join('worlds', os.path.basename(folder), 'logs.txt')}")
        os.system(f"diff {os.path.join(folder, 'parameters.properties')} {os.path.join('worlds', os.path.basename(folder), 'parameters.properties')}")
        os.system(f"diff {os.path.join(folder, 'logs/logs/Checkin.tsv')} {os.path.join('worlds', os.path.basename(folder), 'logs/logs/Checkin.tsv')}")
        os.system(f"diff {os.path.join(folder, 'logs/logs/pattenrs_of_life.log')} {os.path.join('worlds', os.path.basename(folder), 'logs/logs/pattenrs_of_life.log')}")
        print(f"Files copied from folder: {folder}")

def processing_one_folder(folder):
    try:
        print(f"Processing folder: {folder}")
        properties_json = get_properties_from_file(folder)
        initilization_time, simulation_time = get_time_from_log(folder)
        properties_json["initilization_time_ms"] = initilization_time
        properties_json["simulation_time_ms"] = simulation_time
        properties_json["folder"] = folder
        properties_json["parent_id"] = f'{folder.split("/")[-1].split("_")[0]}_{folder.split("/")[-1].split("_")[-1]}'
        properties_json = get_statistics_added(properties_json, folder)
        return properties_json
    except Exception as e:
        print(f"Error processing folder: {folder} - {e}")
        return {"folder": folder, "error": str(e)}

def get_all_properties(sub_folders, save_path="all_properties.json"):
    if os.path.exists(save_path):
        print(f"Loading properties from {save_path}...")
        return load_json(save_path)

    with ProcessPoolExecutor() as executor:
        all_properties = list(
            executor.map(processing_one_folder, sub_folders)
        )
    save_json(all_properties, save_path)
    return all_properties

if __name__ == "__main__":
    # copy_necessary_files()
    sub_folders = get_children(parent="/scratch/hamiri/vanilla-analysis/worlds-revision2")
    get_all_properties(sub_folders, save_path="all_properties_revision2.json")

   
