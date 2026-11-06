import os, tempfile
from pathlib import Path
import pytest

tmp=tempfile.TemporaryDirectory(prefix='nexus-tests-',dir=Path(__file__).resolve().parents[1])
os.environ['DATABASE_URL']='sqlite:///'+(Path(tmp.name)/'test.db').as_posix()
os.environ['JWT_SECRET']='test-only-secret-with-at-least-32-characters'
from app.database import Base, engine, Session
from app.seed import seed
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope='session')
def client():
    Base.metadata.create_all(engine)
    with Session() as db:seed(db)
    with TestClient(app) as c:yield c
    engine.dispose()

@pytest.fixture(scope='session')
def admin(client):
    r=client.post('/api/auth/login',json={'email':'admin@retail.local','password':'RetailDemo!2026'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}

@pytest.fixture(scope='session')
def analyst(client):
    r=client.post('/api/auth/login',json={'email':'analyst@retail.local','password':'RetailDemo!2026'})
    return {'Authorization':'Bearer '+r.json()['access_token']}
