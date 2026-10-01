"""Session refresh: live re-validation, preserved sign-in time, absolute lifetime cap."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
pytest.importorskip('sqlalchemy'); pytest.importorskip('argon2'); pytest.importorskip('jwt'); pytest.importorskip('httpx')
import jwt
from fastapi.testclient import TestClient
from workspace.models import Database, Base, Organization, User, Membership
from workspace.identity import PASSWORDS, PERMISSIONS, MAX_SESSION_SECONDS, signing_secret

SECRET = 'x' * 64

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('WORKSPACE_SIGNING_SECRET', SECRET)
    monkeypatch.setenv('WORKSPACE_DEMO_MODE', 'false')
    db = Database('sqlite:///' + str(tmp_path / 'w.db'), testing=True)
    Base.metadata.create_all(db.engine)
    with db.transaction() as s:
        org = Organization(name='Co'); user = User(email='a@example.test', password_hash=PASSWORDS.hash('correct horse battery'))
        s.add_all([org, user]); s.flush()
        s.add(Membership(organization_id=org.id, user_id=user.id, permissions=sorted(PERMISSIONS), groups=[]))
        ids = (org.id, user.id)
    from workspace.api import create_app
    with TestClient(create_app(db)) as c:
        c.ids = ids; c.db = db
        yield c
    db.engine.dispose()

def login(c):
    r = c.post('/api/session/login', json={'email': 'a@example.test', 'password': 'correct horse battery'})
    assert r.status_code == 200, r.text
    return r.json()['access_token']

def auth(t): return {'Authorization': 'Bearer ' + t}

def test_refresh_issues_new_token_and_keeps_original_signin_time(client):
    t1 = login(client)
    time.sleep(1.1)
    r = client.post('/api/session/refresh', headers=auth(t1))
    assert r.status_code == 200, r.text
    body = r.json(); t2 = body['access_token']
    c1 = jwt.decode(t1, SECRET, algorithms=['HS256'], audience='png5-workspace', issuer='png5-local')
    c2 = jwt.decode(t2, SECRET, algorithms=['HS256'], audience='png5-workspace', issuer='png5-local')
    assert c2['auth'] == c1['auth'] and c2['iat'] > c1['iat'] and c2['exp'] > c1['exp']
    assert body['session_ends_at'] == c1['auth'] + MAX_SESSION_SECONDS
    assert client.get('/api/session', headers=auth(t2)).status_code == 200

def test_refresh_cannot_extend_past_absolute_cap(client):
    org, user = client.ids
    old = int(time.time()) - MAX_SESSION_SECONDS - 5
    stale = jwt.encode({'sub': user, 'org': org, 'iat': int(time.time()), 'auth': old, 'exp': int(time.time()) + 600,
                        'iss': 'png5-local', 'aud': 'png5-workspace'}, SECRET, algorithm='HS256')
    assert client.get('/api/session', headers=auth(stale)).status_code == 401
    assert client.post('/api/session/refresh', headers=auth(stale)).status_code == 401

def test_token_exp_is_clamped_to_cap(client):
    from workspace.identity import token_for
    org, user = client.ids
    near_end = int(time.time()) - MAX_SESSION_SECONDS + 60
    claims = jwt.decode(token_for(user, org, near_end), SECRET, algorithms=['HS256'], audience='png5-workspace', issuer='png5-local')
    assert claims['exp'] == near_end + MAX_SESSION_SECONDS

def test_refresh_fails_after_membership_revoked(client):
    t = login(client)
    with client.db.transaction() as s:
        s.query(Membership).update({'active': False})
    assert client.post('/api/session/refresh', headers=auth(t)).status_code == 401

def test_refresh_requires_authentication_and_rejects_forged_tokens(client):
    assert client.post('/api/session/refresh').status_code == 401
    forged = jwt.encode({'sub': client.ids[1], 'org': client.ids[0], 'iat': int(time.time()), 'exp': int(time.time()) + 600,
                         'iss': 'png5-local', 'aud': 'png5-workspace'}, 'y' * 64, algorithm='HS256')
    assert client.post('/api/session/refresh', headers=auth(forged)).status_code == 401
