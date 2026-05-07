"""
Reset database - delete all courses, teachers, rooms, sections, timetables.
Keeps the database structure intact, just clears the data.
"""

from sqlalchemy.orm import Session
from classsync_api.database import SessionLocal
from classsync_core.models import (
    Course, Teacher, Room, Section,
    Timetable, TimetableEntry, Dataset
)


def reset_database():
    """Clear all data from main tables."""
    db = SessionLocal()

    try:
        print("🗑️  Starting database reset...")

        # Delete in correct order (respecting foreign keys)

        # 1. Timetable entries first (depends on timetables)
        count = db.query(TimetableEntry).delete()
        print(f"   ✅ Deleted {count} timetable entries")

        # 2. Timetables
        count = db.query(Timetable).delete()
        print(f"   ✅ Deleted {count} timetables")

        # 3. Sections (depends on courses)
        count = db.query(Section).delete()
        print(f"   ✅ Deleted {count} sections")

        # 4. Courses (depends on teachers)
        count = db.query(Course).delete()
        print(f"   ✅ Deleted {count} courses")

        # 5. Teachers
        count = db.query(Teacher).delete()
        print(f"   ✅ Deleted {count} teachers")

        # 6. Rooms
        count = db.query(Room).delete()
        print(f"   ✅ Deleted {count} rooms")

        # 7. Datasets (upload history)
        count = db.query(Dataset).delete()
        print(f"   ✅ Deleted {count} dataset records")

        # Commit the changes
        db.commit()
        print("\n🎉 Database reset complete!")
        print("   All courses, teachers, rooms, sections, and timetables deleted.")
        print("   Database structure intact and ready for fresh import.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during reset: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    print("   - All courses")
    print("   - All teachers")
    print("   - All rooms")
    print("   - All sections")
    print("   - All timetables")
    print("   - All upload history")

    confirm = input("\nType 'RESET' to confirm: ")

    if confirm == "RESET":
        reset_database()
    else:
        print("❌ Reset cancelled.")