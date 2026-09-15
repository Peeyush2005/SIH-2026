"""Anonymous browser-session ownership for the optional hosted demonstration."""
import hashlib,hmac,secrets
from contextvars import ContextVar
from fastapi import HTTPException

owner = ContextVar('bluecho_owner', default=None)

class Sessions:
    def __init__(self,service):
        self.service=service
        self.key=secrets.token_bytes(32)
        with service.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS ownership(kind TEXT,id TEXT,owner TEXT,PRIMARY KEY(kind,id))')

    def sign(self,value):
        return value+'.'+hmac.new(self.key,value.encode(),hashlib.sha256).hexdigest()

    def identity(self,cookie):
        value=(cookie or '').split('.')[0]
        if len(value)==48 and hmac.compare_digest(cookie or '',self.sign(value)):
            return value
        return secrets.token_hex(24)

    def claim(self,kind,identifier):
        current=owner.get()
        if current:
            with self.service.db() as db:
                db.execute('INSERT INTO ownership VALUES(?,?,?)',(kind,identifier,current))

    def check(self,kind,identifier):
        current=owner.get()
        if current:
            with self.service.db() as db:
                row=db.execute('SELECT owner FROM ownership WHERE kind=? AND id=?',(kind,identifier)).fetchone()
            if not row or not hmac.compare_digest(row[0],current):
                raise HTTPException(404,'Resource not found in this browser session')

    def ids(self,kind):
        with self.service.db() as db:
            return [r[0] for r in db.execute('SELECT id FROM ownership WHERE kind=? AND owner=?',(kind,owner.get()))]
