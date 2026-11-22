-- Q1: annual temperature anomaly per city and year, with rankings.
-- warm_rank_in_year compares the ten cities within one year, warm_rank_in_city
-- compares the 16 years of one city, abs_anomaly_rank ranks every city-year by
-- the size of its deviation from normal in either direction.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q1_annual_anomaly.sql
WITH annual AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    COUNT(dep_f) AS n_days,
    AVG(dep_f) AS anomaly
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
  GROUP BY city_code, yr
)
SELECT
  city_code,
  city,
  yr,
  n_days,
  ROUND(anomaly, 2) AS anomaly_f,
  RANK() OVER (PARTITION BY yr ORDER BY anomaly DESC) AS warm_rank_in_year,
  RANK() OVER (PARTITION BY city_code ORDER BY anomaly DESC) AS warm_rank_in_city,
  RANK() OVER (ORDER BY ABS(anomaly) DESC) AS abs_anomaly_rank
FROM annual
ORDER BY city_code, yr;
