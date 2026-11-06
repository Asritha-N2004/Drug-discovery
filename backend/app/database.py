import os, re
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def now():
    return datetime.now(timezone.utc).isoformat()

def normalize_url(value):
    if value.startswith('postgres://'):return value.replace('postgres://','postgresql+psycopg://',1)
    if value.startswith('postgresql://'):return value.replace('postgresql://','postgresql+psycopg://',1)
    return value

configured_url=(os.getenv('DATABASE_URL_UNPOOLED') if os.getenv('VERCEL') else None) or os.getenv('DATABASE_URL','sqlite:///./retail.db')
DATABASE_URL = normalize_url(configured_url)
DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA','')
if DATABASE_SCHEMA and not re.fullmatch(r'[a-z_][a-z0-9_]*',DATABASE_SCHEMA):
    raise RuntimeError('DATABASE_SCHEMA must be a lowercase PostgreSQL identifier')
if os.getenv('VERCEL') and not DATABASE_URL.startswith('postgresql'):
    raise RuntimeError('Vercel deployment requires persistent PostgreSQL DATABASE_URL')
connect_args={'check_same_thread':False,'timeout':30} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, hide_parameters=True)
if DATABASE_SCHEMA and DATABASE_URL.startswith('postgresql'):
    @event.listens_for(engine,'connect')
    def set_schema(connection,_):
        # Session configuration must survive rollbacks and be applied on each connection.
        previous=connection.autocommit
        connection.autocommit=True
        with connection.cursor() as cursor:cursor.execute(f'SET search_path TO "{DATABASE_SCHEMA}"')
        connection.autocommit=previous
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure(db, _):
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with Session() as db:
        yield db
