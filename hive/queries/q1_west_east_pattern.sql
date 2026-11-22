-- Q1: how unusual was the 2014-15 warm West / cold East pattern.
-- For every complete July-June year the mean anomaly of the West cities and of
-- the East cities is computed (each city weighted equally) and the periods are
-- ranked by the West minus East contrast. is_2014_15 marks the reference year.
-- Regions: West = Los Angeles, Phoenix, Seattle. East = Chicago, Indianapolis,
-- New York, Philadelphia.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q1_west_east_pattern.sql
WITH tagged AS (
  SELECT
    city_code,
    dep_f,
    MONTH(obs_date) AS mo,
    IF(MONTH(obs_date) >= 7, yr, yr - 1) AS start_yr
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station AND dep_f IS NOT NULL
),
city_period AS (
  SELECT
    city_code,
    start_yr,
    COUNT(DISTINCT mo) AS n_months,
    AVG(dep_f) AS anomaly
  FROM tagged
  GROUP BY city_code, start_yr
),
region_period AS (
  SELECT
    start_yr,
    AVG(IF(city_code IN ('KCQT', 'KPHX', 'KSEA'), anomaly, NULL)) AS west_anomaly,
    AVG(IF(city_code IN ('KMDW', 'KIND', 'KNYC', 'KPHL'), anomaly, NULL)) AS east_anomaly,
    SUM(IF(city_code IN ('KCQT', 'KPHX', 'KSEA'), 1, 0)) AS west_cities,
    SUM(IF(city_code IN ('KMDW', 'KIND', 'KNYC', 'KPHL'), 1, 0)) AS east_cities
  FROM city_period
  WHERE n_months = 12
  GROUP BY start_yr
)
SELECT
  start_yr,
  CONCAT(CAST(start_yr AS STRING), '-07..', CAST(start_yr + 1 AS STRING), '-06') AS period_label,
  west_cities,
  east_cities,
  ROUND(west_anomaly, 2) AS west_anomaly_f,
  ROUND(east_anomaly, 2) AS east_anomaly_f,
  ROUND(west_anomaly - east_anomaly, 2) AS west_minus_east_f,
  RANK() OVER (ORDER BY west_anomaly - east_anomaly DESC) AS contrast_rank,
  RANK() OVER (ORDER BY west_anomaly DESC) AS west_warm_rank,
  RANK() OVER (ORDER BY east_anomaly ASC) AS east_cold_rank,
  COUNT(*) OVER () AS n_periods,
  IF(start_yr = 2014, 1, 0) AS is_2014_15
FROM region_period
WHERE west_anomaly IS NOT NULL AND east_anomaly IS NOT NULL
ORDER BY start_yr;
