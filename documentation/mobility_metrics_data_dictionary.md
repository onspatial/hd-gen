# Mobility Statistics: Flattened Metric Data Dictionary

This document defines **all 384 flattened metric keys** in `all_metrics = selected_metrics`, grouped by their original `get_stat_advanced` sections. The meanings are derived from the supplied function and the accompanying example output. Where a metric is computed in a helper whose implementation was not provided, that limitation is stated explicitly.

## Reading the metrics

- **Agent:** an individual `AgentID`. **Check-in:** one row in the processed mobility table. **Agent-day:** one observed `(AgentID, Date)` combination. **Trip:** a check-in/transition where `IsTrip` is `True` following preprocessing. **Location:** a distinct `LocationID` after any coordinate rounding.
- Statistics describe the **processed dataset**, not necessarily the original raw rows. The preprocessing can filter or classify trips, and may recompute distances depending on the function parameters.
- **Shares and histogram entries** are proportions between 0 and 1, not percentages. Multiply by 100 for percentages. **Distance** is in meters (`m`) unless marked kilometers (`km`).
- The meaning of an unqualified `day` is a date represented in the data, not necessarily a full 24-hour observation. Times and hours use the timestamps as processed; timezone handling is not shown.

### Common suffixes for summary metrics

Every key ending in one of the following suffixes summarizes the distribution of the _parent quantity_ over the parent metric's observational units (trips, agents, agent-days, or dates). Each complete flattened key is explicitly enumerated below.

| Flattened metric | Definition                                                                          | Unit / scale       |
| ---------------- | ----------------------------------------------------------------------------------- | ------------------ |
| `_count`         | Number of nonmissing values included in the summary.                                | observations       |
| `_mean`          | Arithmetic mean across observations.                                                | parent metric unit |
| `_std`           | Standard deviation across observations; the helper determines its exact convention. | parent metric unit |
| `_min`           | Smallest value in the observations.                                                 | parent metric unit |
| `_p05`           | 5th percentile of the observations.                                                 | parent metric unit |
| `_p25`           | 25th percentile of the observations.                                                | parent metric unit |
| `_median`        | 50th percentile of the observations.                                                | parent metric unit |
| `_p75`           | 75th percentile of the observations.                                                | parent metric unit |
| `_p90`           | 90th percentile of the observations.                                                | parent metric unit |
| `_p95`           | 95th percentile of the observations.                                                | parent metric unit |
| `_p99`           | 99th percentile of the observations.                                                | parent metric unit |
| `_max`           | Largest value in the observations.                                                  | parent metric unit |

### Important distinctions

- **`distance_distance_per_trip_m`** is the average distance over valid trips; **`average_distance`** is the mean total distance of an agent on an observed agent-day. They are different quantities.
- **`temporal_trip_duration_gap_hours`** measures elapsed time between consecutive check-ins for trip records, **not** independently observed travel time.
- The per-agent cumulative distance uses the prepared `TripDistance` column; the overall trip-distance totals use `Distance` restricted to `IsTrip`. These may differ if preprocessing populates those columns differently.
- **`home_visit_share`** uses an inferred home location, not verified residential information. **Entropy** and **level of exploration** use helpers whose precise definitions must be checked for publication-grade formulas.

## 1. Basic dataset statistics

| Flattened metric           | Definition                                              | Unit / scale |
| -------------------------- | ------------------------------------------------------- | ------------ |
| `basic_n_agents`           | Distinct agents (`AgentID`) in the processed data.      | agents       |
| `basic_n_checkins`         | Total check-in rows in the processed data.              | check-ins    |
| `basic_n_trips`            | Rows labeled as qualifying trips (`IsTrip == True`).    | trips        |
| `basic_n_unique_locations` | Distinct `LocationID` values visited across all agents. | locations    |
| `basic_start_time`         | Earliest recorded `ArrivingTime`.                       | timestamp    |
| `basic_end_time`           | Latest recorded `ArrivingTime`.                         | timestamp    |
| `basic_n_days`             | Number of distinct observed `Date` values.              | dates        |

## 2. Data quality

| Flattened metric                                   | Definition                                                                                                                               | Unit / scale                      |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| `data_quality_distance_outlier_rows`               | Rows marked `DistanceOutlier` after preprocessing.                                                                                       | rows                              |
| `data_quality_zero_or_stationary_transition_share` | Among rows with `HasPrevious == True`, fraction for which `IsTrip == False`; includes stationary or otherwise nonqualifying transitions. | share of prior-linked transitions |
| `data_quality_nonpositive_time_delta_rows`         | Rows whose `TimeDeltaSeconds` is zero or negative; null time gaps do not satisfy this comparison.                                        | rows                              |
| `data_quality_missing_distance_rows`               | Rows whose processed `Distance` is missing (`NaN`).                                                                                      | rows                              |

## 3. Distance

### 3.1 Scalar distance metrics

| Flattened metric                  | Definition                                                                                        | Unit / scale |
| --------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| `distance_total_distance_m`       | Sum of `Distance` for all qualifying trip rows.                                                   | m            |
| `distance_total_distance_km`      | The same qualifying-trip distance sum expressed in kilometers.                                    | km           |
| `distance_distance_per_trip_m`    | Mean `Distance` across qualifying trips (`IsTrip`).                                               | m/trip       |
| `distance_distance_per_checkin_m` | Sum of qualifying-trip distances divided by **all** processed check-in rows (including nontrips). | m/check-in   |

### 3.2. Trip distance

**What is measured:** `Distance` measured on each `IsTrip` row. Each observation is one of the following: qualifying trips.

| Flattened metric                      | Definition                                                                | Unit / scale     |
| ------------------------------------- | ------------------------------------------------------------------------- | ---------------- |
| `distance_per_trip_distance_m_count`  | Number of nonmissing trip distance observations included in this summary. | qualifying trips |
| `distance_per_trip_distance_m_mean`   | Average trip distance across qualifying trips.                            | m                |
| `distance_per_trip_distance_m_std`    | Standard deviation of trip distance across qualifying trips.              | m                |
| `distance_per_trip_distance_m_min`    | Minimum observed value of trip distance.                                  | m                |
| `distance_per_trip_distance_m_p05`    | 5th percentile of trip distance across qualifying trips.                  | m                |
| `distance_per_trip_distance_m_p25`    | 25th percentile of trip distance across qualifying trips.                 | m                |
| `distance_per_trip_distance_m_median` | 50th (median) percentile of trip distance across qualifying trips.        | m                |
| `distance_per_trip_distance_m_p75`    | 75th percentile of trip distance across qualifying trips.                 | m                |
| `distance_per_trip_distance_m_p90`    | 90th percentile of trip distance across qualifying trips.                 | m                |
| `distance_per_trip_distance_m_p95`    | 95th percentile of trip distance across qualifying trips.                 | m                |
| `distance_per_trip_distance_m_p99`    | 99th percentile of trip distance across qualifying trips.                 | m                |
| `distance_per_trip_distance_m_max`    | Maximum observed value of trip distance.                                  | m                |

### 3.3. Cumulative distance per agent

**What is measured:** Sum of prepared `TripDistance` across all rows for each agent. Each observation is one of the following: agents.

| Flattened metric                             | Definition                                                                                        | Unit / scale |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| `distance_per_agent_total_distance_m_count`  | Number of nonmissing an agent's total accumulated distance observations included in this summary. | agents       |
| `distance_per_agent_total_distance_m_mean`   | Average an agent's total accumulated distance across agents.                                      | m            |
| `distance_per_agent_total_distance_m_std`    | Standard deviation of an agent's total accumulated distance across agents.                        | m            |
| `distance_per_agent_total_distance_m_min`    | Minimum observed value of an agent's total accumulated distance.                                  | m            |
| `distance_per_agent_total_distance_m_p05`    | 5th percentile of an agent's total accumulated distance across agents.                            | m            |
| `distance_per_agent_total_distance_m_p25`    | 25th percentile of an agent's total accumulated distance across agents.                           | m            |
| `distance_per_agent_total_distance_m_median` | 50th (median) percentile of an agent's total accumulated distance across agents.                  | m            |
| `distance_per_agent_total_distance_m_p75`    | 75th percentile of an agent's total accumulated distance across agents.                           | m            |
| `distance_per_agent_total_distance_m_p90`    | 90th percentile of an agent's total accumulated distance across agents.                           | m            |
| `distance_per_agent_total_distance_m_p95`    | 95th percentile of an agent's total accumulated distance across agents.                           | m            |
| `distance_per_agent_total_distance_m_p99`    | 99th percentile of an agent's total accumulated distance across agents.                           | m            |
| `distance_per_agent_total_distance_m_max`    | Maximum observed value of an agent's total accumulated distance.                                  | m            |

### 3.4. Daily total distance per agent

**What is measured:** `TotalDistance` from `get_per_day_stat`, one value per observed agent-day. Each observation is one of the following: agent-days.

| Flattened metric                                 | Definition                                                                                | Unit / scale |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------- | ------------ |
| `distance_per_agent_day_total_distance_m_count`  | Number of nonmissing an agent-day's total distance observations included in this summary. | agent-days   |
| `distance_per_agent_day_total_distance_m_mean`   | Average an agent-day's total distance across agent-days.                                  | m            |
| `distance_per_agent_day_total_distance_m_std`    | Standard deviation of an agent-day's total distance across agent-days.                    | m            |
| `distance_per_agent_day_total_distance_m_min`    | Minimum observed value of an agent-day's total distance.                                  | m            |
| `distance_per_agent_day_total_distance_m_p05`    | 5th percentile of an agent-day's total distance across agent-days.                        | m            |
| `distance_per_agent_day_total_distance_m_p25`    | 25th percentile of an agent-day's total distance across agent-days.                       | m            |
| `distance_per_agent_day_total_distance_m_median` | 50th (median) percentile of an agent-day's total distance across agent-days.              | m            |
| `distance_per_agent_day_total_distance_m_p75`    | 75th percentile of an agent-day's total distance across agent-days.                       | m            |
| `distance_per_agent_day_total_distance_m_p90`    | 90th percentile of an agent-day's total distance across agent-days.                       | m            |
| `distance_per_agent_day_total_distance_m_p95`    | 95th percentile of an agent-day's total distance across agent-days.                       | m            |
| `distance_per_agent_day_total_distance_m_p99`    | 99th percentile of an agent-day's total distance across agent-days.                       | m            |
| `distance_per_agent_day_total_distance_m_max`    | Maximum observed value of an agent-day's total distance.                                  | m            |

### 3.5. Total distance across agents by date

**What is measured:** Sum of the agent-day `TotalDistance` values for each calendar date. Each observation is one of the following: dates.

| Flattened metric                         | Definition                                                                                        | Unit / scale |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| `distance_daily_total_distance_m_count`  | Number of nonmissing a date's total distance across agents observations included in this summary. | dates        |
| `distance_daily_total_distance_m_mean`   | Average a date's total distance across agents across dates.                                       | m            |
| `distance_daily_total_distance_m_std`    | Standard deviation of a date's total distance across agents across dates.                         | m            |
| `distance_daily_total_distance_m_min`    | Minimum observed value of a date's total distance across agents.                                  | m            |
| `distance_daily_total_distance_m_p05`    | 5th percentile of a date's total distance across agents across dates.                             | m            |
| `distance_daily_total_distance_m_p25`    | 25th percentile of a date's total distance across agents across dates.                            | m            |
| `distance_daily_total_distance_m_median` | 50th (median) percentile of a date's total distance across agents across dates.                   | m            |
| `distance_daily_total_distance_m_p75`    | 75th percentile of a date's total distance across agents across dates.                            | m            |
| `distance_daily_total_distance_m_p90`    | 90th percentile of a date's total distance across agents across dates.                            | m            |
| `distance_daily_total_distance_m_p95`    | 95th percentile of a date's total distance across agents across dates.                            | m            |
| `distance_daily_total_distance_m_p99`    | 99th percentile of a date's total distance across agents across dates.                            | m            |
| `distance_daily_total_distance_m_max`    | Maximum observed value of a date's total distance across agents.                                  | m            |

## 4. Visitation and activity

### 4.1. Check-ins per agent

**What is measured:** Number of processed rows for each agent. Each observation is one of the following: agents.

| Flattened metric                       | Definition                                                                            | Unit / scale |
| -------------------------------------- | ------------------------------------------------------------------------------------- | ------------ |
| `visitation_checkins_per_agent_count`  | Number of nonmissing an agent's check-in count observations included in this summary. | agents       |
| `visitation_checkins_per_agent_mean`   | Average an agent's check-in count across agents.                                      | check-ins    |
| `visitation_checkins_per_agent_std`    | Standard deviation of an agent's check-in count across agents.                        | check-ins    |
| `visitation_checkins_per_agent_min`    | Minimum observed value of an agent's check-in count.                                  | check-ins    |
| `visitation_checkins_per_agent_p05`    | 5th percentile of an agent's check-in count across agents.                            | check-ins    |
| `visitation_checkins_per_agent_p25`    | 25th percentile of an agent's check-in count across agents.                           | check-ins    |
| `visitation_checkins_per_agent_median` | 50th (median) percentile of an agent's check-in count across agents.                  | check-ins    |
| `visitation_checkins_per_agent_p75`    | 75th percentile of an agent's check-in count across agents.                           | check-ins    |
| `visitation_checkins_per_agent_p90`    | 90th percentile of an agent's check-in count across agents.                           | check-ins    |
| `visitation_checkins_per_agent_p95`    | 95th percentile of an agent's check-in count across agents.                           | check-ins    |
| `visitation_checkins_per_agent_p99`    | 99th percentile of an agent's check-in count across agents.                           | check-ins    |
| `visitation_checkins_per_agent_max`    | Maximum observed value of an agent's check-in count.                                  | check-ins    |

### 4.2. Trips per agent

**What is measured:** Sum of `IsTrip` for each agent. Each observation is one of the following: agents.

| Flattened metric                    | Definition                                                                                   | Unit / scale |
| ----------------------------------- | -------------------------------------------------------------------------------------------- | ------------ |
| `visitation_trips_per_agent_count`  | Number of nonmissing an agent's qualifying-trip count observations included in this summary. | agents       |
| `visitation_trips_per_agent_mean`   | Average an agent's qualifying-trip count across agents.                                      | trips        |
| `visitation_trips_per_agent_std`    | Standard deviation of an agent's qualifying-trip count across agents.                        | trips        |
| `visitation_trips_per_agent_min`    | Minimum observed value of an agent's qualifying-trip count.                                  | trips        |
| `visitation_trips_per_agent_p05`    | 5th percentile of an agent's qualifying-trip count across agents.                            | trips        |
| `visitation_trips_per_agent_p25`    | 25th percentile of an agent's qualifying-trip count across agents.                           | trips        |
| `visitation_trips_per_agent_median` | 50th (median) percentile of an agent's qualifying-trip count across agents.                  | trips        |
| `visitation_trips_per_agent_p75`    | 75th percentile of an agent's qualifying-trip count across agents.                           | trips        |
| `visitation_trips_per_agent_p90`    | 90th percentile of an agent's qualifying-trip count across agents.                           | trips        |
| `visitation_trips_per_agent_p95`    | 95th percentile of an agent's qualifying-trip count across agents.                           | trips        |
| `visitation_trips_per_agent_p99`    | 99th percentile of an agent's qualifying-trip count across agents.                           | trips        |
| `visitation_trips_per_agent_max`    | Maximum observed value of an agent's qualifying-trip count.                                  | trips        |

### 4.3. Active days per agent

**What is measured:** Distinct observed dates with at least one check-in for each agent. Each observation is one of the following: agents.

| Flattened metric                          | Definition                                                                                    | Unit / scale |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- | ------------ |
| `visitation_active_days_per_agent_count`  | Number of nonmissing an agent's number of active dates observations included in this summary. | agents       |
| `visitation_active_days_per_agent_mean`   | Average an agent's number of active dates across agents.                                      | days         |
| `visitation_active_days_per_agent_std`    | Standard deviation of an agent's number of active dates across agents.                        | days         |
| `visitation_active_days_per_agent_min`    | Minimum observed value of an agent's number of active dates.                                  | days         |
| `visitation_active_days_per_agent_p05`    | 5th percentile of an agent's number of active dates across agents.                            | days         |
| `visitation_active_days_per_agent_p25`    | 25th percentile of an agent's number of active dates across agents.                           | days         |
| `visitation_active_days_per_agent_median` | 50th (median) percentile of an agent's number of active dates across agents.                  | days         |
| `visitation_active_days_per_agent_p75`    | 75th percentile of an agent's number of active dates across agents.                           | days         |
| `visitation_active_days_per_agent_p90`    | 90th percentile of an agent's number of active dates across agents.                           | days         |
| `visitation_active_days_per_agent_p95`    | 95th percentile of an agent's number of active dates across agents.                           | days         |
| `visitation_active_days_per_agent_p99`    | 99th percentile of an agent's number of active dates across agents.                           | days         |
| `visitation_active_days_per_agent_max`    | Maximum observed value of an agent's number of active dates.                                  | days         |

### 4.4. Check-ins per agent-day

**What is measured:** `NumberOfCheckins` reported by `get_per_day_stat`. Each observation is one of the following: agent-days.

| Flattened metric                           | Definition                                                                            | Unit / scale |
| ------------------------------------------ | ------------------------------------------------------------------------------------- | ------------ |
| `visitation_checkins_per_agent_day_count`  | Number of nonmissing check-ins on an agent-day observations included in this summary. | agent-days   |
| `visitation_checkins_per_agent_day_mean`   | Average check-ins on an agent-day across agent-days.                                  | check-ins    |
| `visitation_checkins_per_agent_day_std`    | Standard deviation of check-ins on an agent-day across agent-days.                    | check-ins    |
| `visitation_checkins_per_agent_day_min`    | Minimum observed value of check-ins on an agent-day.                                  | check-ins    |
| `visitation_checkins_per_agent_day_p05`    | 5th percentile of check-ins on an agent-day across agent-days.                        | check-ins    |
| `visitation_checkins_per_agent_day_p25`    | 25th percentile of check-ins on an agent-day across agent-days.                       | check-ins    |
| `visitation_checkins_per_agent_day_median` | 50th (median) percentile of check-ins on an agent-day across agent-days.              | check-ins    |
| `visitation_checkins_per_agent_day_p75`    | 75th percentile of check-ins on an agent-day across agent-days.                       | check-ins    |
| `visitation_checkins_per_agent_day_p90`    | 90th percentile of check-ins on an agent-day across agent-days.                       | check-ins    |
| `visitation_checkins_per_agent_day_p95`    | 95th percentile of check-ins on an agent-day across agent-days.                       | check-ins    |
| `visitation_checkins_per_agent_day_p99`    | 99th percentile of check-ins on an agent-day across agent-days.                       | check-ins    |
| `visitation_checkins_per_agent_day_max`    | Maximum observed value of check-ins on an agent-day.                                  | check-ins    |

### 4.5. Trips per agent-day

**What is measured:** `NumberOfTrips` reported by `get_per_day_stat`. Each observation is one of the following: agent-days.

| Flattened metric                        | Definition                                                                                   | Unit / scale |
| --------------------------------------- | -------------------------------------------------------------------------------------------- | ------------ |
| `visitation_trips_per_agent_day_count`  | Number of nonmissing qualifying trips on an agent-day observations included in this summary. | agent-days   |
| `visitation_trips_per_agent_day_mean`   | Average qualifying trips on an agent-day across agent-days.                                  | trips        |
| `visitation_trips_per_agent_day_std`    | Standard deviation of qualifying trips on an agent-day across agent-days.                    | trips        |
| `visitation_trips_per_agent_day_min`    | Minimum observed value of qualifying trips on an agent-day.                                  | trips        |
| `visitation_trips_per_agent_day_p05`    | 5th percentile of qualifying trips on an agent-day across agent-days.                        | trips        |
| `visitation_trips_per_agent_day_p25`    | 25th percentile of qualifying trips on an agent-day across agent-days.                       | trips        |
| `visitation_trips_per_agent_day_median` | 50th (median) percentile of qualifying trips on an agent-day across agent-days.              | trips        |
| `visitation_trips_per_agent_day_p75`    | 75th percentile of qualifying trips on an agent-day across agent-days.                       | trips        |
| `visitation_trips_per_agent_day_p90`    | 90th percentile of qualifying trips on an agent-day across agent-days.                       | trips        |
| `visitation_trips_per_agent_day_p95`    | 95th percentile of qualifying trips on an agent-day across agent-days.                       | trips        |
| `visitation_trips_per_agent_day_p99`    | 99th percentile of qualifying trips on an agent-day across agent-days.                       | trips        |
| `visitation_trips_per_agent_day_max`    | Maximum observed value of qualifying trips on an agent-day.                                  | trips        |

### 4.6. Distinct locations visited per agent-day (Nl)

**What is measured:** `UniqueLocations` reported by `get_per_day_stat`. Each observation is one of the following: agent-days.

| Flattened metric                                              | Definition                                                                                     | Unit / scale |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------ |
| `visitation_number_locations_visited_Nl_per_agent_day_count`  | Number of nonmissing distinct locations on an agent-day observations included in this summary. | agent-days   |
| `visitation_number_locations_visited_Nl_per_agent_day_mean`   | Average distinct locations on an agent-day across agent-days.                                  | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_std`    | Standard deviation of distinct locations on an agent-day across agent-days.                    | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_min`    | Minimum observed value of distinct locations on an agent-day.                                  | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p05`    | 5th percentile of distinct locations on an agent-day across agent-days.                        | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p25`    | 25th percentile of distinct locations on an agent-day across agent-days.                       | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_median` | 50th (median) percentile of distinct locations on an agent-day across agent-days.              | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p75`    | 75th percentile of distinct locations on an agent-day across agent-days.                       | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p90`    | 90th percentile of distinct locations on an agent-day across agent-days.                       | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p95`    | 95th percentile of distinct locations on an agent-day across agent-days.                       | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_p99`    | 99th percentile of distinct locations on an agent-day across agent-days.                       | locations    |
| `visitation_number_locations_visited_Nl_per_agent_day_max`    | Maximum observed value of distinct locations on an agent-day.                                  | locations    |

### 4.7. Distinct locations per agent

**What is measured:** Number of unique `LocationID` values across each agent's observed history. Each observation is one of the following: agents.

| Flattened metric                               | Definition                                                                                         | Unit / scale |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------ |
| `visitation_unique_locations_per_agent_count`  | Number of nonmissing distinct locations visited by an agent observations included in this summary. | agents       |
| `visitation_unique_locations_per_agent_mean`   | Average distinct locations visited by an agent across agents.                                      | locations    |
| `visitation_unique_locations_per_agent_std`    | Standard deviation of distinct locations visited by an agent across agents.                        | locations    |
| `visitation_unique_locations_per_agent_min`    | Minimum observed value of distinct locations visited by an agent.                                  | locations    |
| `visitation_unique_locations_per_agent_p05`    | 5th percentile of distinct locations visited by an agent across agents.                            | locations    |
| `visitation_unique_locations_per_agent_p25`    | 25th percentile of distinct locations visited by an agent across agents.                           | locations    |
| `visitation_unique_locations_per_agent_median` | 50th (median) percentile of distinct locations visited by an agent across agents.                  | locations    |
| `visitation_unique_locations_per_agent_p75`    | 75th percentile of distinct locations visited by an agent across agents.                           | locations    |
| `visitation_unique_locations_per_agent_p90`    | 90th percentile of distinct locations visited by an agent across agents.                           | locations    |
| `visitation_unique_locations_per_agent_p95`    | 95th percentile of distinct locations visited by an agent across agents.                           | locations    |
| `visitation_unique_locations_per_agent_p99`    | 99th percentile of distinct locations visited by an agent across agents.                           | locations    |
| `visitation_unique_locations_per_agent_max`    | Maximum observed value of distinct locations visited by an agent.                                  | locations    |

### 4.8. Home visit share per agent

**What is measured:** An inferred `HomeLocationID` is assigned to each agent; share is the mean of `LocationID == HomeLocationID` over their check-ins. Each observation is one of the following: agents.

| Flattened metric                     | Definition                                                                                                                 | Unit / scale |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ------------ |
| `visitation_home_visit_share_count`  | Number of nonmissing an agent's fraction of check-ins at the inferred home location observations included in this summary. | agents       |
| `visitation_home_visit_share_mean`   | Average an agent's fraction of check-ins at the inferred home location across agents.                                      | share        |
| `visitation_home_visit_share_std`    | Standard deviation of an agent's fraction of check-ins at the inferred home location across agents.                        | share        |
| `visitation_home_visit_share_min`    | Minimum observed value of an agent's fraction of check-ins at the inferred home location.                                  | share        |
| `visitation_home_visit_share_p05`    | 5th percentile of an agent's fraction of check-ins at the inferred home location across agents.                            | share        |
| `visitation_home_visit_share_p25`    | 25th percentile of an agent's fraction of check-ins at the inferred home location across agents.                           | share        |
| `visitation_home_visit_share_median` | 50th (median) percentile of an agent's fraction of check-ins at the inferred home location across agents.                  | share        |
| `visitation_home_visit_share_p75`    | 75th percentile of an agent's fraction of check-ins at the inferred home location across agents.                           | share        |
| `visitation_home_visit_share_p90`    | 90th percentile of an agent's fraction of check-ins at the inferred home location across agents.                           | share        |
| `visitation_home_visit_share_p95`    | 95th percentile of an agent's fraction of check-ins at the inferred home location across agents.                           | share        |
| `visitation_home_visit_share_p99`    | 99th percentile of an agent's fraction of check-ins at the inferred home location across agents.                           | share        |
| `visitation_home_visit_share_max`    | Maximum observed value of an agent's fraction of check-ins at the inferred home location.                                  | share        |

## 5. Spatial exploration

### 5.1. Radius of gyration (Rg)

**What is measured:** Characterizes spatial spread of visited locations about an agent's center. The exact coordinate weighting and distance formula are in `_compute_radius_of_gyration`. Each observation is one of the following: agents.

| Flattened metric                                     | Definition                                                                                | Unit / scale |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------ |
| `spatial_exploration_radius_of_gyration_Rg_m_count`  | Number of nonmissing an agent's radius of gyration observations included in this summary. | agents       |
| `spatial_exploration_radius_of_gyration_Rg_m_mean`   | Average an agent's radius of gyration across agents.                                      | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_std`    | Standard deviation of an agent's radius of gyration across agents.                        | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_min`    | Minimum observed value of an agent's radius of gyration.                                  | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p05`    | 5th percentile of an agent's radius of gyration across agents.                            | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p25`    | 25th percentile of an agent's radius of gyration across agents.                           | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_median` | 50th (median) percentile of an agent's radius of gyration across agents.                  | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p75`    | 75th percentile of an agent's radius of gyration across agents.                           | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p90`    | 90th percentile of an agent's radius of gyration across agents.                           | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p95`    | 95th percentile of an agent's radius of gyration across agents.                           | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_p99`    | 99th percentile of an agent's radius of gyration across agents.                           | m            |
| `spatial_exploration_radius_of_gyration_Rg_m_max`    | Maximum observed value of an agent's radius of gyration.                                  | m            |

### 5.2. Level-of-exploration rank distribution

The result is a probability distribution indexed by location exploration rank, returned by `_level_of_exploration_distribution(df, max_rank=10)`. Ranks 1 through 10 are separate categories; `>10` aggregates higher ranks. The exact ranking/weighting convention is defined in the helper, which was not supplied.

| Flattened metric                                                    | Definition                                                                | Unit / scale |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------ |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_1`   | Share of exploration-rank distribution assigned to rank 1.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_2`   | Share of exploration-rank distribution assigned to rank 2.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_3`   | Share of exploration-rank distribution assigned to rank 3.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_4`   | Share of exploration-rank distribution assigned to rank 4.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_5`   | Share of exploration-rank distribution assigned to rank 5.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_6`   | Share of exploration-rank distribution assigned to rank 6.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_7`   | Share of exploration-rank distribution assigned to rank 7.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_8`   | Share of exploration-rank distribution assigned to rank 8.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_9`   | Share of exploration-rank distribution assigned to rank 9.                | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_10`  | Share of exploration-rank distribution assigned to rank 10.               | share        |
| `spatial_exploration_level_of_exploration_Le_rank_distribution_>10` | Share of exploration-rank distribution assigned to ranks greater than 10. | share        |

### 5.3. Location entropy per agent

**What is measured:** Uncertainty/diversity of the agent's location visit frequencies, computed by `_level_of_exploration_distribution`. Logarithm base is not shown. Each observation is one of the following: agents.

| Flattened metric                                        | Definition                                                                                    | Unit / scale  |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------- |
| `spatial_exploration_location_entropy_per_agent_count`  | Number of nonmissing an agent's location-visit entropy observations included in this summary. | agents        |
| `spatial_exploration_location_entropy_per_agent_mean`   | Average an agent's location-visit entropy across agents.                                      | entropy units |
| `spatial_exploration_location_entropy_per_agent_std`    | Standard deviation of an agent's location-visit entropy across agents.                        | entropy units |
| `spatial_exploration_location_entropy_per_agent_min`    | Minimum observed value of an agent's location-visit entropy.                                  | entropy units |
| `spatial_exploration_location_entropy_per_agent_p05`    | 5th percentile of an agent's location-visit entropy across agents.                            | entropy units |
| `spatial_exploration_location_entropy_per_agent_p25`    | 25th percentile of an agent's location-visit entropy across agents.                           | entropy units |
| `spatial_exploration_location_entropy_per_agent_median` | 50th (median) percentile of an agent's location-visit entropy across agents.                  | entropy units |
| `spatial_exploration_location_entropy_per_agent_p75`    | 75th percentile of an agent's location-visit entropy across agents.                           | entropy units |
| `spatial_exploration_location_entropy_per_agent_p90`    | 90th percentile of an agent's location-visit entropy across agents.                           | entropy units |
| `spatial_exploration_location_entropy_per_agent_p95`    | 95th percentile of an agent's location-visit entropy across agents.                           | entropy units |
| `spatial_exploration_location_entropy_per_agent_p99`    | 99th percentile of an agent's location-visit entropy across agents.                           | entropy units |
| `spatial_exploration_location_entropy_per_agent_max`    | Maximum observed value of an agent's location-visit entropy.                                  | entropy units |

### 5.4. Normalized location entropy per agent

**What is measured:** Scale-adjusted version of per-agent location entropy, computed by the helper; exact normalization not shown. Each observation is one of the following: agents.

| Flattened metric                                                   | Definition                                                                                               | Unit / scale     |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------- |
| `spatial_exploration_normalized_location_entropy_per_agent_count`  | Number of nonmissing an agent's normalized location-visit entropy observations included in this summary. | agents           |
| `spatial_exploration_normalized_location_entropy_per_agent_mean`   | Average an agent's normalized location-visit entropy across agents.                                      | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_std`    | Standard deviation of an agent's normalized location-visit entropy across agents.                        | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_min`    | Minimum observed value of an agent's normalized location-visit entropy.                                  | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p05`    | 5th percentile of an agent's normalized location-visit entropy across agents.                            | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p25`    | 25th percentile of an agent's normalized location-visit entropy across agents.                           | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_median` | 50th (median) percentile of an agent's normalized location-visit entropy across agents.                  | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p75`    | 75th percentile of an agent's normalized location-visit entropy across agents.                           | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p90`    | 90th percentile of an agent's normalized location-visit entropy across agents.                           | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p95`    | 95th percentile of an agent's normalized location-visit entropy across agents.                           | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_p99`    | 99th percentile of an agent's normalized location-visit entropy across agents.                           | normalized score |
| `spatial_exploration_normalized_location_entropy_per_agent_max`    | Maximum observed value of an agent's normalized location-visit entropy.                                  | normalized score |

### 5.5. Top-1 location share per agent

**What is measured:** Check-in concentration at the single most-visited location. Each observation is one of the following: agents.

| Flattened metric                                           | Definition                                                                                                               | Unit / scale |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------ |
| `spatial_exploration_top1_location_share_per_agent_count`  | Number of nonmissing an agent's fraction of visits to their most-visited location observations included in this summary. | agents       |
| `spatial_exploration_top1_location_share_per_agent_mean`   | Average an agent's fraction of visits to their most-visited location across agents.                                      | share        |
| `spatial_exploration_top1_location_share_per_agent_std`    | Standard deviation of an agent's fraction of visits to their most-visited location across agents.                        | share        |
| `spatial_exploration_top1_location_share_per_agent_min`    | Minimum observed value of an agent's fraction of visits to their most-visited location.                                  | share        |
| `spatial_exploration_top1_location_share_per_agent_p05`    | 5th percentile of an agent's fraction of visits to their most-visited location across agents.                            | share        |
| `spatial_exploration_top1_location_share_per_agent_p25`    | 25th percentile of an agent's fraction of visits to their most-visited location across agents.                           | share        |
| `spatial_exploration_top1_location_share_per_agent_median` | 50th (median) percentile of an agent's fraction of visits to their most-visited location across agents.                  | share        |
| `spatial_exploration_top1_location_share_per_agent_p75`    | 75th percentile of an agent's fraction of visits to their most-visited location across agents.                           | share        |
| `spatial_exploration_top1_location_share_per_agent_p90`    | 90th percentile of an agent's fraction of visits to their most-visited location across agents.                           | share        |
| `spatial_exploration_top1_location_share_per_agent_p95`    | 95th percentile of an agent's fraction of visits to their most-visited location across agents.                           | share        |
| `spatial_exploration_top1_location_share_per_agent_p99`    | 99th percentile of an agent's fraction of visits to their most-visited location across agents.                           | share        |
| `spatial_exploration_top1_location_share_per_agent_max`    | Maximum observed value of an agent's fraction of visits to their most-visited location.                                  | share        |

### 5.6. Top-3 location share per agent

**What is measured:** Combined check-in concentration across the three most-visited locations (or available locations). Each observation is one of the following: agents.

| Flattened metric                                           | Definition                                                                                                                      | Unit / scale |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| `spatial_exploration_top3_location_share_per_agent_count`  | Number of nonmissing an agent's fraction of visits to their three most-visited locations observations included in this summary. | agents       |
| `spatial_exploration_top3_location_share_per_agent_mean`   | Average an agent's fraction of visits to their three most-visited locations across agents.                                      | share        |
| `spatial_exploration_top3_location_share_per_agent_std`    | Standard deviation of an agent's fraction of visits to their three most-visited locations across agents.                        | share        |
| `spatial_exploration_top3_location_share_per_agent_min`    | Minimum observed value of an agent's fraction of visits to their three most-visited locations.                                  | share        |
| `spatial_exploration_top3_location_share_per_agent_p05`    | 5th percentile of an agent's fraction of visits to their three most-visited locations across agents.                            | share        |
| `spatial_exploration_top3_location_share_per_agent_p25`    | 25th percentile of an agent's fraction of visits to their three most-visited locations across agents.                           | share        |
| `spatial_exploration_top3_location_share_per_agent_median` | 50th (median) percentile of an agent's fraction of visits to their three most-visited locations across agents.                  | share        |
| `spatial_exploration_top3_location_share_per_agent_p75`    | 75th percentile of an agent's fraction of visits to their three most-visited locations across agents.                           | share        |
| `spatial_exploration_top3_location_share_per_agent_p90`    | 90th percentile of an agent's fraction of visits to their three most-visited locations across agents.                           | share        |
| `spatial_exploration_top3_location_share_per_agent_p95`    | 95th percentile of an agent's fraction of visits to their three most-visited locations across agents.                           | share        |
| `spatial_exploration_top3_location_share_per_agent_p99`    | 99th percentile of an agent's fraction of visits to their three most-visited locations across agents.                           | share        |
| `spatial_exploration_top3_location_share_per_agent_max`    | Maximum observed value of an agent's fraction of visits to their three most-visited locations.                                  | share        |

## 6. Temporal patterns

### 6.1. Inter-check-in time gap

**What is measured:** `TimeDeltaSeconds / 3600` for rows with `HasPrevious == True`. Each observation is one of the following: prior-linked check-ins.

| Flattened metric                          | Definition                                                                                                 | Unit / scale           |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------- |
| `temporal_inter_checkin_gap_hours_count`  | Number of nonmissing the elapsed time between consecutive check-ins observations included in this summary. | prior-linked check-ins |
| `temporal_inter_checkin_gap_hours_mean`   | Average the elapsed time between consecutive check-ins across prior-linked check-ins.                      | hours                  |
| `temporal_inter_checkin_gap_hours_std`    | Standard deviation of the elapsed time between consecutive check-ins across prior-linked check-ins.        | hours                  |
| `temporal_inter_checkin_gap_hours_min`    | Minimum observed value of the elapsed time between consecutive check-ins.                                  | hours                  |
| `temporal_inter_checkin_gap_hours_p05`    | 5th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.            | hours                  |
| `temporal_inter_checkin_gap_hours_p25`    | 25th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.           | hours                  |
| `temporal_inter_checkin_gap_hours_median` | 50th (median) percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.  | hours                  |
| `temporal_inter_checkin_gap_hours_p75`    | 75th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.           | hours                  |
| `temporal_inter_checkin_gap_hours_p90`    | 90th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.           | hours                  |
| `temporal_inter_checkin_gap_hours_p95`    | 95th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.           | hours                  |
| `temporal_inter_checkin_gap_hours_p99`    | 99th percentile of the elapsed time between consecutive check-ins across prior-linked check-ins.           | hours                  |
| `temporal_inter_checkin_gap_hours_max`    | Maximum observed value of the elapsed time between consecutive check-ins.                                  | hours                  |

### 6.2. Trip-associated check-in time gap

**What is measured:** `TimeDeltaSeconds / 3600` for rows with `IsTrip == True`; not a measured in-transit duration. Each observation is one of the following: qualifying trips.

| Flattened metric                          | Definition                                                                                            | Unit / scale     |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------- |
| `temporal_trip_duration_gap_hours_count`  | Number of nonmissing the time gap for a qualifying trip record observations included in this summary. | qualifying trips |
| `temporal_trip_duration_gap_hours_mean`   | Average the time gap for a qualifying trip record across qualifying trips.                            | hours            |
| `temporal_trip_duration_gap_hours_std`    | Standard deviation of the time gap for a qualifying trip record across qualifying trips.              | hours            |
| `temporal_trip_duration_gap_hours_min`    | Minimum observed value of the time gap for a qualifying trip record.                                  | hours            |
| `temporal_trip_duration_gap_hours_p05`    | 5th percentile of the time gap for a qualifying trip record across qualifying trips.                  | hours            |
| `temporal_trip_duration_gap_hours_p25`    | 25th percentile of the time gap for a qualifying trip record across qualifying trips.                 | hours            |
| `temporal_trip_duration_gap_hours_median` | 50th (median) percentile of the time gap for a qualifying trip record across qualifying trips.        | hours            |
| `temporal_trip_duration_gap_hours_p75`    | 75th percentile of the time gap for a qualifying trip record across qualifying trips.                 | hours            |
| `temporal_trip_duration_gap_hours_p90`    | 90th percentile of the time gap for a qualifying trip record across qualifying trips.                 | hours            |
| `temporal_trip_duration_gap_hours_p95`    | 95th percentile of the time gap for a qualifying trip record across qualifying trips.                 | hours            |
| `temporal_trip_duration_gap_hours_p99`    | 99th percentile of the time gap for a qualifying trip record across qualifying trips.                 | hours            |
| `temporal_trip_duration_gap_hours_max`    | Maximum observed value of the time gap for a qualifying trip record.                                  | hours            |

### 6.3. Speed on qualifying trips

**What is measured:** `SpeedMps` for qualifying trip rows; construction and interpretation depend on preprocessing. Each observation is one of the following: qualifying trips.

| Flattened metric            | Definition                                                                                                   | Unit / scale     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------- |
| `temporal_speed_mps_count`  | Number of nonmissing the computed speed assigned to a qualifying trip observations included in this summary. | qualifying trips |
| `temporal_speed_mps_mean`   | Average the computed speed assigned to a qualifying trip across qualifying trips.                            | m/s              |
| `temporal_speed_mps_std`    | Standard deviation of the computed speed assigned to a qualifying trip across qualifying trips.              | m/s              |
| `temporal_speed_mps_min`    | Minimum observed value of the computed speed assigned to a qualifying trip.                                  | m/s              |
| `temporal_speed_mps_p05`    | 5th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                  | m/s              |
| `temporal_speed_mps_p25`    | 25th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                 | m/s              |
| `temporal_speed_mps_median` | 50th (median) percentile of the computed speed assigned to a qualifying trip across qualifying trips.        | m/s              |
| `temporal_speed_mps_p75`    | 75th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                 | m/s              |
| `temporal_speed_mps_p90`    | 90th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                 | m/s              |
| `temporal_speed_mps_p95`    | 95th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                 | m/s              |
| `temporal_speed_mps_p99`    | 99th percentile of the computed speed assigned to a qualifying trip across qualifying trips.                 | m/s              |
| `temporal_speed_mps_max`    | Maximum observed value of the computed speed assigned to a qualifying trip.                                  | m/s              |

### 6.4. Active time span per agent-day

**What is measured:** `ActiveSpanHours` from `get_per_day_stat`; generally covers the first-to-last observed check-in within a date, subject to the helper's implementation. Each observation is one of the following: agent-days.

| Flattened metric                                  | Definition                                                                                        | Unit / scale |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| `temporal_active_span_hours_per_agent_day_count`  | Number of nonmissing the observed within-day activity span observations included in this summary. | agent-days   |
| `temporal_active_span_hours_per_agent_day_mean`   | Average the observed within-day activity span across agent-days.                                  | hours        |
| `temporal_active_span_hours_per_agent_day_std`    | Standard deviation of the observed within-day activity span across agent-days.                    | hours        |
| `temporal_active_span_hours_per_agent_day_min`    | Minimum observed value of the observed within-day activity span.                                  | hours        |
| `temporal_active_span_hours_per_agent_day_p05`    | 5th percentile of the observed within-day activity span across agent-days.                        | hours        |
| `temporal_active_span_hours_per_agent_day_p25`    | 25th percentile of the observed within-day activity span across agent-days.                       | hours        |
| `temporal_active_span_hours_per_agent_day_median` | 50th (median) percentile of the observed within-day activity span across agent-days.              | hours        |
| `temporal_active_span_hours_per_agent_day_p75`    | 75th percentile of the observed within-day activity span across agent-days.                       | hours        |
| `temporal_active_span_hours_per_agent_day_p90`    | 90th percentile of the observed within-day activity span across agent-days.                       | hours        |
| `temporal_active_span_hours_per_agent_day_p95`    | 95th percentile of the observed within-day activity span across agent-days.                       | hours        |
| `temporal_active_span_hours_per_agent_day_p99`    | 99th percentile of the observed within-day activity span across agent-days.                       | hours        |
| `temporal_active_span_hours_per_agent_day_max`    | Maximum observed value of the observed within-day activity span.                                  | hours        |

### 6.5. Active agents per date

**What is measured:** Distinct `AgentID` values per date, calculated from `per_day`. Each observation is one of the following: dates.

| Flattened metric                      | Definition                                                                                                           | Unit / scale |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------ |
| `temporal_daily_active_agents_count`  | Number of nonmissing the number of agents with an observed check-in on a date observations included in this summary. | dates        |
| `temporal_daily_active_agents_mean`   | Average the number of agents with an observed check-in on a date across dates.                                       | agents       |
| `temporal_daily_active_agents_std`    | Standard deviation of the number of agents with an observed check-in on a date across dates.                         | agents       |
| `temporal_daily_active_agents_min`    | Minimum observed value of the number of agents with an observed check-in on a date.                                  | agents       |
| `temporal_daily_active_agents_p05`    | 5th percentile of the number of agents with an observed check-in on a date across dates.                             | agents       |
| `temporal_daily_active_agents_p25`    | 25th percentile of the number of agents with an observed check-in on a date across dates.                            | agents       |
| `temporal_daily_active_agents_median` | 50th (median) percentile of the number of agents with an observed check-in on a date across dates.                   | agents       |
| `temporal_daily_active_agents_p75`    | 75th percentile of the number of agents with an observed check-in on a date across dates.                            | agents       |
| `temporal_daily_active_agents_p90`    | 90th percentile of the number of agents with an observed check-in on a date across dates.                            | agents       |
| `temporal_daily_active_agents_p95`    | 95th percentile of the number of agents with an observed check-in on a date across dates.                            | agents       |
| `temporal_daily_active_agents_p99`    | 99th percentile of the number of agents with an observed check-in on a date across dates.                            | agents       |
| `temporal_daily_active_agents_max`    | Maximum observed value of the number of agents with an observed check-in on a date.                                  | agents       |

### 6.6. Temporal shares

| Flattened metric                      | Definition                                                                       | Unit / scale           |
| ------------------------------------- | -------------------------------------------------------------------------------- | ---------------------- |
| `temporal_weekend_checkin_share`      | Fraction of check-in rows marked `IsWeekend == True`.                            | share of all check-ins |
| `temporal_night_checkin_share_0_to_6` | Fraction of check-ins with hour < 6, i.e., 00:00 through 05:59, excluding 06:00. | share of all check-ins |

### 6.7. Check-in distribution by hour

Each metric is the proportion of **all** check-ins falling within the listed hour, using the processed `Hour` field. Keys for unobserved hours are absent from the raw returned dictionary, although they may appear in a downstream padded flattened list.

| Flattened metric                          | Definition                                                        | Unit / scale           |
| ----------------------------------------- | ----------------------------------------------------------------- | ---------------------- |
| `temporal_hourly_checkin_distribution_0`  | Share of check-ins timestamped between 00:00 and 00:59 (hour 0).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_1`  | Share of check-ins timestamped between 01:00 and 01:59 (hour 1).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_2`  | Share of check-ins timestamped between 02:00 and 02:59 (hour 2).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_3`  | Share of check-ins timestamped between 03:00 and 03:59 (hour 3).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_4`  | Share of check-ins timestamped between 04:00 and 04:59 (hour 4).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_5`  | Share of check-ins timestamped between 05:00 and 05:59 (hour 5).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_6`  | Share of check-ins timestamped between 06:00 and 06:59 (hour 6).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_7`  | Share of check-ins timestamped between 07:00 and 07:59 (hour 7).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_8`  | Share of check-ins timestamped between 08:00 and 08:59 (hour 8).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_9`  | Share of check-ins timestamped between 09:00 and 09:59 (hour 9).  | share of all check-ins |
| `temporal_hourly_checkin_distribution_10` | Share of check-ins timestamped between 10:00 and 10:59 (hour 10). | share of all check-ins |
| `temporal_hourly_checkin_distribution_11` | Share of check-ins timestamped between 11:00 and 11:59 (hour 11). | share of all check-ins |
| `temporal_hourly_checkin_distribution_12` | Share of check-ins timestamped between 12:00 and 12:59 (hour 12). | share of all check-ins |
| `temporal_hourly_checkin_distribution_13` | Share of check-ins timestamped between 13:00 and 13:59 (hour 13). | share of all check-ins |
| `temporal_hourly_checkin_distribution_14` | Share of check-ins timestamped between 14:00 and 14:59 (hour 14). | share of all check-ins |
| `temporal_hourly_checkin_distribution_15` | Share of check-ins timestamped between 15:00 and 15:59 (hour 15). | share of all check-ins |
| `temporal_hourly_checkin_distribution_16` | Share of check-ins timestamped between 16:00 and 16:59 (hour 16). | share of all check-ins |
| `temporal_hourly_checkin_distribution_17` | Share of check-ins timestamped between 17:00 and 17:59 (hour 17). | share of all check-ins |
| `temporal_hourly_checkin_distribution_18` | Share of check-ins timestamped between 18:00 and 18:59 (hour 18). | share of all check-ins |
| `temporal_hourly_checkin_distribution_19` | Share of check-ins timestamped between 19:00 and 19:59 (hour 19). | share of all check-ins |
| `temporal_hourly_checkin_distribution_20` | Share of check-ins timestamped between 20:00 and 20:59 (hour 20). | share of all check-ins |
| `temporal_hourly_checkin_distribution_21` | Share of check-ins timestamped between 21:00 and 21:59 (hour 21). | share of all check-ins |
| `temporal_hourly_checkin_distribution_22` | Share of check-ins timestamped between 22:00 and 22:59 (hour 22). | share of all check-ins |
| `temporal_hourly_checkin_distribution_23` | Share of check-ins timestamped between 23:00 and 23:59 (hour 23). | share of all check-ins |

### 6.8. Check-in distribution by weekday

Assumes the usual pandas weekday indexing: Monday = 0, ..., Sunday = 6, consistent with `DayOfWeek` used in the function.

| Flattened metric                            | Definition                                                     | Unit / scale           |
| ------------------------------------------- | -------------------------------------------------------------- | ---------------------- |
| `temporal_dayofweek_checkin_distribution_0` | Share of all check-ins falling on Monday (`DayOfWeek` = 0).    | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_1` | Share of all check-ins falling on Tuesday (`DayOfWeek` = 1).   | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_2` | Share of all check-ins falling on Wednesday (`DayOfWeek` = 2). | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_3` | Share of all check-ins falling on Thursday (`DayOfWeek` = 3).  | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_4` | Share of all check-ins falling on Friday (`DayOfWeek` = 4).    | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_5` | Share of all check-ins falling on Saturday (`DayOfWeek` = 5).  | share of all check-ins |
| `temporal_dayofweek_checkin_distribution_6` | Share of all check-ins falling on Sunday (`DayOfWeek` = 6).    | share of all check-ins |

## 7. Location transitions

A transition is counted here only when a previous check-in is available **and** the current `LocationID` differs from `PrevLocationID`. Origin-to-destination (OD) pairs are ordered: A → B and B → A are separate pairs.

| Flattened metric                      | Definition                                                                                                                                                                                    | Unit / scale                         |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `transitions_n_unique_od_pairs`       | Number of distinct ordered `(PrevLocationID, LocationID)` pairs among observed location changes.                                                                                              | OD pairs                             |
| `transitions_od_transition_entropy`   | Entropy of the frequency distribution over ordered OD transition pairs; exact logarithm base is defined in `_entropy_from_counts`.                                                            | entropy units                        |
| `transitions_top_od_transition_share` | Count of the most common ordered OD pair divided by the number of all location-change transitions.                                                                                            | share of location-change transitions |
| `transitions_top_od_transitions`      | Most frequent ordered origin/destination pairs, each with `PrevLocationID`, `LocationID`, and occurrence `count`; up to `top_n` records. In the example, this list is serialized as a string. | records / serialized list            |

## 8. Histogram and discrete distributions

These are **normalized frequencies**: a bucket value is the proportion of the relevant population falling into the bucket. An interval `[a,b)` includes `a` and excludes `b`; `[a,b]` includes both ends. Units refer to the underlying bucket dimension, while the stored value itself is a share.

### 8.1. Distinct locations visited per agent-day

Denominator: observed agent-days. The bucket `n` corresponds to `UniqueLocations == n`, as produced by `_integer_distribution(..., max_value=20)`. The supplied flattened key list has values 1–12 and 14, while this specific output contains only 1–8.

| Flattened metric                                          | Definition                                                                    | Unit / scale        |
| --------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------- |
| `distributions_number_locations_visited_per_agent_day_1`  | Proportion of agent-days on which exactly 1 distinct location was visited.    | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_2`  | Proportion of agent-days on which exactly 2 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_3`  | Proportion of agent-days on which exactly 3 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_4`  | Proportion of agent-days on which exactly 4 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_5`  | Proportion of agent-days on which exactly 5 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_6`  | Proportion of agent-days on which exactly 6 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_7`  | Proportion of agent-days on which exactly 7 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_8`  | Proportion of agent-days on which exactly 8 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_9`  | Proportion of agent-days on which exactly 9 distinct locations were visited.  | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_10` | Proportion of agent-days on which exactly 10 distinct locations were visited. | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_11` | Proportion of agent-days on which exactly 11 distinct locations were visited. | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_12` | Proportion of agent-days on which exactly 12 distinct locations were visited. | share of agent-days |
| `distributions_number_locations_visited_per_agent_day_14` | Proportion of agent-days on which exactly 14 distinct locations were visited. | share of agent-days |

### 8.2. Exploration-rank distribution (duplicate representation)

This repeats the **same exploration-rank distribution** that appears under `spatial_exploration_level_of_exploration_Le_rank_distribution_*`. The values should match for each corresponding rank in one returned result.

| Flattened metric                              | Definition                                                         | Unit / scale |
| --------------------------------------------- | ------------------------------------------------------------------ | ------------ |
| `distributions_level_of_exploration_rank_1`   | Share of exploration-rank distribution assigned to rank 1.         | share        |
| `distributions_level_of_exploration_rank_2`   | Share of exploration-rank distribution assigned to rank 2.         | share        |
| `distributions_level_of_exploration_rank_3`   | Share of exploration-rank distribution assigned to rank 3.         | share        |
| `distributions_level_of_exploration_rank_4`   | Share of exploration-rank distribution assigned to rank 4.         | share        |
| `distributions_level_of_exploration_rank_5`   | Share of exploration-rank distribution assigned to rank 5.         | share        |
| `distributions_level_of_exploration_rank_6`   | Share of exploration-rank distribution assigned to rank 6.         | share        |
| `distributions_level_of_exploration_rank_7`   | Share of exploration-rank distribution assigned to rank 7.         | share        |
| `distributions_level_of_exploration_rank_8`   | Share of exploration-rank distribution assigned to rank 8.         | share        |
| `distributions_level_of_exploration_rank_9`   | Share of exploration-rank distribution assigned to rank 9.         | share        |
| `distributions_level_of_exploration_rank_10`  | Share of exploration-rank distribution assigned to rank 10.        | share        |
| `distributions_level_of_exploration_rank_>10` | Share of exploration-rank distribution assigned to ranks above 10. | share        |

### 8.3. Trip distance

Denominator: qualifying trips. The bucket indicates trip distances measured in kilometers.

| Flattened metric                            | Definition                                               | Unit / scale              |
| ------------------------------------------- | -------------------------------------------------------- | ------------------------- |
| `distributions_trip_distance_km_[0,0.05)`   | Share of qualifying trips with 0 ≤ distance < 0.05 km.   | share of qualifying trips |
| `distributions_trip_distance_km_[0.05,0.1)` | Share of qualifying trips with 0.05 ≤ distance < 0.1 km. | share of qualifying trips |
| `distributions_trip_distance_km_[0.1,0.25)` | Share of qualifying trips with 0.1 ≤ distance < 0.25 km. | share of qualifying trips |
| `distributions_trip_distance_km_[0.25,0.5)` | Share of qualifying trips with 0.25 ≤ distance < 0.5 km. | share of qualifying trips |
| `distributions_trip_distance_km_[0.5,1)`    | Share of qualifying trips with 0.5 ≤ distance < 1 km.    | share of qualifying trips |
| `distributions_trip_distance_km_[1,2)`      | Share of qualifying trips with 1 ≤ distance < 2 km.      | share of qualifying trips |
| `distributions_trip_distance_km_[2,5)`      | Share of qualifying trips with 2 ≤ distance < 5 km.      | share of qualifying trips |
| `distributions_trip_distance_km_[5,10)`     | Share of qualifying trips with 5 ≤ distance < 10 km.     | share of qualifying trips |
| `distributions_trip_distance_km_[10,20)`    | Share of qualifying trips with 10 ≤ distance < 20 km.    | share of qualifying trips |
| `distributions_trip_distance_km_[20,50)`    | Share of qualifying trips with 20 ≤ distance < 50 km.    | share of qualifying trips |
| `distributions_trip_distance_km_[50,100]`   | Share of qualifying trips with 50 ≤ distance ≤ 100 km.   | share of qualifying trips |

### 8.4. Total daily distance per agent

Denominator: agent-days. The bucket indicates total distance on an agent-day measured in kilometers.

| Flattened metric                                      | Definition                                        | Unit / scale        |
| ----------------------------------------------------- | ------------------------------------------------- | ------------------- |
| `distributions_daily_distance_per_agent_km_[0,0.5)`   | Share of agent-days with 0 ≤ distance < 0.5 km.   | share of agent-days |
| `distributions_daily_distance_per_agent_km_[0.5,1)`   | Share of agent-days with 0.5 ≤ distance < 1 km.   | share of agent-days |
| `distributions_daily_distance_per_agent_km_[1,2)`     | Share of agent-days with 1 ≤ distance < 2 km.     | share of agent-days |
| `distributions_daily_distance_per_agent_km_[2,5)`     | Share of agent-days with 2 ≤ distance < 5 km.     | share of agent-days |
| `distributions_daily_distance_per_agent_km_[5,10)`    | Share of agent-days with 5 ≤ distance < 10 km.    | share of agent-days |
| `distributions_daily_distance_per_agent_km_[10,20)`   | Share of agent-days with 10 ≤ distance < 20 km.   | share of agent-days |
| `distributions_daily_distance_per_agent_km_[20,50)`   | Share of agent-days with 20 ≤ distance < 50 km.   | share of agent-days |
| `distributions_daily_distance_per_agent_km_[50,100)`  | Share of agent-days with 50 ≤ distance < 100 km.  | share of agent-days |
| `distributions_daily_distance_per_agent_km_[100,200]` | Share of agent-days with 100 ≤ distance ≤ 200 km. | share of agent-days |

### 8.5. Radius of gyration

Denominator: agents with computed radius of gyration. The bucket indicates per-agent radius of gyration measured in kilometers.

| Flattened metric                                | Definition                                                                               | Unit / scale                                     |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `distributions_radius_of_gyration_km_[0,0.5)`   | Share of agents with computed radius of gyration with 0 ≤ radius of gyration < 0.5 km.   | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[0.5,1)`   | Share of agents with computed radius of gyration with 0.5 ≤ radius of gyration < 1 km.   | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[1,2)`     | Share of agents with computed radius of gyration with 1 ≤ radius of gyration < 2 km.     | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[2,5)`     | Share of agents with computed radius of gyration with 2 ≤ radius of gyration < 5 km.     | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[5,10)`    | Share of agents with computed radius of gyration with 5 ≤ radius of gyration < 10 km.    | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[10,20)`   | Share of agents with computed radius of gyration with 10 ≤ radius of gyration < 20 km.   | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[20,50)`   | Share of agents with computed radius of gyration with 20 ≤ radius of gyration < 50 km.   | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[50,100)`  | Share of agents with computed radius of gyration with 50 ≤ radius of gyration < 100 km.  | share of agents with computed radius of gyration |
| `distributions_radius_of_gyration_km_[100,200]` | Share of agents with computed radius of gyration with 100 ≤ radius of gyration ≤ 200 km. | share of agents with computed radius of gyration |

## 9. Backward-compatible top-level aliases

These are four convenience keys added at the end of the function. They are not four new statistical definitions.

| Flattened metric    | Definition                                                                                                         | Unit / scale |
| ------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------ |
| `distance_per_trip` | Alias of `distance_distance_per_trip_m` and `distance_per_trip_distance_m_mean`: average qualifying-trip distance. | m            |
| `average_distance`  | Alias of `distance_per_agent_day_total_distance_m_mean`: average total distance per observed agent-day.            | m/agent-day  |
| `max_distance`      | Alias of `distance_per_trip_distance_m_max`: longest qualifying trip distance.                                     | m            |
| `median_distance`   | Alias of `distance_per_agent_day_total_distance_m_median`: median total distance per observed agent-day.           | m/agent-day  |
