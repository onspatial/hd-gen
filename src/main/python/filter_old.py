


from importlib.resources import path
import json
import os

def read_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)



if __name__ == "__main__":

    
    params = read_json("src/main/python/params.pool.json")
    filtered = []
    for param in params:
        dir = "/".join(param["config"]["run_sh_path"].split("/")[:-3])

        if dir.startswith("/home/amiri/onone"):
            filtered.append(param)

    write_json("src/main/python/params.pool.json", filtered)