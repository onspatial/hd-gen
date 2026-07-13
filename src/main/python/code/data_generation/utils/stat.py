from utils import file
import utils.helpers as helpers
import pandas
import math
import numpy 

EARTH_RADIUS_M = 6371008.8

def get_stat_from_file(path="data/geolife/stat.json"):
    stat = None
    try:
        if file.exists(path):
            stat = file.load_json(path)
    except Exception as e:
        print("Error: loading stat from file")
        print(e)
    return stat
    
def save_stat_to_file(stat, path="data/geolife/stat.json"):
    try:
        stat = helpers.get_json_compatible_dict(stat)
        file.save_json(stat, path)
    except Exception as e:
        print("Error: saving stat to file")
        print(e)
        return None




def _summary(series):
    s = pandas.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return {
            "count": 0, "mean": None, "std": None, "min": None,
            "p05": None, "p25": None, "median": None, "p75": None,
            "p90": None, "p95": None, "p99": None, "max": None,
        }

    q = s.quantile([0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=0)),
        "min": float(s.min()),
        "p05": float(q.loc[0.05]),
        "p25": float(q.loc[0.25]),
        "median": float(q.loc[0.50]),
        "p75": float(q.loc[0.75]),
        "p90": float(q.loc[0.90]),
        "p95": float(q.loc[0.95]),
        "p99": float(q.loc[0.99]),
        "max": float(s.max()),
    }


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, numpy.integer):
        return int(obj)
    if isinstance(obj, numpy.floating):
        return None if numpy.isnan(obj) else float(obj)
    if isinstance(obj, float):
        return None if math.isnan(obj) else obj
    if pandas.isna(obj) if obj is not None else False:
        return None
    return obj


def _entropy_from_counts(counts):
    counts = pandas.Series(counts, dtype="float64")
    counts = counts[counts > 0]
    if counts.sum() == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-(p * numpy.log2(p)).sum())


def _js_divergence_dict(p, q):
    keys = sorted(set(p.keys()) | set(q.keys()))
    pv = numpy.array([float(p.get(k, 0.0)) for k in keys], dtype=float)
    qv = numpy.array([float(q.get(k, 0.0)) for k in keys], dtype=float)

    if pv.sum() > 0:
        pv = pv / pv.sum()
    if qv.sum() > 0:
        qv = qv / qv.sum()

    m = 0.5 * (pv + qv)

    def kl(a, b):
        mask = a > 0
        return float(numpy.sum(a[mask] * numpy.log2(a[mask] / b[mask])))

    return 0.5 * kl(pv, m) + 0.5 * kl(qv, m)


def _haversine_m(lat1, lon1, lat2, lon2):
    lat1 = numpy.radians(pandas.to_numeric(lat1, errors="coerce").astype(float))
    lon1 = numpy.radians(pandas.to_numeric(lon1, errors="coerce").astype(float))
    lat2 = numpy.radians(pandas.to_numeric(lat2, errors="coerce").astype(float))
    lon2 = numpy.radians(pandas.to_numeric(lon2, errors="coerce").astype(float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        numpy.sin(dlat / 2.0) ** 2
        + numpy.cos(lat1) * numpy.cos(lat2) * numpy.sin(dlon / 2.0) ** 2
    )
    return 2 * EARTH_RADIUS_M * numpy.arcsin(numpy.sqrt(a))


def make_location_id(df, grid_size_m=100):
    if "VenueId" in df.columns:
        venue = df["VenueId"].astype(str)
        if venue.notna().mean() > 0.8:
            return venue

    if "LocationID" in df.columns:
        return df["LocationID"].astype(str)

    lat = pandas.to_numeric(df["Latitude"], errors="coerce")
    lon = pandas.to_numeric(df["Longitude"], errors="coerce")

    lat_step = grid_size_m / 111_320.0
    lon_step = grid_size_m / (111_320.0 * numpy.cos(numpy.radians(lat.mean())))

    lat_bin = numpy.floor(lat / lat_step).astype("Int64")
    lon_bin = numpy.floor(lon / lon_step).astype("Int64")

    return lat_bin.astype(str) + "," + lon_bin.astype(str)


def _prepare_mobility_df(
    data,
    coordinate_decimals=5,
    recompute_distance=False,
    min_trip_distance_m=10,
    max_trip_distance_m=100000,
):
    df = data.copy()

    if "AgentID" not in df.columns and "UserId" in df.columns:
        df = df.rename(columns={"UserId": "AgentID"})
    if "ArrivingTime" not in df.columns and "CheckinTime" in df.columns:
        df = df.rename(columns={"CheckinTime": "ArrivingTime"})

    if "AgentID" not in df.columns or "ArrivingTime" not in df.columns:
        raise ValueError("Input must contain AgentID and ArrivingTime.")

    df["AgentID"] = pandas.to_numeric(df["AgentID"], errors="coerce")
    df["ArrivingTime"] = pandas.to_datetime(df["ArrivingTime"], errors="coerce")
    df = df.dropna(subset=["AgentID", "ArrivingTime"]).copy()
    df["AgentID"] = df["AgentID"].astype(int)

    df = df.sort_values(["AgentID", "ArrivingTime"]).reset_index(drop=True)

    df["Date"] = df["ArrivingTime"].dt.date
    df["Hour"] = df["ArrivingTime"].dt.hour
    df["DayOfWeek"] = df["ArrivingTime"].dt.dayofweek
    df["IsWeekend"] = df["DayOfWeek"].isin([5, 6])

    df["LocationID"] = make_location_id(df, grid_size_m=100)
    df["PrevTime"] = df.groupby("AgentID")["ArrivingTime"].shift(1)
    df["PrevLocationID"] = df.groupby("AgentID")["LocationID"].shift(1)
    df["TimeDeltaSeconds"] = (df["ArrivingTime"] - df["PrevTime"]).dt.total_seconds()
    df["HasPrevious"] = df["PrevTime"].notna()

    if "VenueType" in df.columns:
        df["VenueType"] = df["VenueType"].astype(str)
        df["PrevVenueType"] = df.groupby("AgentID")["VenueType"].shift(1)

    if recompute_distance or "Distance" not in df.columns:
        if "Latitude" not in df.columns or "Longitude" not in df.columns:
            raise ValueError("Distance missing. Need Latitude/Longitude to compute it.")

        df["PrevLatitude"] = df.groupby("AgentID")["Latitude"].shift(1)
        df["PrevLongitude"] = df.groupby("AgentID")["Longitude"].shift(1)
        df["Distance"] = _haversine_m(
            df["PrevLatitude"],
            df["PrevLongitude"],
            df["Latitude"],
            df["Longitude"],
        )
    else:
        df["Distance"] = pandas.to_numeric(df["Distance"], errors="coerce")

    df.loc[~df["HasPrevious"], "Distance"] = 0.0
    df.loc[df["Distance"] < 0, "Distance"] = numpy.nan

    df["DistanceOutlier"] = df["Distance"] > max_trip_distance_m
    df.loc[df["DistanceOutlier"], "Distance"] = numpy.nan

    df["SpeedMps"] = df["Distance"] / df["TimeDeltaSeconds"]
    df.loc[df["TimeDeltaSeconds"] <= 0, "SpeedMps"] = numpy.nan

    df["IsTrip"] = (
        df["HasPrevious"]
        & df["Distance"].notna()
        & (df["Distance"] >= min_trip_distance_m)
        & (df["TimeDeltaSeconds"].fillna(0) > 0)
    )

    df["TripDistance"] = df["Distance"].where(df["IsTrip"], 0.0)
    df["TripDistanceOnly"] = df["Distance"].where(df["IsTrip"], numpy.nan)

    return df


def _compute_radius_of_gyration(df):
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        return pandas.Series(dtype=float)

    tmp = df[["AgentID", "Latitude", "Longitude"]].copy()
    tmp["Latitude"] = pandas.to_numeric(tmp["Latitude"], errors="coerce")
    tmp["Longitude"] = pandas.to_numeric(tmp["Longitude"], errors="coerce")
    tmp = tmp.dropna(subset=["Latitude", "Longitude"])

    if len(tmp) == 0:
        return pandas.Series(dtype=float)

    lat_rad = numpy.radians(tmp["Latitude"].astype(float))
    lon_rad = numpy.radians(tmp["Longitude"].astype(float))
    lat0 = float(lat_rad.mean())

    tmp["_x"] = EARTH_RADIUS_M * lon_rad * math.cos(lat0)
    tmp["_y"] = EARTH_RADIUS_M * lat_rad

    x_mean = tmp.groupby("AgentID")["_x"].transform("mean")
    y_mean = tmp.groupby("AgentID")["_y"].transform("mean")

    tmp["_sqdist"] = (tmp["_x"] - x_mean) ** 2 + (tmp["_y"] - y_mean) ** 2
    return numpy.sqrt(tmp.groupby("AgentID")["_sqdist"].mean())


def _infer_home_locations(df, night_start_hour=20, night_end_hour=6):
    night = df[(df["Hour"] >= night_start_hour) | (df["Hour"] < night_end_hour)]

    def mode_location(base):
        counts = (
            base.groupby(["AgentID", "LocationID"], observed=True)
            .size()
            .reset_index(name="n")
            .sort_values(["AgentID", "n"], ascending=[True, False])
        )
        if len(counts) == 0:
            return pandas.Series(dtype=object)
        return counts.drop_duplicates("AgentID").set_index("AgentID")["LocationID"]

    return mode_location(night).combine_first(mode_location(df))


def _integer_distribution(values, max_value=20):
    s = pandas.to_numeric(values, errors="coerce").dropna().astype(int)
    if len(s) == 0:
        return {}

    clipped = s.where(s <= max_value, max_value + 1)
    counts = clipped.value_counts().sort_index()
    total = counts.sum()

    out = {}
    for k, v in counts.items():
        label = f">{max_value}" if k == max_value + 1 else str(int(k))
        out[label] = float(v / total)
    return out


def _bin_distribution(values, bins, unit_divisor=1.0):
    v = pandas.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float) / unit_divisor
    if len(v) == 0:
        return {}

    counts, edges = numpy.histogram(v, bins=bins)
    total = counts.sum()
    if total == 0:
        return {}

    out = {}
    for i, count in enumerate(counts):
        left, right = edges[i], edges[i + 1]
        label = f"[{left:g},{right:g}]" if i == len(counts) - 1 else f"[{left:g},{right:g})"
        out[label] = float(count / total)

    return out


def _level_of_exploration_distribution(df, max_rank=10):
    counts = (
        df.groupby(["AgentID", "LocationID"], observed=True)
        .size()
        .reset_index(name="visits")
    )

    if len(counts) == 0:
        return {}, {}

    counts = counts.sort_values(["AgentID", "visits"], ascending=[True, False])
    counts["rank"] = counts.groupby("AgentID").cumcount() + 1

    total_visits = counts["visits"].sum()
    top = counts[counts["rank"] <= max_rank].groupby("rank")["visits"].sum()
    other = counts[counts["rank"] > max_rank]["visits"].sum()

    distribution = {str(i): 0.0 for i in range(1, max_rank + 1)}
    for rank, visits in top.items():
        distribution[str(int(rank))] = float(visits / total_visits)
    distribution[f">{max_rank}"] = float(other / total_visits)

    total_by_agent = counts.groupby("AgentID")["visits"].transform("sum")
    counts["p"] = counts["visits"] / total_by_agent
    counts["neg_p_log2_p"] = -counts["p"] * numpy.log2(counts["p"])

    entropy = counts.groupby("AgentID")["neg_p_log2_p"].sum()
    n_locations = counts.groupby("AgentID")["LocationID"].count()
    normalized_entropy = entropy / numpy.log2(n_locations.replace(1, numpy.nan))
    normalized_entropy = normalized_entropy.fillna(0.0)

    top1_share = counts[counts["rank"] == 1].set_index("AgentID")["p"]
    top3_share = counts[counts["rank"] <= 3].groupby("AgentID")["p"].sum()

    per_agent = {
        "location_entropy": entropy,
        "normalized_location_entropy": normalized_entropy,
        "top1_location_share": top1_share,
        "top3_location_share": top3_share,
    }

    return distribution, per_agent


def _top_records(df, cols, n=20):
    if any(col not in df.columns for col in cols):
        return []

    return (
        df.groupby(cols, observed=True)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(n)
        .to_dict(orient="records")
    )


def get_per_day_stat(data, **kwargs):
    df = _prepare_mobility_df(data, **kwargs)

    agg = {
        "NumberOfCheckins": ("ArrivingTime", "size"),
        "NumberOfTrips": ("IsTrip", "sum"),
        "TotalDistance": ("TripDistance", "sum"),
        "AverageTripDistance": ("TripDistanceOnly", "mean"),
        "MedianTripDistance": ("TripDistanceOnly", "median"),
        "MaxDistance": ("TripDistanceOnly", "max"),
        "MinDistance": ("TripDistanceOnly", "min"),
        "UniqueLocations": ("LocationID", "nunique"),
        "FirstCheckin": ("ArrivingTime", "min"),
        "LastCheckin": ("ArrivingTime", "max"),
    }

    if "VenueType" in df.columns:
        agg["UniqueVenueTypes"] = ("VenueType", "nunique")

    per_day = df.groupby(["AgentID", "Date"], observed=True).agg(**agg).reset_index()
    per_day["ActiveSpanHours"] = (
        per_day["LastCheckin"] - per_day["FirstCheckin"]
    ).dt.total_seconds() / 3600.0

    return per_day.drop(columns=["FirstCheckin", "LastCheckin"])


def get_stat(
    data,
    reference_stat=None,
    coordinate_decimals=5,
    recompute_distance=False,
    min_trip_distance_m=10,
    max_trip_distance_m=100000,
    max_rank=10,
    top_n=20,
):
    df = _prepare_mobility_df(
        data,
        coordinate_decimals=coordinate_decimals,
        recompute_distance=recompute_distance,
        min_trip_distance_m=min_trip_distance_m,
        max_trip_distance_m=max_trip_distance_m,
    )

    if df is None or len(df) == 0:
        return {
            "error": "empty_dataframe",
            "message": (
                "No rows available for scoring. Most likely the bounding box removed all rows, "
                "or coordinate conversion produced coordinates outside the AOI."
            ),
            "basic": {
                "n_agents": 0,
                "n_checkins": 0,
                "n_trips": 0,
                "n_unique_locations": 0,
                "n_days": 0,
            },
            "distance_per_trip": None,
            "average_distance": None,
            "max_distance": None,
            "median_distance": None,
            "distributions": {},
        }

    per_day = get_per_day_stat(
        df,
        coordinate_decimals=coordinate_decimals,
        recompute_distance=False,
        min_trip_distance_m=min_trip_distance_m,
        max_trip_distance_m=max_trip_distance_m,
    )

    trip_df = df[df["IsTrip"]].copy()

    agent = df.groupby("AgentID", observed=True).agg(
        checkins=("ArrivingTime", "size"),
        active_days=("Date", "nunique"),
        unique_locations=("LocationID", "nunique"),
    )

    agent["trips"] = df.groupby("AgentID", observed=True)["IsTrip"].sum()
    agent["total_distance_m"] = df.groupby("AgentID", observed=True)["TripDistance"].sum()
    agent["avg_daily_distance_m"] = agent["total_distance_m"] / agent["active_days"].replace(0, numpy.nan)
    agent["checkins_per_active_day"] = agent["checkins"] / agent["active_days"].replace(0, numpy.nan)
    agent["trips_per_active_day"] = agent["trips"] / agent["active_days"].replace(0, numpy.nan)

    rg = _compute_radius_of_gyration(df)
    if len(rg) > 0:
        agent["radius_of_gyration_m"] = rg

    home_locations = _infer_home_locations(df)
    df_home = df.join(home_locations.rename("HomeLocationID"), on="AgentID")
    df_home["IsHomeVisit"] = df_home["LocationID"] == df_home["HomeLocationID"]
    agent["home_visit_share"] = df_home.groupby("AgentID", observed=True)["IsHomeVisit"].mean()

    le_dist, concentration = _level_of_exploration_distribution(df, max_rank=max_rank)
    for name, series in concentration.items():
        agent[name] = series

    moved = df[df["HasPrevious"] & (df["LocationID"] != df["PrevLocationID"])].copy()
    od_counts = moved.groupby(["PrevLocationID", "LocationID"], observed=True).size()

    daily_total = per_day.groupby("Date", observed=True)["TotalDistance"].sum()
    daily_active_agents = per_day.groupby("Date", observed=True)["AgentID"].nunique()

    hourly_dist = (df["Hour"].value_counts().sort_index() / len(df)).to_dict()
    weekday_dist = (df["DayOfWeek"].value_counts().sort_index() / len(df)).to_dict()

    distributions = {
        "number_locations_visited_per_agent_day": _integer_distribution(
            per_day["UniqueLocations"], max_value=20
        ),
        "level_of_exploration_rank": le_dist,
        "trip_distance_km": _bin_distribution(
            trip_df["Distance"],
            bins=[0, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100],
            unit_divisor=1000.0,
        ),
        "daily_distance_per_agent_km": _bin_distribution(
            per_day["TotalDistance"],
            bins=[0, 0.5, 1, 2, 5, 10, 20, 50, 100, 200],
            unit_divisor=1000.0,
        ),
    }

    if "radius_of_gyration_m" in agent.columns:
        distributions["radius_of_gyration_km"] = _bin_distribution(
            agent["radius_of_gyration_m"],
            bins=[0, 0.5, 1, 2, 5, 10, 20, 50, 100, 200],
            unit_divisor=1000.0,
        )

    result = {
        "basic": {
            "n_agents": int(df["AgentID"].nunique()),
            "n_checkins": int(len(df)),
            "n_trips": int(df["IsTrip"].sum()),
            "n_unique_locations": int(df["LocationID"].nunique()),
            "start_time": str(df["ArrivingTime"].min()),
            "end_time": str(df["ArrivingTime"].max()),
            "n_days": int(df["Date"].nunique()),
        },
        "data_quality": {
            "distance_outlier_rows": int(df["DistanceOutlier"].sum()),
            "zero_or_stationary_transition_share": float(
                ((df["HasPrevious"]) & (~df["IsTrip"])).sum()
                / max(int(df["HasPrevious"].sum()), 1)
            ),
            "nonpositive_time_delta_rows": int((df["TimeDeltaSeconds"] <= 0).sum()),
            "missing_distance_rows": int(df["Distance"].isna().sum()),
        },
        "distance": {
            "total_distance_m": float(trip_df["Distance"].sum()) if len(trip_df) else 0.0,
            "total_distance_km": float(trip_df["Distance"].sum() / 1000.0) if len(trip_df) else 0.0,
            "distance_per_trip_m": float(trip_df["Distance"].mean()) if len(trip_df) else None,
            "distance_per_checkin_m": float(trip_df["Distance"].sum() / len(df)) if len(df) else None,
            "per_trip_distance_m": _summary(trip_df["Distance"]),
            "per_agent_total_distance_m": _summary(agent["total_distance_m"]),
            "per_agent_day_total_distance_m": _summary(per_day["TotalDistance"]),
            "daily_total_distance_m": _summary(daily_total),
        },
        "visitation": {
            "checkins_per_agent": _summary(agent["checkins"]),
            "trips_per_agent": _summary(agent["trips"]),
            "active_days_per_agent": _summary(agent["active_days"]),
            "checkins_per_agent_day": _summary(per_day["NumberOfCheckins"]),
            "trips_per_agent_day": _summary(per_day["NumberOfTrips"]),
            "number_locations_visited_Nl_per_agent_day": _summary(per_day["UniqueLocations"]),
            "unique_locations_per_agent": _summary(agent["unique_locations"]),
            "home_visit_share": _summary(agent["home_visit_share"]),
        },
        "spatial_exploration": {
            "radius_of_gyration_Rg_m": (
                _summary(agent["radius_of_gyration_m"])
                if "radius_of_gyration_m" in agent.columns
                else {}
            ),
            "level_of_exploration_Le_rank_distribution": le_dist,
            "location_entropy_per_agent": _summary(agent["location_entropy"]),
            "normalized_location_entropy_per_agent": _summary(
                agent["normalized_location_entropy"]
            ),
            "top1_location_share_per_agent": _summary(agent["top1_location_share"]),
            "top3_location_share_per_agent": _summary(agent["top3_location_share"]),
        },
        "temporal": {
            "inter_checkin_gap_hours": _summary(
                df.loc[df["HasPrevious"], "TimeDeltaSeconds"] / 3600.0
            ),
            "trip_duration_gap_hours": _summary(trip_df["TimeDeltaSeconds"] / 3600.0),
            "speed_mps": _summary(trip_df["SpeedMps"]),
            "active_span_hours_per_agent_day": _summary(per_day["ActiveSpanHours"]),
            "daily_active_agents": _summary(daily_active_agents),
            "weekend_checkin_share": float(df["IsWeekend"].mean()) if len(df) else None,
            "night_checkin_share_0_to_6": float((df["Hour"] < 6).mean()) if len(df) else None,
            "hourly_checkin_distribution": {str(int(k)): float(v) for k, v in hourly_dist.items()},
            "dayofweek_checkin_distribution": {str(int(k)): float(v) for k, v in weekday_dist.items()},
        },
        "transitions": {
            "n_unique_od_pairs": int(len(od_counts)),
            "od_transition_entropy": _entropy_from_counts(od_counts.values),
            "top_od_transition_share": (
                float(od_counts.max() / od_counts.sum())
                if len(od_counts) and od_counts.sum() > 0
                else None
            ),
            "top_od_transitions": _top_records(
                moved, ["PrevLocationID", "LocationID"], n=top_n
            ),
        },
        "distributions": distributions,
    }

    if "VenueType" in df.columns:
        venue_counts = df["VenueType"].value_counts()
        result["semantics"] = {
            "n_unique_venue_types": int(df["VenueType"].nunique()),
            "venue_type_entropy": _entropy_from_counts(venue_counts.values),
            "top_venue_types": [
                {
                    "VenueType": str(k),
                    "count": int(v),
                    "share": float(v / venue_counts.sum()),
                }
                for k, v in venue_counts.head(top_n).items()
            ],
            "unique_venue_types_per_agent_day": (
                _summary(per_day["UniqueVenueTypes"])
                if "UniqueVenueTypes" in per_day.columns
                else {}
            ),
            "top_venue_type_transitions": _top_records(
                df[df["HasPrevious"] & df["PrevVenueType"].notna()],
                ["PrevVenueType", "VenueType"],
                n=top_n,
            ),
        }

    if reference_stat is not None:
        result["js_divergence"] = {}
        ref_dist = reference_stat.get("distributions", {})
        for name, dist in distributions.items():
            if name in ref_dist:
                result["js_divergence"][name] = _js_divergence_dict(dist, ref_dist[name])

    result["distance_per_trip"] = result["distance"]["distance_per_trip_m"]
    result["average_distance"] = result["distance"]["per_agent_day_total_distance_m"]["mean"]
    result["max_distance"] = result["distance"]["per_trip_distance_m"]["max"]
    result["median_distance"] = result["distance"]["per_agent_day_total_distance_m"]["median"]

    return _to_jsonable(result)