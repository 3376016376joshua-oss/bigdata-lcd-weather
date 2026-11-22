-- Q5: longest dry spells per city, found with a gaps and islands window query.
-- A dry day has less than 0.01 in of precipitation (trace counts as dry). Within
-- one city, consecutive dry days share the same value of
-- obs_date minus row_number, so that value identifies each run (island) of dry
-- days. A wet day or a day missing from the data ends the run.
-- The five longest spells of every city are returned.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q5_dry_spells.sql
WITH dry_days AS (
  SELECT
    city_code,
    city,
    obs_date,
    DATE_SUB(
      obs_date,
      CAST(ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY obs_date) AS INT)
    ) AS island_key
  FROM ${hivevar:db}.lcd_daily
  WHERE prcp_in < 0.01
),
spells AS (
  SELECT
    city_code,
    MAX(city) AS city,
    MIN(obs_date) AS start_date,
    MAX(obs_date) AS end_date,
    COUNT(*) AS length_days
  FROM dry_days
  GROUP BY city_code, island_key
),
ranked AS (
  SELECT
    city_code,
    city,
    start_date,
    end_date,
    length_days,
    ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY length_days DESC, start_date)
      AS spell_rank
  FROM spells
)
SELECT
  city_code,
  city,
  spell_rank,
  CAST(start_date AS STRING) AS start_date,
  CAST(end_date AS STRING) AS end_date,
  length_days
FROM ranked
WHERE spell_rank <= 5
ORDER BY city_code, spell_rank;
