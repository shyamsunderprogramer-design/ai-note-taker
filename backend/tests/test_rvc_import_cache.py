"""A missing optional RVC package must not be retried for every voice request."""
import sys

from modules.voice import rvc_engine


def test_failed_optional_import_is_cached(monkeypatch, caplog):
    monkeypatch.setattr(rvc_engine, '_IMPORT_ATTEMPTED', False)
    monkeypatch.setattr(rvc_engine, '_TTS_RVC_CLASS', None)
    monkeypatch.setitem(sys.modules, 'tts_with_rvc', None)
    assert rvc_engine._get_tts_rvc_class() is None
    assert rvc_engine._get_tts_rvc_class() is None
    failures = [record for record in caplog.records
                if record.name == 'rvc_engine' and 'not available' in record.getMessage()]
    assert len(failures) == 1
