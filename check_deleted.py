
from classsync_api.database import SessionLocal
from classsync_core.models import Course

db = SessionLocal()
total = db.query(Course).count()
active = db.query(Course).filter(Course.is_deleted == False).count()
deleted = db.query(Course).filter(Course.is_deleted == True).count()

print(f"Total Courses: {total}")
print(f"Active Courses: {active}")
print(f"Deleted Courses: {deleted}")

db.close()
