from psx_ingest.worker import celery_app


def test_celery_app_is_configured() -> None:
    assert celery_app.main == "psx_ingest"
    assert celery_app.conf.timezone == "Asia/Karachi"
    assert celery_app.conf.enable_utc is True


def test_beat_schedule_contains_eod_task() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "ingest-eod-ohlcv" in schedule
    assert schedule["ingest-eod-ohlcv"]["task"] == "psx_ingest.tasks.ohlcv.ingest_eod_ohlcv"


def test_beat_schedule_contains_corporate_actions() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "ingest-corporate-actions-morning" in schedule
    assert "ingest-corporate-actions-evening" in schedule
