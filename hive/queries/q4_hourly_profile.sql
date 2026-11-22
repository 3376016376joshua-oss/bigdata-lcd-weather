-- Q4: hour-by-hour temperature cycle per city and season.
-- Uses only the routine hourly reports (FM-15) so that bursts of special
-- reports during storms do not weight some hours more than others.
-- Each report goes to its nearest hour, so the routine report at 13:53 stands for
-- 14:00 and one at 23:53 wraps to hour 0.
-- diurnal_anomaly_f is the hourly mean minus the mean of the 24 hourly means of
-- the same city and season.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q4_hourly_profile.sql
WITH hourly AS (
  SELECT
    city_code,
    MAX(city) AS city,
    season,
    PMOD(HOUR(obs_ts) + IF(MINUTE(obs_ts) >= 30, 1, 0), 24) AS hr,
    COUNT(*) AS n_obs,
    AVG(temp_f) AS mean_temp
  FROM ${hivevar:db}.lcd_hourly
  WHERE is_primary_station AND report_type = 'FM-15' AND temp_f IS NOT NULL
  GROUP BY city_code, season, PMOD(HOUR(obs_ts) + IF(MINUTE(obs_ts) >= 30, 1, 0), 24)
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
