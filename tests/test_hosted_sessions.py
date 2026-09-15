"""Hosted access isolation and quotas; fixtures are synthetic software tests."""
import io
from PIL import Image
from fastapi.testclient import TestClient
from bluecho.dashboard.service import create_app,uid


def test_hosted_browser_ownership_and_limits(tmp_path):
    app=create_app(tmp_path/'store',tmp_path/'registry',hosted=True,allowed_hosts=('demo.example',),allowed_origins=('https://demo.example',))
    image=io.BytesIO();Image.new('RGB',(20,20)).save(image,format='PNG')
    with TestClient(app,base_url='https://demo.example') as first:
        second=TestClient(app,base_url='https://demo.example')
        health=first.get('/api/v1/capabilities')
        assert health.json()['deployment']=='hosted'
        assert 'httponly' in health.headers['set-cookie'].lower()
        assert 'secure' in health.headers['set-cookie'].lower()
        source=first.post('/api/v1/sources',files={'file':('fixture.png',image.getvalue(),'image/png')}).json()
        data={'source_id':source['id'],'models':['none'],'modality':'SSS','max_pings':128}
        assert second.post('/api/v1/jobs',json=data).status_code==404
        assert first.post('/api/v1/jobs',json={**data,'max_pings':0}).status_code==422
        assert first.post('/api/v1/sources',content=b'x',headers={'content-length':str(34*1024**2)}).status_code==413
        assert first.post('/api/v1/sources',headers={'Origin':'https://evil.example'}).status_code==403
        assert first.get('/api/v1/jobs',headers={'Host':'evil.example'}).status_code==403
        service=app.state.service;job=uid()
        import json
        with service.db() as db:
            identity=service.sessions.identity(first.cookies.get('bluecho-session'))
            db.execute('INSERT INTO jobs(id,state,payload,created,message) VALUES(?,?,?,?,?)',(job,'failed',json.dumps({'source_id':source['id']}),'2026-01-01','fixture'))
            db.execute('INSERT INTO ownership VALUES(?,?,?)',('job',job,identity))
        assert len(first.get('/api/v1/jobs').json())==1
        assert second.get('/api/v1/jobs').json()==[]
        assert second.get('/api/v1/jobs/'+job).status_code==404
        assert second.get('/api/v1/jobs/'+job+'/windows/0/evidence/original.png').status_code==404
        assert second.post('/api/v1/jobs/'+job+'/cancel',json={}).status_code==404
        assert first.get('/api/v1/jobs/'+job).status_code==200
