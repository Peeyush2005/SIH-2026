import json
from pathlib import Path
import pytest
from PIL import Image
from bluecho.phase1.engine import RecordingEngine
from bluecho.phase1.quality import assess_quality


def test_cancelled_recording_retains_completed_windows(tmp_path,monkeypatch):
    import bluecho.phase1.engine as module
    source=tmp_path/'input.xtf';source.write_bytes(b'fixture')
    def windows(*a,**k):
        yield {'reference':{'file':'input.xtf','ping_start':10}}
        raise KeyboardInterrupt
    monkeypatch.setattr(module,'xtf_windows',windows)
    engine=RecordingEngine(tmp_path/'registry')
    monkeypatch.setattr(engine,'process_window',lambda *a,**k:{'detections':[]})
    with pytest.raises(KeyboardInterrupt):engine.predict(source,tmp_path/'out',model_ids=['fixture'],channel=0)
    report=json.loads((tmp_path/'out/recording.json').read_text())
    assert report['status']=='CANCELLED' and report['completed_windows']==1
    assert report['windows'][0]['reference']['ping_start']==10


def test_malformed_recording_is_error_not_empty(tmp_path):
    pytest.importorskip('pyxtf')
    path=tmp_path/'bad.xtf';path.write_bytes(b'not sonar')
    with pytest.raises(Exception):RecordingEngine(tmp_path/'registry').predict(path,tmp_path/'out',model_ids=['sss-pipeline-v3'],channel=0)
    report=json.loads((tmp_path/'out/recording.json').read_text())
    assert report['status']=='ERROR' and report['completed_windows']==0


def test_quality_striping_does_not_call_shadows_dropout():
    import numpy as np
    a=np.full((40,80),25,dtype='uint8');a[::2]=200
    q,_=assess_quality(Image.fromarray(a))
    assert any(x['flag']=='strong_row_striping_uncertain' for x in q['regions'])
    assert not any(x['flag']=='invalid_or_missing_rows' for x in q['regions'])
