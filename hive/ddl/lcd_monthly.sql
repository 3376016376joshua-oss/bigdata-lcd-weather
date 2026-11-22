-- Monthly summaries (SOM), one row per station and month.
-- Temperatures and degree days in degF, precipitation and snow in inches; departures are
-- from the 1991-2020 normals.
--
-- Registers the ORC files that jobs/phase2_ingest.py wrote as an external table and loads
-- their partitions. Does nothing to a table that Phase 2 already registered, apart from
-- refreshing its partitions. Run with Beeline:
--   beeline -u "$LCD_BEELINE_URL" --hivevar db=wl3564_nyu_edu \
--     --hivevar clean_zone=hdfs:///user/wl3564_nyu_edu/lcd/clean -f hive/ddl/lcd_monthly.sql

USE ${hivevar:db};

CREATE EXTERNAL TABLE IF NOT EXISTS lcd_monthly (
  city_code          STRING,
  city               STRING,
  month              INT,
  mean_tmax_f        DOUBLE,
  mean_tmin_f        DOUBLE,
  mean_tavg_f        DOUBLE,
  dep_tavg_f         DOUBLE,
  total_prcp_in      DOUBLE,
  dep_prcp_in        DOUBLE,
  total_snow_in      DOUBLE,
  days_max_ge_90     INT,
  days_min_le_32     INT,
  hdd                DOUBLE,
  cdd                DOUBLE,
  normal_tavg_f      DOUBLE,
  is_primary_station BOOLEAN
)
PARTITIONED BY (station STRING, yr INT)
STORED AS ORC
LOCATION '${hivevar:clean_zone}/lcd_monthly';

MSCK REPAIR TABLE lcd_monthly;
