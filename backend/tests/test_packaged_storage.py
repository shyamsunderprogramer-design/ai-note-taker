from lib.storage_paths import storage_path


def test_packaged_storage_stays_outside_readonly_application(tmp_path, monkeypatch):
    application = tmp_path / "application"
    application.mkdir()
    application.chmod(0o555)
    user_data = tmp_path / "user data"
    monkeypatch.setenv("ANT_DATA_DIR", str(user_data))
    try:
        destination = storage_path(application / "modules/ai/data", "analytics")
        destination.mkdir(parents=True)
        (destination / "history.json").write_text("{}")
        assert destination == user_data / "analytics"
        assert list(application.iterdir()) == []
    finally:
        application.chmod(0o755)


def test_source_install_keeps_existing_data_location(tmp_path, monkeypatch):
    monkeypatch.delenv("ANT_DATA_DIR", raising=False)
    legacy = tmp_path / "backend/data"
    assert storage_path(legacy, "unused") == legacy
