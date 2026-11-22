-- Routine (FM-15), special (FM-16) and synoptic (FM-12) reports, one row per report.
-- obs_ts is local standard time; temperatures in degF, wind in mph, visibility in miles,
-- precipitation in inches (a trace is 0.0), pressure in hPa.
--
-- Registers the ORC files that jobs/phase2_ingest.py wrote as an external table and loads
-- their partitions. Does nothing to a table that Phase 2 already registered, apart from
-- refreshing its partitions. Run with Beeline:
--   beeline -u "$LCD_BEELINE_URL" --hivevar db=wl3564_nyu_edu \
--     --hivevar clean_zone=hdfs:///user/wl3564_nyu_edu/lcd/clean -f hive/ddl/lcd_hourly.sql

USE ${hivevar:db};

CREATE EXTERNAL TABLE IF NOT EXISTS lcd_hourly (
  city_code              STRING,
  city                   STRING,
  obs_ts                 TIMESTAMP,
  obs_date               DATE,
  report_type            STRING,
  temp_f                 DOUBLE,
  dewpt_f                DOUBLE,
  wetbulb_f              DOUBLE,
  rh_pct                 DOUBLE,
  wind_speed_mph         DOUBLE,
  wind_gust_mph          DOUBLE,
  wind_dir_deg           INT,
  station_pressure_hpa   DOUBLE,
  sea_level_pressure_hpa DOUBLE,
  pressure_change_hpa    DOUBLE,
  visibility_mi          DOUBLE,
  sky_conditions         STRING,
  sky_cover_okta         INT,
  precip_in              DOUBLE,
  hour                   INT,
  month                  INT,
  season                 STRING,
  is_special             BOOLEAN,
  is_primary_station     BOOLEAN
)
PARTITIONED BY (station STRING, yr INT)
STORED AS ORC
LOCATION '${hivevar:clean_zone}/lcd_hourly';

MSCK REPAIR TABLE lcd_hourly;
