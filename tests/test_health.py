from macropulse.api.main import health

def test_health() -> None:
    assert health() == {"status": "ok", "data_mode": "starter-no-live-data"}
