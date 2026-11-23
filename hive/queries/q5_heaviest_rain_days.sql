-- Q5: heaviest daily rain events, the ten wettest days of every city.
-- overall_rank ranks the day among all wet days of all cities.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q5_heaviest_rain_days.sql
WITH ranked AS (
  SELECT
    city_code,
    city,
    obs_date,
    yr,
    season,
    prcp_in,
    ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY prcp_in DESC, obs_date) AS city_rank,
    RANK() OVER (ORDER BY prcp_in DESC) AS overall_rank
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station AND prcp_in >= 0.01
)
SELECT
  city_code,
  city,
  city_rank,
  overall_rank,
  CAST(obs_date AS STRING) AS obs_date,
  yr,
  season,
  ROUND(prcp_in, 2) AS prcp_in
FROM ranked
WHERE city_rank <= 10
ORDER BY city_code, city_rank;
