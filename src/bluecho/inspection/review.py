"""Transactional review events; immutable source/prediction and frozen split gate."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime,timezone
from pathlib import Path


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

class ReviewQueue:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, source TEXT NOT NULL, source_group TEXT NOT NULL, original TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, item TEXT NOT NULL REFERENCES items(id), payload TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_items BEFORE UPDATE ON items BEGIN SELECT RAISE(ABORT,'immutable original'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_events BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable review'); END;
        CREATE TRIGGER IF NOT EXISTS no_delete_items BEFORE DELETE ON items BEGIN SELECT RAISE(ABORT,'immutable original'); END;
        CREATE TRIGGER IF NOT EXISTS no_delete_events BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable review'); END;''')
        self.db.execute('PRAGMA foreign_keys=ON')
    def close(self):self.db.close()
    def add(self,item,source_group):
        source=item['source_sha256'];identifier=item['candidate_id'];raw=canonical(item)
        if len(source)!=64 or not source_group:raise ValueError('Source hash and related-recording group required')
        existing=self.db.execute('SELECT source,source_group,original FROM items WHERE id=?',(identifier,)).fetchone()
        if existing and existing!=(source,source_group,raw):raise ValueError('Immutable prediction/source conflict')
        with self.db:self.db.execute('INSERT OR IGNORE INTO items VALUES(?,?,?,?)',(identifier,source,source_group,raw))
    def annotate(self,identifier,*,action,reviewer=None,label=None,box=None,timestamp=None,annotation_version=1):
        original=self.db.execute('SELECT original FROM items WHERE id=?',(identifier,)).fetchone()
        if not original:raise ValueError('Unknown review item')
        if action not in ('confirmed','corrected','false_alert','missed_object','clear_region'):raise ValueError('Unknown review action')
        if type(annotation_version)!=int or annotation_version<1:raise ValueError('Invalid annotation version')
        if action in ('confirmed','corrected','missed_object') and not isinstance(label,str):raise ValueError('Reviewed label required')
        if action in ('corrected','missed_object') and box is None:raise ValueError('Corrected box required')
        if box is not None:
            if len(box)!=4 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in box) or not 0<=box[0]<box[2] or not 0<=box[1]<box[3]:raise ValueError('Invalid review box')
            dimensions=json.loads(original[0]).get('image_dimensions')
            if dimensions and (box[2]>dimensions['width'] or box[3]>dimensions['height']):raise ValueError('Review box outside image')
        stamp=timestamp or datetime.now(timezone.utc).isoformat()
        if datetime.fromisoformat(stamp.replace('Z','+00:00')).tzinfo is None:raise ValueError('Timezone required')
        event={'item':identifier,'action':action,'reviewer':reviewer,'label':label,'box_xyxy_pixels':box,'timestamp':stamp,'annotation_version':annotation_version}
        key=hashlib.sha256(canonical(event).encode()).hexdigest()
        with self.db:self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(key,identifier,canonical(event)))
        return {'event_id':key,**event}
    def export(self):
        return {'schema_version':'1.0','items':[{'source_group':g,'original_prediction':json.loads(p)} for g,p in self.db.execute('SELECT source_group,original FROM items ORDER BY id')],'events':[{'event_id':k,**json.loads(p)} for k,p in self.db.execute('SELECT id,payload FROM events ORDER BY rowid')]}
    def import_bundle(self,bundle):
        if bundle.get('schema_version')!='1.0':raise ValueError('Unsupported review schema')
        # Validate in an isolated database first; no partial import on invalid events.
        check=ReviewQueue(':memory:')
        try:
            for row in bundle['items']:check.add(row['original_prediction'],row['source_group'])
            for event in bundle['events']:
                v=dict(event);expected=v.pop('event_id');identifier=v.pop('item');v['box']=v.pop('box_xyxy_pixels')
                actual=check.annotate(identifier,**v)
                if actual['event_id']!=expected:raise ValueError('Review event checksum mismatch')
            with self.db:
                for identifier,source,group,original in check.db.execute('SELECT * FROM items'):
                    old=self.db.execute('SELECT source,source_group,original FROM items WHERE id=?',(identifier,)).fetchone()
                    if old and old!=(source,group,original):raise ValueError('Immutable prediction/source conflict')
                    self.db.execute('INSERT OR IGNORE INTO items VALUES(?,?,?,?)',(identifier,source,group,original))
                self.db.executemany('INSERT OR IGNORE INTO events VALUES(?,?,?)',check.db.execute('SELECT * FROM events').fetchall())
        finally:check.close()
    def development_manifest(self,frozen):
        """Explicit allowlist plus frozen heldout hashes AND related recording groups."""
        held_hash=set(frozen['heldout_source_sha256']);held_group=set(frozen['heldout_source_groups']);allowed=set(frozen['development_source_groups']);rows=[];excluded=[]
        for identifier,source,group,original in self.db.execute('SELECT * FROM items'):
            events=[json.loads(v[0]) for v in self.db.execute('SELECT payload FROM events WHERE item=? ORDER BY rowid',(identifier,))]
            if not events:continue
            if source in held_hash or group in held_group or group not in allowed:excluded.append({'candidate_id':identifier,'reason':'HELDOUT_OR_UNAPPROVED_GROUP'});continue
            if events[-1]['action']=='clear_region':continue
            rows.append({'source_sha256':source,'source_group':group,'original_prediction':json.loads(original),'review':events[-1]})
        return {'schema_version':'1.0','purpose':'development_only_no_training_started','frozen_manifest_sha256':hashlib.sha256(canonical(frozen).encode()).hexdigest(),'examples':rows,'excluded':excluded}
