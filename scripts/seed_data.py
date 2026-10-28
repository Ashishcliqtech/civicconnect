"""Add departments, categories and clearly-labelled DEMO data:  python scripts/seed_data.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.services.seed_service import seed_demo_data

app = create_app()
with app.app_context():
    db.create_all()
    seed_demo_data()
