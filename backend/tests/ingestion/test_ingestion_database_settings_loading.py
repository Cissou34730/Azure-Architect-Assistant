import importlib

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

import app.core.app_settings as app_settings_module


def _reload_ingestion_database():
    from backend.app.ingestion import ingestion_database

    return importlib.reload(ingestion_database)


@pytest.mark.parametrize(
    'exc',
    [
        ValidationError.from_exception_data('AppSettings', []),
        SettingsError('settings failure'),
        FileNotFoundError('missing .env'),
    ],
)
def test_ingestion_database_settings_load_failure_falls_back_to_env(monkeypatch, caplog, exc):
    caplog.set_level('WARNING')

    ingestion_db_env_value = 'relative_ingestion_test.db'
    monkeypatch.setenv('INGESTION_DATABASE', ingestion_db_env_value)

    def _raise():
        raise exc

    monkeypatch.setattr(app_settings_module, 'get_app_settings', _raise)

    ingestion_database = _reload_ingestion_database()

    assert ingestion_database.app_settings is None
    assert ingestion_db_env_value in ingestion_database.INGESTION_DB_PATH

    assert any(
        'App settings could not be loaded; falling back' in record.message
        for record in caplog.records
    )
