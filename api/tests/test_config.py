from app.config import Settings

DUMMY = "dummy-not-a-real-key"


def test_secrets_never_appear_in_repr_or_dump():
    s = Settings(_env_file=None, meta_api_key=DUMMY, baseten_api_key=DUMMY)
    assert DUMMY not in repr(s)
    assert DUMMY not in str(s.model_dump())
    assert s.meta_api_key.get_secret_value() == DUMMY


def test_baseten_defaults_match_brief():
    s = Settings(_env_file=None)
    assert s.baseten_base_url == "https://inference.baseten.co/v1"
    assert s.baseten_model == "meta-models/muse-spark-open-1026"


def test_blank_env_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("BASETEN_BASE_URL", "")
    assert Settings(_env_file=None).baseten_base_url == "https://inference.baseten.co/v1"
