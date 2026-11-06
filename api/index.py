"""Vercel Python function entry point; persistence is supplied by PostgreSQL."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.cloud import initialize_cloud_database
initialize_cloud_database()
from app.main import app
