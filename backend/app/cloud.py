"""Idempotent PostgreSQL bootstrap for an authenticated cloud deployment.

Initialization uses runtime-provided secrets without reading them back from
Vercel. An advisory lock coordinates simultaneous cold starts.
"""
import os
from pathlib import Path
from sqlalchemy import text
from .database import engine,Session,DATABASE_SCHEMA

def initialize_cloud_database():
    if not os.getenv('VERCEL') or os.getenv('CLOUD_INITIALIZE')!='true':return
    if not DATABASE_SCHEMA:raise RuntimeError('Cloud initialization requires an isolated DATABASE_SCHEMA')
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(hashtext(:key))"),{'key':DATABASE_SCHEMA+'_bootstrap'})
        try:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"'))
            connection.commit()
            from alembic.config import Config
            from alembic import command
            backend=Path(__file__).resolve().parents[1]
            config=Config(str(backend/'alembic.ini'))
            config.set_main_option('script_location',str(backend/'migrations'))
            command.upgrade(config,'head')
            from .seed import seed
            with Session() as db:seed(db)
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"),{'key':DATABASE_SCHEMA+'_bootstrap'})
            connection.commit()
