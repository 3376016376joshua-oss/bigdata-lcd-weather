-- Q5: California drought check for Los Angeles (KCQT), 2012-2016 against the
-- other years of 2010-2025. For both groups of years: mean annual precipitation,
-- wet days per year and the longest dry spell that started in those years
-- (gaps and islands as in q5_dry_spells.sql).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q5_california_drought.sql
WITH la_days AS (
  SELECT
    obs_date,
    yr,
    prcp_in,
    IF(yr BETWEEN 2012 AND 2016, 'drought 2012-2016', 'other years') AS period_label
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station AND city_code = 'KCQT' AND prcp_in IS NOT NULL
),
annual AS (
  SELECT
    period_label,
    yr,
    SUM(prcp_in) AS total_prcp,
    SUM(IF(prcp_in >= 0.01, 1, 0)) AS wet_days
  FROM la_days
  GROUP BY period_label, yr
),
period_precip AS (
  SELECT
    period_label,
    COUNT(*) AS n_years,
    AVG(total_prcp) AS mean_annual_prcp,
    MIN(total_prcp) AS driest_year_prcp,
    AVG(wet_days) AS mean_wet_days
  FROM annual
  GROUP BY period_label
),
dry_days AS (
  SELECT
    obs_date,
    DATE_SUB(obs_date, CAST(ROW_NUMBER() OVER (ORDER BY obs_date) AS INT)) AS island_key
  FROM la_days
  WHERE prcp_in < 0.01
),
spells AS (
  SELECT
    MIN(obs_date) AS start_date,
    COUNT(*) AS length_days
  FROM dry_days
  GROUP BY island_key
),
period_spells AS (
  SELECT
    IF(YEAR(start_date) BETWEEN 2012 AND 2016, 'drought 2012-2016', 'other years')
      AS period_label,
    MAX(length_days) AS longest_dry_spell_days
  FROM spells
  GROUP BY IF(YEAR(start_date) BETWEEN 2012 AND 2016, 'drought 2012-2016', 'other years')
)
SELECT
  p.period_label,
  p.n_years,
  ROUND(p.mean_annual_prcp, 2) AS mean_annual_prcp_in,
  ROUND(p.driest_year_prcp, 2) AS driest_year_prcp_in,
  ROUND(p.mean_wet_days, 1) AS mean_wet_days_per_year,
  s.longest_dry_spell_days
FROM period_precip p
LEFT JOIN period_spells s ON p.period_label = s.period_label
ORDER BY period_label;
