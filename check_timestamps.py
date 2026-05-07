
from classsync_api.database import SessionLocal
from classsync_core.models import Course
from sqlalchemy import desc

db = SessionLocal()
last_deleted = db.query(Course).filter(Course.is_deleted == True).order_by(desc(Course.deleted_at)).first()

if last_deleted:
    print(f"Last deleted course: {last_deleted.name}")
    print(f"Deleted at: {last_deleted.deleted_at}")
    print(f"Created at: {last_deleted.created_at}")
else:
    print("No deleted courses found.")

db.close()
