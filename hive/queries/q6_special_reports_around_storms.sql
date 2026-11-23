-- Q6: how special reports (FM-16) cluster around storms.
-- The five wettest days of every city are taken as storm days. For day offsets
-- -3 to +3 around them the mean number of special reports per day is compared
-- with the mean over all days of the city (city_mean_special_reports).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q6_special_reports_around_storms.sql
WITH hourly_day AS (
  SELECT
    city_code,
    obs_date,
    SUM(IF(report_type = 'FM-16', 1, 0)) AS special_reports
  FROM ${hivevar:db}.lcd_hourly
  WHERE is_primary_station AND report_type IN ('FM-15', 'FM-16')
  GROUP BY city_code, obs_date
),
days AS (
  SELECT
    d.city_code,
    d.city,
    d.obs_date,
    d.prcp_in,
    h.special_reports
  FROM ${hivevar:db}.lcd_daily d
  JOIN hourly_day h ON d.city_code = h.city_code AND d.obs_date = h.obs_date
  WHERE d.is_primary_station AND d.prcp_in IS NOT NULL
),
ranked AS (
  SELECT
    city_code,
    obs_date,
    ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY prcp_in DESC, obs_date) AS storm_rank
  FROM days
  WHERE prcp_in >= 0.01
),
storms AS (
  SELECT city_code, obs_date AS storm_date
  FROM ranked
  WHERE storm_rank <= 5
),
around AS (
  SELECT
    a.city_code,
    a.city,
    DATEDIFF(a.obs_date, s.storm_date) AS day_offset,
    a.special_reports,
    a.prcp_in
  FROM days a
  JOIN storms s ON a.city_code = s.city_code
  WHERE DATEDIFF(a.obs_date, s.storm_date) BETWEEN -3 AND 3
),
by_offset AS (
  SELECT
    city_code,
    MAX(city) AS city,
    day_offset,
    COUNT(*) AS n_days,
    AVG(special_reports) AS mean_special,
    AVG(prcp_in) AS mean_prcp
  FROM around
  GROUP BY city_code, day_offset
),
baseline AS (
  SELECT city_code, AVG(special_reports) AS city_mean_special
  FROM days
  GROUP BY city_code
)
SELECT
  o.city_code,
  o.city,
  o.day_offset,
  o.n_days,
  ROUND(o.mean_special, 2) AS mean_special_reports,
  ROUND(o.mean_prcp, 2) AS mean_prcp_in,
  ROUND(b.city_mean_special, 2) AS city_mean_special_reports
FROM by_offset o
JOIN baseline b ON o.city_code = b.city_code
ORDER BY city_code, day_offset;
