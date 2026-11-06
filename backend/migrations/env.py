import os
from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from app.database import Base, normalize_url, DATABASE_SCHEMA, DATABASE_URL
from app import models

url=DATABASE_URL if os.getenv('VERCEL') else normalize_url(os.getenv('DATABASE_URL','sqlite:///./retail.db'))
if context.is_offline_mode():
    context.configure(url=url,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    with create_engine(url,poolclass=NullPool).connect() as connection:
        if DATABASE_SCHEMA and url.startswith('postgresql'):
            connection.exec_driver_sql(f'SET search_path TO "{DATABASE_SCHEMA}"')
            connection.commit()
        context.configure(connection=connection,target_metadata=Base.metadata,render_as_batch=url.startswith('sqlite'))
        with context.begin_transaction():context.run_migrations()
