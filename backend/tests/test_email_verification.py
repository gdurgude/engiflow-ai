import sqlite3
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from app import main as m
from app import main as core, auth


def test_verified_registration_flow(tmp_path, monkeypatch):
    temp_db = tmp_path / 'verify.db'
    with sqlite3.connect(core.DB) as src, sqlite3.connect(temp_db) as dest:
        src.backup(dest)
    monkeypatch.setattr(core, 'DB', temp_db)
    codes = []
    monkeypatch.setattr(auth, 'send_verification', lambda email, code: codes.append((email,code)))
    c = TestClient(m.app)
    email = f'new-{uuid4().hex}@example.org'
    password = 'super-safe-123'
    result = c.post('/auth/signup', json={'name':'Sample User','email':email,'password':password})
    assert result.status_code == 201 and result.json()['verification_required']
    assert 'engiflow_session' not in result.cookies
    assert c.get('/projects').status_code == 401
    assert c.post('/auth/login',json={'email':email,'password':password}).status_code == 403
    bad = c.post('/auth/verify-email',json={'email':email,'code':'000000' if codes[0][1]!='000000' else '999999'})
    assert bad.status_code == 400
    good = c.post('/auth/verify-email',json={'email':email,'code':codes[0][1]})
    assert good.status_code == 200
    assert c.get('/projects').status_code == 200
    assert c.post('/auth/login',json={'email':email,'password':'wrong-password'}).status_code == 401
    assert c.post('/auth/login',json={'email':email,'password':password}).status_code == 200
    assert c.post('/auth/verify-email',json={'email':email,'code':codes[0][1]}).status_code == 400


def test_expired_code_rejected(tmp_path,monkeypatch):
    temp_db=tmp_path / 'expired.db'
    with sqlite3.connect(core.DB) as src, sqlite3.connect(temp_db) as dest: src.backup(dest)
    monkeypatch.setattr(core,'DB',temp_db)
    codes=[]
    monkeypatch.setattr(auth,'send_verification',lambda email,code: codes.append(code))
    c=TestClient(m.app)
    email=f'expire-{uuid4().hex}@example.org'
    assert c.post('/auth/signup',json={'name':'Test','email':email,'password':'safe-password-123'}).status_code==201
    with sqlite3.connect(temp_db) as conn:
        conn.execute('UPDATE email_verifications SET expires_at=?',(int(time.time())-1,))
    assert c.post('/auth/verify-email',json={'email':email,'code':codes[0]}).status_code==400
