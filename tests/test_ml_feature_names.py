from lcdweather.ml.feature_names import clean_feature_name, feature_names


def test_clean_feature_name_restores_original_column_names():
    assert clean_feature_name("tmax_f__imputed") == "tmax_f"
    assert clean_feature_name("city_code__onehot_KSEA") == "city_code=KSEA"


def test_feature_names_orders_attributes_by_vector_index():
    metadata = {
        "ml_attr": {
            "attrs": {
                "binary": [{"idx": 2, "name": "city_code__onehot_KSEA"}],
                "numeric": [
                    {"idx": 1, "name": "dep_f__imputed"},
                    {"idx": 0, "name": "tmax_f__imputed"},
                ],
            },
            "num_attrs": 3,
        }
    }

    assert feature_names(metadata, 3) == ["tmax_f", "dep_f", "city_code=KSEA"]


def test_feature_names_falls_back_to_positions_without_metadata():
    assert feature_names({}, 2) == ["feature_0", "feature_1"]
