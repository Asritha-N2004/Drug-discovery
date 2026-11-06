import tempfile
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

def test_frozen_migration_roundtrip(monkeypatch):
    with tempfile.TemporaryDirectory(dir=Path.cwd(),prefix='nexus-tests-migration-') as directory:
        url='sqlite:///'+(Path(directory)/'migration.db').as_posix()
        monkeypatch.setenv('DATABASE_URL',url)
        config=Config('alembic.ini')
        command.upgrade(config,'head')
        engine=create_engine(url)
        assert len(inspect(engine).get_table_names())>=20
        engine.dispose()
        command.downgrade(config,'base')
        command.upgrade(config,'head')
        engine=create_engine(url)
        assert 'inventory_allocations' in inspect(engine).get_table_names()
        engine.dispose()

def test_personal_preferences_and_settings_permissions(client,admin,analyst):
    preferences={'inventory_alerts':False,'workflow_updates':False}
    assert client.put('/api/settings/notifications',headers=analyst,json=preferences).status_code==200
    assert client.get('/api/notifications',headers=analyst).json()==[]
    assert client.get('/api/settings',headers=analyst).json()['notifications']==preferences
    assert client.get('/api/settings',headers=admin).json()['notifications']['inventory_alerts'] is True
    config=client.get('/api/settings',headers=admin).json()['optimization']
    assert client.put('/api/settings/optimization',headers=analyst,json=config).status_code==403
    assert client.put('/api/settings/optimization',headers=admin,json=config).status_code==200
    assert client.put('/api/settings/notifications',headers=analyst,json={'inventory_alerts':True,'workflow_updates':True}).status_code==200
