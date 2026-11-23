-- Daily summaries (SOD), one row per station and day.
-- Temperatures and degree days in degF, precipitation and snow in inches (a trace is 0.0),
-- wind in mph; dep_f is the departure of the daily mean from the 1991-2020 normal.
--
-- Registers the ORC files that jobs/phase2_ingest.py wrote as an external table and loads
-- their partitions. Does nothing to a table that Phase 2 already registered, apart from
-- refreshing its partitions. Run with Beeline:
--   beeline -u "$LCD_BEELINE_URL" --hivevar db=wl3564_nyu_edu \
--     --hivevar clean_zone=hdfs:///user/wl3564_nyu_edu/lcd/clean -f hive/ddl/lcd_daily.sql

CREATE DATABASE IF NOT EXISTS ${hivevar:db};
USE ${hivevar:db};

CREATE EXTERNAL TABLE IF NOT EXISTS lcd_daily (
  city_code          STRING,
  city               STRING,
  obs_date           DATE,
  tmax_f             DOUBLE,
  tmin_f             DOUBLE,
  tavg_f             DOUBLE,
  dep_f              DOUBLE,
  prcp_in            DOUBLE,
  prcp_trace         BOOLEAN,
  snow_in            DOUBLE,
  snow_depth_in      DOUBLE,
  hdd                DOUBLE,
  cdd                DOUBLE,
  peak_wind_mph      DOUBLE,
  sustained_wind_mph DOUBLE,
  sunrise            STRING,
  sunset             STRING,
  month              INT,
  season             STRING,
  doy                INT,
  temp_range_f       DOUBLE,
  is_warm_extreme    BOOLEAN,
  is_cold_extreme    BOOLEAN,
  is_dry_day         BOOLEAN,
  is_wet_day         BOOLEAN,
  is_primary_station BOOLEAN
)
PARTITIONED BY (station STRING, yr INT)
STORED AS ORC
LOCATION '${hivevar:clean_zone}/lcd_daily';

MSCK REPAIR TABLE lcd_daily;
