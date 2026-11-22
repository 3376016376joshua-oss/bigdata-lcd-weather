from lcdweather.timing.inputs import measure_inputs, parse_du_output, raw_globs
from lcdweather.timing.plan import YearWindow


def _write_raw(root, station, year, data_rows):
    folder = root / station
    folder.mkdir(exist_ok=True)
    lines = ['"STATION","DATE"'] + [
        f'"{station}","{year}-01-01T00:{i:02d}"' for i in range(data_rows)
    ]
    path = folder / f"LCD_{station}_{year}.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_raw_globs_follow_the_raw_zone_layout():
    globs = raw_globs("hdfs:///user/x/lcd/raw/", YearWindow(2024, 2025))

    assert globs == [
        "hdfs:///user/x/lcd/raw/*/LCD_*_2024.csv",
        "hdfs:///user/x/lcd/raw/*/LCD_*_2025.csv",
    ]


def test_local_stats_count_only_files_of_the_window(tmp_path):
    kept = [
        _write_raw(tmp_path, "USW00000001", 2025, data_rows=3),
        _write_raw(tmp_path, "USW00000002", 2025, data_rows=5),
        _write_raw(tmp_path, "USW00000001", 2024, data_rows=2),
    ]
    _write_raw(tmp_path, "USW00000001", 2023, data_rows=7)

    stats = measure_inputs(str(tmp_path), YearWindow(2024, 2025))

    assert stats.files == 3
    assert stats.bytes == sum(path.stat().st_size for path in kept)
    assert stats.rows == 3 + 5 + 2


def test_file_uri_raw_root_is_read_from_the_local_path(tmp_path):
    path = _write_raw(tmp_path, "USW00000001", 2025, data_rows=4)

    stats = measure_inputs(f"file://{tmp_path}", YearWindow(2025, 2025))

    assert (stats.files, stats.bytes, stats.rows) == (1, path.stat().st_size, 4)


def test_row_count_can_be_skipped(tmp_path):
    _write_raw(tmp_path, "USW00000001", 2025, data_rows=3)

    stats = measure_inputs(str(tmp_path), YearWindow(2025, 2025), count_rows=False)

    assert stats.files == 1
    assert stats.rows is None


def test_parse_du_output_reads_the_size_column():
    output = (
        "1048576  3145728  hdfs:///user/x/lcd/raw/A/LCD_A_2025.csv\n"
        "2048  hdfs:///user/x/lcd/raw/B/LCD_B_2025.csv\n"
        "\n"
    )

    assert parse_du_output(output) == [1048576, 2048]
