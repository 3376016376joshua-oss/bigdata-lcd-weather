import unittest

from lcdweather import units


class UnitConversionTest(unittest.TestCase):
    def test_temperature(self):
        self.assertAlmostEqual(units.c_to_f(0.0), 32.0)
        self.assertAlmostEqual(units.c_to_f(100.0), 212.0)
        self.assertAlmostEqual(units.c_to_f(-40.0), -40.0)
        self.assertAlmostEqual(units.c_to_f(-3.9), 24.98)

    def test_temperature_difference_has_no_offset(self):
        self.assertAlmostEqual(units.delta_c_to_f(0.0), 0.0)
        self.assertAlmostEqual(units.delta_c_to_f(-11.76), -21.168)
        self.assertAlmostEqual(units.delta_c_to_f(20.1), 36.18)

    def test_precipitation(self):
        self.assertAlmostEqual(units.mm_to_in(25.4), 1.0)
        self.assertAlmostEqual(units.mm_to_in(8.4), 0.3307, places=4)

    def test_pressure(self):
        self.assertAlmostEqual(units.hpa_to_inhg(1013.25), 29.9213, places=4)

    def test_wind_speed(self):
        self.assertAlmostEqual(units.ms_to_mph(1.0), 2.23694, places=5)
        # 3 knots in the METAR is stored as 1.5 m/s.
        self.assertAlmostEqual(units.ms_to_mph(1.5), 3.3554, places=4)

    def test_visibility(self):
        self.assertAlmostEqual(units.km_to_mi(16.093), 10.0, places=3)

    def test_missing_value_stays_missing(self):
        conversions = (
            units.c_to_f,
            units.delta_c_to_f,
            units.mm_to_in,
            units.hpa_to_inhg,
            units.ms_to_mph,
            units.km_to_mi,
        )
        for convert in conversions:
            with self.subTest(convert=convert.__name__):
                self.assertIsNone(convert(None))


if __name__ == "__main__":
    unittest.main()
