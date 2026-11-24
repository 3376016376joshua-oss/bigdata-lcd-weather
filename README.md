# bigdata-lcd-weather

**Hourly Weather Analysis of Ten U.S. Cities: A Hive and Spark Study of NOAA Local
Climatological Data, 2010-2025.**
NYU Big Data, Section C, Fall 2026 final project - Weijun Li (wl3564), Yichong Wu (yw9614),
Le Zheng (lz3516).

The project analyses the hourly reports of NOAA Local Climatological Data (LCD) Version 2 for
the ten cities of FiveThirtyEight's "US Weather History" over 16 years. The pipeline is
ingestion -> HDFS -> Hive -> Spark -> visualization, and everything runs on the NYU Dataproc
cluster.

## Data

| City | Code | LCD station | Years used |
| --- | --- | --- | --- |
| Charlotte | KCLT | USW00013881 | 2010-2025 |
| Los Angeles (Downtown/USC) | KCQT | USW00093134 | 2010-2023 |
| Los Angeles (Intl Airport) | KCQT | USW00023174 | 2024-2025 |
| Houston | KHOU | USW00012918 | 2010-2025 |
| Indianapolis | KIND | USW00093819 | 2010-2025 |
| Jacksonville | KJAX | USW00013889 | 2010-2025 |
| Chicago | KMDW | USW00014819 | 2010-2025 |
| New York | KNYC | USW00094728 | 2010-2025 |
| Philadelphia | KPHL | USW00013739 | 2010-2025 |
| Phoenix | KPHX | USW00023183 | 2010-2025 |
| Seattle | KSEA | USW00024233 | 2010-2025 |

- **LCD v2**: one CSV per station and year at
  `https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access/<year>/LCD_<station>_<year>.csv`.
  Each file has the same 125 columns, all quoted text, in metric units (degC, mm, hPa, m/s,
  km). `REPORT_TYPE` tells the rows apart: `FM-15` routine hourly, `FM-16` special, `FM-12`
  synoptic, `SOD` daily summary, `SOM` monthly summary.
- **Los Angeles**: the Downtown/USC files are incomplete in 2024-2025, so the airport station
  stands for the city in those years. `config/stations.csv` holds the station list;
  `start_year` and `end_year` are the years a station is its city's source. The USC files
  of 2024-2025 are still downloaded, so the raw zone holds all 160 files of the ten stations
  plus the two airport files.
- **FiveThirtyEight validation set**: ten CSVs (July 2014 to June 2015) from
  <https://github.com/fivethirtyeight/data/tree/master/us-weather-history>.

## Research questions

1. Which cities deviated most from normal temperatures, in which months and years, and how
   unusual was 2014-15 (warm West, cold East) within 2010-2025?
2. How many extreme days (daily mean at least 10 degF above or below normal) did each city
   have each year, and in which seasons?
3. Do warm extremes outnumber cold extremes, and did the balance change over 2010-2025?
4. What are the seasonal and hour-by-hour temperature cycles of each city, and how do the ten
   cities cluster by climate?
5. Which cities and months were wetter or drier than normal, and what were the longest dry
   spells and heaviest rain events (for example the California drought of 2012-2016)?
6. How do day-to-day temperature volatility, daily temperature range and humidity differ by
   city, and how do special weather reports cluster around storms?
7. Regression: predict the next day's maximum temperature from the calendar, the departure
   from normal and the previous 24 hours of hourly readings.
8. Classification: will a day have measurable precipitation, given the preceding hours'
   pressure change, humidity, wind and sky conditions?

## Repository layout

| Path | Contents |
| --- | --- |
| `config/stations.csv` | Station list: `station_id,city,city_code,state,lat,lon,start_year,end_year` |
| `src/lcdweather/` | Python package: `config` (paths, Hive database, years), `units` (metric to U.S. units), `stations`, `acquire/` (Phase 1), `ingest/` (Phases 2 and 3), and the analysis and ML code |
| `scripts/` | Bash and Python entry points: downloads, HDFS upload, `spark-submit` wrappers |
| `jobs/` | Thin PySpark jobs for `spark-submit`, named `<phase>_<name>.py` |
| `hive/ddl/`, `hive/queries/` | HiveQL run with Beeline |
| `notebooks/`, `viz/` | Jupyter notebooks; plotting scripts that read `results/*.csv` and write `figures/` |
| `manifests/` | Small CSVs describing the raw download (committed) |
| `results/`, `figures/` | Outputs of the cluster runs |
| `tests/` | pytest suite; Spark tests run on a local SparkSession with `tests/fixtures/` |

## Settings

Every script and job reads the same settings, each overridable with an environment variable
(`src/lcdweather/config.py` for Python, `scripts/env.sh` for Bash):

| Variable | Default | Meaning |
| --- | --- | --- |
| `LCD_NETID` | `wl3564` | NYU NetID that owns the HDFS home and the Hive database |
| `LCD_HDFS_ROOT` | `hdfs:///user/<netid>_nyu_edu/lcd` | Root of the `raw/`, `clean/`, `fivethirtyeight/` and `results/` zones; an absolute path without a scheme is read as `hdfs://<path>` |
| `LCD_HIVE_DB` | `<netid>_nyu_edu` | Hive database |
| `LCD_FIRST_YEAR`, `LCD_LAST_YEAR` | `2010`, `2025` | Years of the study |
| `LCD_LOCAL_RAW_DIR` | `data/raw` | Local folder of the downloaded LCD files |
| `LCD_FIVETHIRTYEIGHT_DIR` | `data/fivethirtyeight` | Local folder of the validation files |
| `LCD_MANIFESTS_DIR`, `LCD_RESULTS_DIR`, `LCD_FIGURES_DIR` | `manifests`, `results`, `figures` | Local output folders |

A teammate runs the whole pipeline in their own space with `export LCD_NETID=yw9614`.

## Runbook (NYU Dataproc)

Log in to the Dataproc cluster, clone the repository and run every command from its root:

```bash
git clone https://github.com/3376016376joshua-oss/bigdata-lcd-weather.git
cd bigdata-lcd-weather
export LCD_NETID=wl3564   # your own NetID
```

The cluster already provides Python 3, Spark, Hive and HDFS; the figure step installs
Plotly for your user if it is missing.

All six phases in one go, in the background so a closed terminal does not stop them:

```bash
mkdir -p logs && nohup bash scripts/run_all.sh > logs/run_all.log 2>&1 &
tail logs/run_all.log                                      # one line per step, with run time
bash scripts/run_all.sh 3                                  # start at Phase 3 instead
```

Each step writes its full output to `logs/<step>.log`; a failed step prints the end of its
log and stops the run. The sections below run the phases one at a time.

The Spark scripts give the driver 1 GB of memory and a short job history
(`LCD_SPARK_CLUSTER_OPTS` in `scripts/phase_common.sh`): the cluster limits each user to
3 GB on the master node, where the driver runs, and kills a driver that goes over.

### Phase 1 - Collecting and checking the data

```bash
# 1. Download the 162 station-year files (about 1.4 GB) into data/raw/<station>/.
#    Rerunning resumes: files already recorded in the manifest are skipped.
python3 scripts/download_lcd.py

# 2. Check them: header, rows per file and report type, missing days.
python3 scripts/check_lcd.py

# 3. Fetch the ten FiveThirtyEight validation files into data/fivethirtyeight/.
bash scripts/fetch_fivethirtyeight.sh

# 4. Copy both sets to HDFS (add --dry-run to print the hdfs commands only).
bash scripts/upload_hdfs.sh
hdfs dfs -ls -R "hdfs:///user/${LCD_NETID}_nyu_edu/lcd" | head
```

`download_lcd.py` and `check_lcd.py` use only the Python standard library. Both accept
`--years 2014-2015,2024` and `--stations USW00094728,USW00023174` to work on a subset; a
subset run replaces only the selected files' rows in the manifests and keeps the others.
`download_lcd.py` also takes `--out`, `--workers`, `--retries` and `--force`.

HDFS layout after step 4:

```
hdfs:///user/<netid>_nyu_edu/lcd/raw/<station_id>/LCD_<station_id>_<year>.csv
hdfs:///user/<netid>_nyu_edu/lcd/fivethirtyeight/<CODE>.csv
```

The manifests written by steps 1 and 2:

| File | One row per | Columns |
| --- | --- | --- |
| `manifests/download_manifest.csv` | file | `station,year,url,bytes,sha256,downloaded_at` |
| `manifests/file_checks.csv` | file | size, column count, `header_ok`, rows, malformed rows, first and last report, days with hourly reports and with a daily summary |
| `manifests/report_type_counts.csv` | file and report type | `station,year,report_type,rows` |
| `manifests/missing_days.csv` | station and missing day | `station,year,date,missing_hourly,missing_daily_summary` |

`check_lcd.py` exits with status 1 if a file is absent, a header is not the 125-column LCD v2
header, or a file has malformed rows or rows of another station. Missing days are data, not errors.

**What the committed manifests show** (downloaded 2026-11-22):

- 162 files, 1,411,774,781 bytes, 2,046,011 rows; every file has the identical 125-column
  header and no malformed row.
- Rows by report type: FM-15 1,425,274; FM-16 313,797; FM-12 240,346; SOD 59,169; SOM 1,944;
  and three rare types: SY-MT 5,339 (almost all Jacksonville), AUTO 113, blank 29. Phase 2
  keeps SY-MT and AUTO in `lcd_hourly` and drops the blank rows.
- Los Angeles Downtown/USC has no hourly reports on 225 days of 2024 and on every day of 2025
  (its 2025 file holds daily and monthly summaries only), which is why the airport station
  replaces it.
- Elsewhere the files are nearly complete. Every other station, the airport included, has no
  hourly reports on 2025-08-30 to 2025-09-01 (a gap on NOAA's side; the daily summaries are
  there). The only other gaps: New York 2012-01-29/30 and Los Angeles USC 2018-03-25/26
  without hourly reports, and Chicago 2012-02-28 and 2017-08-16 without a daily summary.

### Phase 2 - Loading and cleaning in Hive

Needs the raw zone in HDFS: `$LCD_HDFS_ROOT/raw/<station_id>/LCD_<station_id>_<year>.csv`.

```bash
bash scripts/run_phase2.sh
```

The script zips `src/lcdweather`, submits `jobs/phase2_ingest.py` with `spark-submit`, then
runs the three files in `hive/ddl/` with Beeline. The job reads every raw file with all 125
columns as text, turns the cells into numbers, converts the units and writes three ORC
tables partitioned by `station` and `yr` under `$LCD_HDFS_ROOT/clean/`, registered as
external tables in the Hive database:

Every `run_phase*.sh` script submits its jobs in YARN client mode, so run them on the
master node.

| Table | Rows from | One row per |
| --- | --- | --- |
| `lcd_hourly` | `FM-15` routine, `FM-16` special, `FM-12` synoptic, `SY-MT` synoptic merged with a METAR, `AUTO` automatic station | report |
| `lcd_daily` | `SOD` | station and day |
| `lcd_monthly` | `SOM` | station and month |

Check the result:

```bash
beeline -u jdbc:hive2://localhost:10000 -e "
  USE ${LCD_HIVE_DB:-wl3564_nyu_edu};
  SHOW TABLES LIKE 'lcd_*';
  SELECT city_code, COUNT(*) FROM lcd_daily WHERE is_primary_station GROUP BY city_code;"
hdfs dfs -ls "hdfs:///user/${LCD_NETID:-wl3564}_nyu_edu/lcd/clean/lcd_daily" | head
```

What the cleaning does:

- **Units**: temperatures, departures and degree days to degF; precipitation, snowfall and
  snow depth to inches; wind to mph; visibility to miles. Pressure stays in hPa.
- **Flags**: a trailing flag letter is dropped (`0.805s` suspect, `4.023V` variable); `T`
  (trace) becomes 0.0, with `prcp_trace` set in `lcd_daily`; `*`, `M`, `None`, `VRB` and
  blank become null.
- **Derived columns**: `season` (DJF/MAM/JJA/SON), `hour`, `month`, `doy`, `temp_range_f`,
  `dep_f` (departure of the daily mean from the 1991-2020 normal), `is_warm_extreme`
  (`dep_f >= 10`), `is_cold_extreme` (`dep_f <= -10`), `is_dry_day` (`prcp_in < 0.01`, so a
  trace is dry) and `is_wet_day`. A flag is null when its source value is missing.
- **`sky_cover_okta`**: total sky cover, the largest amount of any reported cloud layer
  (METAR layer amounts are cumulative), 0-8 oktas, 9 when the sky is obscured; null when no
  layer gives an amount.
- **`normal_tavg_f`** in `lcd_monthly` is the monthly mean minus its departure; LCD v2 does
  not give the normal itself.
- **Stations**: `city` and `city_code` come from `config/stations.csv`; stations not listed
  there are dropped. Los Angeles has both of its stations in every table under the code
  `KCQT`. `is_primary_station` is true for the station that stands for the city in that year
  (Downtown/USC to 2023, the airport from 2024), so filter on it to get one station per
  city and year.
- **Duplicates**: reports that are identical in every cleaned column are written once. Two
  different reports for the same minute (an `FM-12` next to an `FM-15`) are both kept.
- **Time**: `obs_ts` is local standard time as written by NOAA, with no daylight saving. The
  jobs run with `spark.sql.session.timeZone=UTC` so that no hour is shifted; set the same in
  any Spark session that reads `obs_ts`, or use the ready-made `obs_date` and `hour`. In
  Hive/Beeline queries use `obs_date` and `hour`: Hive can show `obs_ts` shifted when the
  cluster JVM time zone is not UTC.

Options, passed through to the job:

```bash
bash scripts/run_phase2.sh --years 2010-2013        # a subset: 2014 | 2010-2013 | 2010,2014
# A timed trial that leaves the real tables alone (tables trial_lcd_hourly, ...):
LCD_SKIP_HIVE_DDL=1 bash scripts/run_phase2.sh --years 2010-2013 --table-prefix trial_
# Extra spark-submit flags:
LCD_SPARK_SUBMIT_OPTS="--num-executors 4 --executor-memory 4g" bash scripts/run_phase2.sh
```

Every run replaces the tables it writes, so a run with `--years` and no `--table-prefix`
leaves only those years in `lcd_*`.

If Hive cannot read the tables that Spark registered, write the files only and let Hive
create the tables: `bash scripts/run_phase2.sh --files-only` (the Beeline step then creates
the external tables and runs `MSCK REPAIR TABLE`). A single DDL file is run with:

```bash
beeline -u jdbc:hive2://localhost:10000 --hivevar db="$LCD_HIVE_DB" \
  --hivevar clean_zone="$LCD_HDFS_ROOT/clean" -f hive/ddl/lcd_daily.sql
```

The Beeline address is `LCD_BEELINE_URL` (default `jdbc:hive2://localhost:10000`), and
`LCD_LOCAL_WAREHOUSE` (default `spark-warehouse`) is where a `--local` run keeps its tables.

### Phase 3 - Validation and profiling

Needs the Phase 2 tables and the FiveThirtyEight files in
`$LCD_HDFS_ROOT/fivethirtyeight/<CODE>.csv`.

```bash
bash scripts/run_phase3.sh
```

The script submits `jobs/phase3_validate.py` and `jobs/phase3_profile.py`, which write to
`$LCD_HDFS_ROOT/results/<name>/`, then copies each result to `results/<name>.csv` with
`hdfs dfs -getmerge`:

| File | Contents |
| --- | --- |
| `results/validation_538.csv` | Per city, `lcd_daily` against FiveThirtyEight for 2014-07-01 to 2015-06-30: days compared and, for `tmax`, `tmin`, `tavg` and `prcp`, the pairs (`_n`), correlation (`_corr`), mean absolute difference (`_mae`) and mean difference LCD minus FiveThirtyEight (`_bias`) |
| `results/validation_538_daily.csv` | The joined days: both values and their difference for each measure |
| `results/profile_report_types.csv` | Raw zone: rows per station, year and `REPORT_TYPE` |
| `results/profile_missing.csv` | Cleaned tables: rows, missing values and percent missing per station and column |
| `results/profile_ranges.csv` | Cleaned tables: count, minimum, maximum, mean and standard deviation per station and numeric column |
| `results/table_row_counts.csv` | Exact rows of each table, all stations and primary stations only, with stations, station-years and first and last year |

Only the measured values are compared. FiveThirtyEight took its normals from records since
1880 and LCD v2 uses 1991-2020, so the anomalies of the two sources are expected to differ.
FiveThirtyEight rounds to whole degF, which alone gives a mean absolute difference of up to
about 0.3 degF.

Both jobs take `--from-files` to read the ORC files in the cleaned zone instead of the Hive
tables.

### Trying Phases 2 and 3 on a laptop

In the local environment described under "Local development", `--local` runs the same jobs
without HDFS or Hive:

```bash
python jobs/phase2_ingest.py --local --input data/raw --years 2014-2015
python jobs/phase3_validate.py --local --fivethirtyeight data/fivethirtyeight
python jobs/phase3_profile.py --local --input data/raw --years 2014-2015
```

The tables go to `spark-warehouse/clean/` and the results to `results/`.

### Phase 4 - Analysis with Hive and Spark (questions 1-6)

The geography, time and category analysis. It answers questions 1-6 from the cleaned Hive
tables `lcd_daily`, `lcd_hourly` and `lcd_monthly`. Each `hive/queries/q<N>_<name>.sql` file holds
one query and produces one result table with the same name. The same files run on both
engines: Beeline runs them on Hive, and `jobs/phase4_analysis.py` runs them with Spark SQL,
so every question has a single definition.

For question 4 this phase covers the seasonal and hour-of-day temperature cycles; the
clustering of the ten cities is done with k-means in the Spark MLlib phase.

| Question | Query files (`hive/queries/`) |
| --- | --- |
| 1 Temperature anomalies, 2014-15 West/East pattern | `q1_monthly_anomaly`, `q1_annual_anomaly`, `q1_city_deviation_ranking`, `q1_jul_jun_city_anomaly`, `q1_west_east_pattern` |
| 2 Extreme days per city, year and season | `q2_extreme_days_by_year`, `q2_extreme_days_by_season` |
| 3 Warm against cold extremes and the trend | `q3_balance_by_year`, `q3_balance_trend` |
| 4 Seasonal and hourly temperature cycles | `q4_monthly_climatology`, `q4_hourly_profile`, `q4_cycle_amplitude` |
| 5 Precipitation against normal, dry spells, heavy rain | `q5_monthly_precip_vs_normal`, `q5_annual_precip_vs_normal`, `q5_dry_spells`, `q5_heaviest_rain_days`, `q5_california_drought` |
| 6 Volatility, humidity and special reports | `q6_city_volatility`, `q6_seasonal_volatility`, `q6_special_reports_by_day_type`, `q6_special_reports_correlation`, `q6_special_reports_around_storms` |

Definitions used throughout: an extreme day has a daily mean 10 °F or more above or below
normal; a dry day has less than 0.01 in of precipitation (trace is dry); West is Los
Angeles, Phoenix and Seattle, East is Chicago, Indianapolis, New York and Philadelphia;
routine reports are `FM-15` and special reports are `FM-16`. Cities are grouped by
`city_code` and every query reads only rows with `is_primary_station`, so the Los Angeles
series is Downtown/USC for 2010-2023 and the airport for 2024-2025, one station per day.
The hourly cycle puts each routine report in its nearest hour (the report at 13:53 counts
for 14:00). Dry spells (`q5_dry_spells.sql`) use a gaps-and-islands window query.

Run from the repository root on the cluster, after the cleaned tables exist. The scripts
read `LCD_NETID`, `LCD_HIVE_DB`, `LCD_HDFS_ROOT` and `LCD_RESULTS_DIR` (see
`scripts/env.sh`).

```bash
# Spark SQL: run all queries, write results to HDFS, then copy them into results/
scripts/run_phase4.sh all

# The same in two steps, or only some questions
scripts/run_phase4.sh spark --questions 1 5
scripts/run_phase4.sh fetch

# HiveQL through Beeline: the same queries on Hive, output in results/hive/
LCD_BEELINE_URL=jdbc:hive2://localhost:10000 scripts/run_phase4.sh hive

# One query by hand
beeline -u jdbc:hive2://localhost:10000 --hivevar db=wl3564_nyu_edu \
  -f hive/queries/q5_dry_spells.sql
```

`spark` writes each result to `$LCD_HDFS_ROOT/results/q<N>_<name>/` and `fetch` merges it
into `results/q<N>_<name>.csv`. To skip HDFS, pass a local directory to the job:
`scripts/run_phase4.sh spark --results-dir results`. The `all` step always goes through HDFS
and rejects `--results-dir`.

The tests in `tests/analysis/` run every query on small synthetic tables in local Spark
and draw every figure.

### Phase 5 - Machine learning with Spark MLlib (questions 7-8)

The jobs are `jobs/phase5_*.py`. They read the
cleaned Hive tables `lcd_hourly` and `lcd_daily`, whose columns (`obs_ts`, `report_type`,
`temp_f`, `station_pressure_hpa`, `tmax_f`, `prcp_in`, ...) come from Phase 2, so Phase 2
must have been run first. Only rows with `is_primary_station` are used, so Los Angeles has
one station per day.

```bash
# Submit the three jobs to YARN, then merge their result CSVs from HDFS into results/.
bash scripts/run_phase5.sh

bash scripts/run_phase5.sh kmeans      # only the named job(s): regression, classification, kmeans
bash scripts/run_phase5.sh fetch       # only download the results again
```

The script zips `src/lcdweather` for `--py-files`, so nothing is installed on the cluster.
`LCD_SPARK_SUBMIT_OPTS` (extra spark-submit flags, shared with `run_phase2.sh`, applied
after the `LCD_SPARK_CLUSTER_OPTS` defaults), `PHASE5_JOB_ARGS` (extra flags for every job) and `PHASE5_GRID` (`full`, or `quick` for a one-point grid) adjust the run. One job by hand:

```bash
(cd src && python3 -m zipfile -c ../lcdweather.zip lcdweather)
spark-submit --py-files lcdweather.zip jobs/phase5_regression.py \
  --database "${LCD_NETID}_nyu_edu" --results-dir "hdfs:///user/${LCD_NETID}_nyu_edu/lcd/results"
```

| Job | Question | Models | Results |
| --- | --- | --- | --- |
| `phase5_regression.py` | 7: next-day maximum temperature | linear regression, gradient-boosted trees, persistence baseline (tomorrow = today) | `q7_tuning`, `q7_metrics` (RMSE, MAE, R2), `q7_metrics_by_city`, `q7_predictions`, `q7_feature_importance` |
| `phase5_classification.py` | 8: measurable precipitation (>= 0.01 in) on the next day | logistic regression, random forest, persistence baseline | `q8_tuning`, `q8_metrics` (ROC and PR AUC, precision, recall, F1), `q8_confusion_matrix`, `q8_metrics_by_city`, `q8_roc_curve`, `q8_feature_importance`, `q8_class_balance` |
| `phase5_kmeans.py` | 4: climate types of the ten cities | k-means for k = 2..6, best silhouette selected | `kmeans_silhouette`, `kmeans_assignments`, `kmeans_city_features` |

How the models are built (`src/lcdweather/ml/`):

- **One row per city and day.** Features are known by the end of day *t*; the label belongs to
  day *t+1*. Regression uses the day-of-year sine and cosine and the month of the predicted
  day, today's departure from normal, maximum, minimum and mean, the same three values 1, 2
  and 3 days back, and a summary of today's routine (FM-15) hourly reports: mean, minimum,
  maximum and last temperature, dew point, humidity, wind, pressure and the pressure change
  over 3, 12 and 24 hours. Classification uses the pressure changes, humidity, dew point
  depression, wind and gusts, sky cover, hourly precipitation and the number of special
  (FM-16) reports, plus month and city.
- **No leakage.** Lags and labels are taken by calendar-day offset, so a missing day gives a
  null instead of another day's value, and every window looks backward only. The split is by
  the predicted day: train 2010-2021, validation 2022-2023, test 2024-2025.
- **Pipeline.** Median imputer, one-hot city and month, `VectorAssembler`, `StandardScaler`,
  then the estimator. Imputer and scaler are fitted on the training rows only.
- **Tuning.** Each grid point is fitted on train and scored on validation (RMSE, ROC AUC);
  the best one is refitted on train + validation and scored once on test. Classification
  metrics use a 0.5 decision threshold.
- **Baselines.** The persistence baseline (tomorrow = today) is scored only on days whose
  own value is known; those days are never dropped from the models' data.

Figures (need pandas and matplotlib; they read `results/*.csv` and write `figures/*.png`):

```bash
python3 viz/ml_regression.py       # ml_q7_*: metrics, predicted vs actual, importance, RMSE by city
python3 viz/ml_classification.py   # ml_q8_*: metrics, ROC and PR curves, confusion, importance
python3 viz/ml_kmeans.py           # ml_kmeans_*: silhouette, monthly profiles, map of the clusters
```

A smoke run without Hive, on small generated tables (locally or on the cluster):

```bash
LCD_SPARK_SUBMIT_OPTS="--master local[2]" PHASE5_JOB_ARGS="--synthetic" PHASE5_GRID=quick \
  LCD_RESULTS_URI=results bash scripts/run_phase5.sh
```

### Phase 6 - Visualization and run-time scaling

_Exporting `results/*.csv` from HDFS and drawing the figures. Steps are added with the
visualization code._

#### Figures

Every figure, for questions 1-8, k-means and the run-time scaling, in one step (it installs
Plotly and seaborn for your user when they are missing):

```bash
bash scripts/run_phase6_figures.sh
```

The figure scripts read only `results/*.csv`. Those for questions 1-6 write a PNG
(matplotlib/seaborn) and an interactive HTML page (Plotly) per figure into `figures/`:

| Script | Figures |
| --- | --- |
| `viz/q1_anomaly.py` | `q1_anomaly_heatmap`, `q1_west_east_pattern` |
| `viz/q2_extremes.py` | `q2_extreme_days_by_year`, `q2_extreme_days_by_season` |
| `viz/q3_balance.py` | `q3_balance_by_year`, `q3_balance_trend_by_city` |
| `viz/q4_cycles.py` | `q4_hourly_cycle`, `q4_monthly_climatology` |
| `viz/q5_precipitation.py` | `q5_precip_actual_vs_normal`, `q5_longest_dry_spells`, `q5_heaviest_rain_days` |
| `viz/q6_volatility.py` | `q6_city_volatility`, `q6_special_reports_wet_vs_dry`, `q6_special_reports_around_storms` |

#### Run-time scaling

Times the Phase 2 ingestion job (`jobs/phase2_ingest.py`) and the Phase 4 analysis job
(`jobs/phase4_analysis.py`) on 1, 4, 8 and 16 years of input (2025, 2022-2025, 2018-2025,
2010-2025) and records wall-clock time against the raw input size. The raw zone must hold
Phase 1's uploads.

```bash
bash scripts/run_phase6_timing.sh                              # both jobs, four sizes
bash scripts/run_phase6_timing.sh --jobs analysis --repeats 3  # median of three runs
python3 viz/timing_scaling.py                                  # figures/timing_runtime_scaling.png
```

- `results/runtime_scaling.csv`: one row per run with the job, years, input files, bytes and
  rows (from `hdfs dfs -du` and a line count of the raw CSVs; `--skip-row-count` skips the
  count), wall-clock seconds, exit code and the exact command.
- `results/runtime_scaling_summary.csv`: per job and size the median time, seconds per GB,
  input and time ratios against the 1-year run, and the slope of log(time) on log(bytes).
  A slope of 1 is linear growth; below 1 means fixed start-up cost dominates.
- Each window writes to scratch outputs, never the production cleaned zone or database:
  `phase2_ingest.py --input <raw zone> --output <clean-root>/<n>y --db <db-prefix>_t<n>y
  --years <start>-<end>`, then `phase4_analysis.py --db <db-prefix>_t<n>y --results-dir
  <analysis-results-root>/<n>y`. The defaults are `<LCD_HDFS_ROOT>/timing/clean`,
  `<LCD_HIVE_DB>_timing` and `<LCD_HDFS_ROOT>/timing/results`; change them with
  `--clean-root`, `--db-prefix` and `--analysis-results-root`.
- `--jobs analysis` alone reuses the `<db-prefix>_t<n>y` databases of an earlier ingest run.
- A failed job is recorded with its exit code and the script exits with status 1.

## Local development (optional)

The real runs happen on NYU Dataproc. A local environment is only for linting and running
the tests, which use a local SparkSession and the small sample in `tests/fixtures/`:

```bash
conda create -n bigdata-lcd python=3.11
conda activate bigdata-lcd
pip install -e ".[dev]"

# Spark needs Java 17, for example on macOS:
brew install openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"

ruff check .
pytest
```

Without pyspark or Java the Spark tests are skipped and the rest still runs. GitHub Actions
runs `ruff check .` and `pytest -q` on every push and pull request (Python 3.11, Java 17,
pyspark 3.5), with `LCD_REQUIRE_SPARK=1` so the Spark tests cannot be skipped there.
