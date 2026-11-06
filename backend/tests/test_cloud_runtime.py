import pytest
from app.database import normalize_url
from app.cloud import initialize_cloud_database

def test_postgresql_url_normalization():
    assert normalize_url('postgres://example/db')=='postgresql+psycopg://example/db'
    assert normalize_url('postgresql://example/db')=='postgresql+psycopg://example/db'
    assert normalize_url('sqlite:///demo.db')=='sqlite:///demo.db'

def test_cloud_initializer_is_disabled_locally(monkeypatch):
    monkeypatch.delenv('VERCEL',raising=False)
    assert initialize_cloud_database() is None

def test_serverless_workflow_finishes_in_request(client,admin,monkeypatch):
    monkeypatch.setenv('VERCEL','1')
    response=client.post('/api/optimization/run',headers=admin,json={'method':'greedy','run_name':'Serverless request lifetime test'})
    assert response.status_code==202,response.text
    assert response.json()['status']=='waiting_for_approval'
    run_id=response.json()['id']
    assert client.post(f'/api/optimization/runs/{run_id}/reject',headers=admin).status_code==200
    assert client.get('/health').json()['event_transport']=='database polling'
