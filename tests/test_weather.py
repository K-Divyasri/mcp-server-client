from mcp_kb import weather


def test_offline_known_city():
    result = weather.get_weather("Paris", live=False)
    assert "Paris" in result
    assert "offline demo data" in result


def test_offline_is_case_insensitive():
    result = weather.get_weather("PARIS", live=False)
    assert "clear sky" in result


def test_offline_unknown_city_is_honest():
    result = weather.get_weather("Atlantis", live=False)
    assert "No offline weather data" in result
    assert "Atlantis" in result


def test_live_flag_defaults_from_env(monkeypatch):
    monkeypatch.delenv("MCP_KB_LIVE_WEATHER", raising=False)
    # live=None reads the env var; with it unset, behaves like live=False
    result = weather.get_weather("Paris")
    assert "offline demo data" in result


def test_live_env_var_enables_live_path(monkeypatch):
    monkeypatch.setenv("MCP_KB_LIVE_WEATHER", "1")
    calls = {}

    def fake_fetch(city):
        calls["city"] = city
        return f"{city}: fake live result"

    monkeypatch.setattr(weather, "_fetch_live", fake_fetch)
    result = weather.get_weather("Berlin")
    assert calls["city"] == "Berlin"
    assert result == "Berlin: fake live result"


def test_live_fetch_failure_falls_back_to_offline(monkeypatch):
    monkeypatch.setattr(weather, "_fetch_live", lambda city: None)
    result = weather.get_weather("Paris", live=True)
    assert "offline demo data" in result


def test_describe_code_known_and_unknown():
    assert weather._describe_code(0) == "clear sky"
    assert "weather code 999" == weather._describe_code(999)
