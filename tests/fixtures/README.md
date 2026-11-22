# Test fixtures

`LCD_USW00094728_2014_sample.csv` is a small LCD v2 file for tests: 198 rows on the real
125-column header, quoted like the NOAA files.

- Real rows of New York Central Park (`LCD_USW00094728_2014.csv`) for 2014-01-01 to
  2014-01-05: 122 FM-15, 50 FM-16 and 5 SOD rows, plus the January SOM row
  (`2014-01-31T23:59:00`). The days cover a snowstorm and a cold extreme (January 3).
- 20 synthetic FM-12 rows at 03, 09, 15 and 21 local time. Central Park files have no FM-12
  rows, so these copy the FM-15 report of the hour before, in the shape FM-12 rows have at
  other stations (no altimeter, visibility or precipitation; `SOURCE` 223).
- Five values edited to carry flags that occur in other real files:
  `HourlyWindSpeed` `5.1s` and `HourlyVisibility` `16.093s`, `4.023V`, `*` on 2014-01-02
  (12:51 to 15:51), and `DailyPrecipitation` `T` on 2014-01-04.

Flags already present in the real rows: `T` (trace) in `HourlyPrecipitation` and
`DailySnowfall`, `VRB` in `HourlyWindDirection`.
