-- Q5: which cities and years were wetter or drier than normal.
-- Annual precipitation per city and year against the station normal (sum of the
-- monthly normals, NULL unless all months of the year have one) and against the
-- 2010-2025 mean of the city. dryness_rank_in_city = 1 is the driest year of
-- the city, which also shows where the California drought years 2012-2016 rank
-- for Los Angeles (KCQT).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q5_annual_precip_vs_normal.sql
WITH daily_month AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    MONTH(obs_date) AS mo,
    COUNT(*) AS n_days,
    SUM(IF(prcp_in >= 0.01, 1, 0)) AS wet_days,
    SUM(prcp_in) AS total_prcp
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station AND prcp_in IS NOT NULL
  GROUP BY city_code, yr, MONTH(obs_date)
),
official AS (
  SELECT
    city_code,
    yr,
    `month` AS mo,
    MAX(total_prcp_in - dep_prcp_in) AS normal_prcp
  FROM ${hivevar:db}.lcd_monthly
  WHERE is_primary_station
  GROUP BY city_code, yr, `month`
),
annual AS (
  SELECT
    d.city_code,
    MAX(d.city) AS city,
    d.yr,
    COUNT(*) AS n_months,
    SUM(d.n_days) AS n_days,
    SUM(d.wet_days) AS wet_days,
    SUM(d.total_prcp) AS total_prcp,
    IF(COUNT(o.normal_prcp) = COUNT(*), SUM(o.normal_prcp), CAST(NULL AS DOUBLE))
      AS normal_prcp
  FROM daily_month d
  LEFT JOIN official o
    ON d.city_code = o.city_code AND d.yr = o.yr AND d.mo = o.mo
  GROUP BY d.city_code, d.yr
),
with_baseline AS (
  SELECT
    city_code,
    city,
    yr,
    n_months,
    n_days,
    wet_days,
    total_prcp,
    normal_prcp,
    AVG(total_prcp) OVER (PARTITION BY city_code) AS period_mean_prcp,
    RANK() OVER (PARTITION BY city_code ORDER BY total_prcp ASC) AS dryness_rank_in_city
  FROM annual
)
SELECT
  city_code,
  city,
  yr,
  n_months,
  n_days,
  wet_days,
  ROUND(total_prcp, 2) AS total_prcp_in,
  ROUND(normal_prcp, 2) AS normal_prcp_in,
  ROUND(total_prcp - normal_prcp, 2) AS dep_prcp_in,
  IF(normal_prcp IS NULL OR normal_prcp = 0, CAST(NULL AS DOUBLE),
     ROUND(100 * total_prcp / normal_prcp, 1)) AS pct_of_normal,
  ROUND(period_mean_prcp, 2) AS period_mean_prcp_in,
  IF(period_mean_prcp = 0, CAST(NULL AS DOUBLE),
     ROUND(100 * total_prcp / period_mean_prcp, 1)) AS pct_of_period_mean,
  dryness_rank_in_city
FROM with_baseline
ORDER BY city_code, yr;
