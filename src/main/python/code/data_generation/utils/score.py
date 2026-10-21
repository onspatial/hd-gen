

def get_score_from_stat (stat1, stat2, normalize=None,selected_metrics=[]):
    stat1 = flatten_dict(stat1)
  
    stat2 = flatten_dict(stat2)
    if normalize:
        normalize = flatten_dict(normalize)

    print("Calculating score...")
    score = 0.0
    diff = {}
    for key in selected_metrics:
        # print(f"Processing key: {key}")
        if key in stat2:
            # print(f"Key {key} found in both stats")
            # print(f"Value in stat1: {stat1[key]}, Value in stat2: {stat2[key]}")
            
            try:
                
                if type(stat1[key]) in [int, float]:
                    diff[key] = (abs(stat1[key] - stat2[key]))
               
            except:
                print("Error: ", key, stat1[key], stat2[key])
                diff[key] = 0
           
    if normalize:
        for key in diff:
            if key in normalize:
                if normalize[key] == 0:
                    diff[key] = 0
                else:
                    diff[key] = diff[key] / normalize[key]
            else:
                print(f"Key {key} not found in normalize")
                diff[key] = 0
        normalization = 1
            
    else:
        normalization = 100
    # print("Diff: ", diff)
    score = float(sum(diff.values()) / len(diff))
    scaled_score =  normalization - score/normalization
    return score, scaled_score

def flatten_dict(d, parent_key="", sep="_"):
    result = {}

    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)

        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key, sep))
        else:
            result[new_key] = value

    return result