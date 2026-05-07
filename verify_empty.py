"""
Verify database is empty.
"""

from classsync_api.database import SessionLocal
from classsync_core.models import Course, Teacher, Room, Section, Timetable

db = SessionLocal()

print("📊 Database Status:")
print(f"   Courses: {db.query(Course).count()}")
print(f"   Teachers: {db.query(Teacher).count()}")
print(f"   Rooms: {db.query(Room).count()}")
print(f"   Sections: {db.query(Section).count()}")
print(f"   Timetables: {db.query(Timetable).count()}")

if db.query(Course).count() == 0:
    print("\n✅ Database is clean and ready!")
else:
    print("\n⚠️  Database still has data!")

db.close()