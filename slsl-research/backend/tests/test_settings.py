from app.services.settings_service import SettingsService


def test_settings_roundtrip(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.artifacts_dir", tmp_path / "artifacts")
    svc = SettingsService(db_session)
    initial = svc.get_settings()
    assert initial["torch_threads"] == 2
    updated = svc.update_settings({"torch_threads": 3, "uncertainty_threshold": 0.3})
    assert updated["torch_threads"] == 3
    assert updated["uncertainty_threshold"] == 0.3


def test_export_metadata(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.artifacts_dir", tmp_path / "artifacts")
    data = SettingsService(db_session).export_metadata()
    assert "datasets" in data
    assert "models" in data
    assert "exported_at" in data
