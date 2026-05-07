
from classsync_api.database import SessionLocal
from classsync_core.models import Course, Teacher

db = SessionLocal()
print("Checking Institution IDs...")

courses = db.query(Course.institution_id).distinct().all()
print(f"Distinct Institution IDs in Courses: {[c[0] for c in courses]}")

teachers = db.query(Teacher.institution_id).distinct().all()
print(f"Distinct Institution IDs in Teachers: {[t[0] for t in teachers]}")

db.close()
