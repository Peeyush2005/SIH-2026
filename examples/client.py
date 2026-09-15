"""Upload one locally held sonar image, wait, then download JSON and CSV."""
import argparse
from pathlib import Path
import time
import httpx


def main():
    p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--url',default='http://127.0.0.1:8000');p.add_argument('--output',default='client-result')
    a=p.parse_args();image=Path(a.image);out=Path(a.output);out.mkdir(exist_ok=False)
    with httpx.Client(base_url=a.url,timeout=60) as client:
        with image.open('rb') as f:
            response=client.post('/jobs',data={'modality':'SSS_LF'},files={'file':(image.name,f)})
        response.raise_for_status();job=response.json()['job_id']
        deadline=time.monotonic()+1200
        while time.monotonic()<deadline:
            response=client.get(f'/jobs/{job}');response.raise_for_status();status=response.json()
            print(status['state'],status['progress'],flush=True)
            if status['state']=='failed':raise RuntimeError(status['error'])
            if status['state']=='completed':break
            time.sleep(.5)
        else:raise TimeoutError(f'Job {job} still running; check /jobs/{job}')
        for fmt in ('json','csv'):
            response=client.get(f'/jobs/{job}/export/{fmt}');response.raise_for_status();(out/f'results.{fmt}').write_bytes(response.content)
        response=client.get(f'/jobs/{job}/evidence/annotated.png');response.raise_for_status();(out/'annotated.png').write_bytes(response.content)
        print('Saved',out.resolve())


if __name__=='__main__':main()
