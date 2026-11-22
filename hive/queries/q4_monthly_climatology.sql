-- Q4: seasonal temperature cycle, the 2010-2025 monthly climatology per city.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q4_monthly_climatology.sql
SELECT
  city_code,
  MAX(city) AS city,
  MONTH(obs_date) AS mo,
  COUNT(tavg_f) AS n_days,
  ROUND(AVG(tavg_f), 2) AS mean_tavg_f,
  ROUND(AVG(tmax_f), 2) AS mean_tmax_f,
  ROUND(AVG(tmin_f), 2) AS mean_tmin_f,
  ROUND(AVG(temp_range_f), 2) AS mean_daily_range_f
FROM ${hivevar:db}.lcd_daily
GROUP BY city_code, MONTH(obs_date)
ORDER BY city_code, mo;
