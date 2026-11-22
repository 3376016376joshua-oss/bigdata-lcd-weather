-- Q4: hour-by-hour temperature cycle per city and season.
-- Uses only the routine hourly reports (FM-15) so that bursts of special
-- reports during storms do not weight some hours more than others.
-- diurnal_anomaly_f is the hourly mean minus the mean of the 24 hourly means of
-- the same city and season.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q4_hourly_profile.sql
WITH hourly AS (
  SELECT
    city_code,
    MAX(city) AS city,
    season,
    HOUR(obs_ts) AS hr,
    COUNT(*) AS n_obs,
    AVG(temp_f) AS mean_temp
  FROM ${hivevar:db}.lcd_hourly
  WHERE report_type = 'FM-15' AND temp_f IS NOT NULL
  GROUP BY city_code, season, HOUR(obs_ts)
)
SELECT
  city_code,
  city,
  season,
  hr,
  n_obs,
  ROUND(mean_temp, 2) AS mean_temp_f,
  ROUND(mean_temp - AVG(mean_temp) OVER (PARTITION BY city_code, season), 2)
    AS diurnal_anomaly_f
FROM hourly
ORDER BY city_code, season, hr;
