-- Q6: how the number of special reports (FM-16) per day moves with daily
-- precipitation and with the pressure swing of the day, as correlations per
-- city. pressure_range_hpa is the highest minus the lowest station pressure
-- reported during the day.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q6_special_reports_correlation.sql
WITH hourly_day AS (
  SELECT
    city_code,
    obs_date,
    SUM(IF(report_type = 'FM-16', 1, 0)) AS special_reports,
    SUM(IF(report_type = 'FM-15', 1, 0)) AS routine_reports,
    MAX(station_pressure_hpa) - MIN(station_pressure_hpa) AS pressure_range
  FROM ${hivevar:db}.lcd_hourly
  WHERE report_type IN ('FM-15', 'FM-16')
  GROUP BY city_code, obs_date
),
days AS (
  SELECT
    d.city_code,
    d.city,
    d.prcp_in,
    h.special_reports,
    h.routine_reports,
    h.pressure_range
  FROM ${hivevar:db}.lcd_daily d
  JOIN hourly_day h ON d.city_code = h.city_code AND d.obs_date = h.obs_date
  WHERE d.prcp_in IS NOT NULL
)
SELECT
  city_code,
  MAX(city) AS city,
  COUNT(*) AS n_days,
  SUM(routine_reports) AS routine_reports,
  SUM(special_reports) AS special_reports,
  ROUND(AVG(special_reports), 2) AS mean_special_reports_per_day,
  ROUND(CORR(special_reports, prcp_in), 3) AS corr_special_vs_prcp,
  ROUND(CORR(special_reports, pressure_range), 3) AS corr_special_vs_pressure_range,
  ROUND(AVG(pressure_range), 2) AS mean_pressure_range_hpa
FROM days
GROUP BY city_code
ORDER BY city_code;
