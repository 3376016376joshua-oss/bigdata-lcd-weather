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
| `src/lcdweather/` | Python package: `config` (paths, Hive database, years), `units` (metric to U.S. units), `stations`, `acquire/` (Phase 1), and the ingestion, analysis and ML code |
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
| `LCD_HDFS_ROOT` | `hdfs:///user/<netid>_nyu_edu/lcd` | Root of the `raw/`, `clean/`, `fivethirtyeight/` and `results/` zones |
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

The cluster already provides Python 3, Spark, Hive and HDFS; nothing has to be installed
there.

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
  and three rare types to drop or fold in during cleaning: SY-MT 5,339 (almost all
  Jacksonville), AUTO 113, blank 29.
- Los Angeles Downtown/USC has no hourly reports on 225 days of 2024 and on every day of 2025
  (its 2025 file holds daily and monthly summaries only), which is why the airport station
  replaces it.
- Elsewhere the files are nearly complete. Every other station, the airport included, has no
  hourly reports on 2025-08-30 to 2025-09-01 (a gap on NOAA's side; the daily summaries are
  there). The only other gaps: New York 2012-01-29/30 and Los Angeles USC 2018-03-25/26
  without hourly reports, and Chicago 2012-02-28 and 2017-08-16 without a daily summary.

### Phase 2 - Loading and cleaning in Hive

_Raw CSV to the cleaned ORC tables `lcd_hourly`, `lcd_daily` and `lcd_monthly`. Steps are
added with the ingestion code._

### Phase 3 - Analysis with Hive and Spark (questions 1-6)

_Steps are added with the analysis code._

### Phase 4 - Machine learning with Spark MLlib (questions 7-8)

_Steps are added with the ML code._

### Phase 5 - Results and figures

_Exporting `results/*.csv` from HDFS and drawing the figures. Steps are added with the
visualization code._

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
