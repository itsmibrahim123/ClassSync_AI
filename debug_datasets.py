
import json
from classsync_api.database import SessionLocal
from classsync_core.models import Dataset
from sqlalchemy import desc

db = SessionLocal()

print("--- Recent Datasets ---")
datasets = db.query(Dataset).order_by(desc(Dataset.created_at)).limit(5).all()

if not datasets:
    print("No datasets found.")
else:
    for ds in datasets:
        print(f"ID: {ds.id}")
        print(f"Filename: {ds.filename}")
        print(f"Status: {ds.status}")
        print(f"Created At: {ds.created_at}")
        if ds.validation_errors:
            print(f"Validation Errors: {ds.validation_errors}")
        print("-" * 30)

db.close()
