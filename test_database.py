"""
Test database operations and models.
"""

from sqlalchemy.orm import Session
from classsync_api.database import SessionLocal, engine
from classsync_core.models import (
    Institution, User, Room, Teacher, Course, Section,
    UserRole, SubscriptionTier, RoomType, CourseType
)
from datetime import datetime, timedelta


def test_create_institution():
    """Test creating an institution."""
    db: Session = SessionLocal()

    try:
        # Create test institution
        institution = Institution(
            name="Test University",
            code="TEST_UNIV",
            email="admin@testuniv.edu",
            phone="+1234567890",
            address="123 Test Street, Test City",
            subscription_tier=SubscriptionTier.FREE_TRIAL,
            subscription_expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )

        db.add(institution)
        db.commit()
        db.refresh(institution)

        print(f"Institution created: {institution.name} (ID: {institution.id})")
        return institution.id

    except Exception as e:
        print(f"Error creating institution: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_create_user(institution_id: int):
    """Test creating a user."""
    db: Session = SessionLocal()

    try:
        user = User(
            institution_id=institution_id,
            email="admin@testuniv.edu",
            hashed_password="$2b$12$dummy_hashed_password",  # In real app, use proper hashing
            full_name="Test Admin",
            role=UserRole.ADMIN,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"User created: {user.full_name} ({user.email})")
        return user.id

    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_create_room(institution_id: int):
    """Test creating a room."""
    db: Session = SessionLocal()

    try:
        room = Room(
            institution_id=institution_id,
            code="LH-101",
            name="Lecture Hall 101",
            room_type=RoomType.LECTURE_HALL,
            capacity=100,
            building="Main Building",
            floor="1",
            is_available=True
        )

        db.add(room)
        db.commit()
        db.refresh(room)

        print(f"Room created: {room.name} (Code: {room.code})")
        return room.id

    except Exception as e:
        print(f"Error creating room: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_create_teacher(institution_id: int):
    """Test creating a teacher."""
    db: Session = SessionLocal()

    try:
        teacher = Teacher(
            institution_id=institution_id,
            code="T001",
            name="Dr. John Smith",
            email="john.smith@testuniv.edu",
            department="Computer Science",
            time_preferences={"avoid_early": True, "prefer_afternoon": False}
        )

        db.add(teacher)
        db.commit()
        db.refresh(teacher)

        print(f"Teacher created: {teacher.name} (Code: {teacher.code})")
        return teacher.id

    except Exception as e:
        print(f"Error creating teacher: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_create_course(institution_id: int, teacher_id: int):
    """Test creating a course."""
    db: Session = SessionLocal()

    try:
        course = Course(
            institution_id=institution_id,
            teacher_id=teacher_id,
            code="CS101",
            name="Introduction to Programming",
            course_type=CourseType.LECTURE,
            credit_hours=3,
            duration_minutes=90,
            sessions_per_week=2
        )

        db.add(course)
        db.commit()
        db.refresh(course)

        print(f"Course created: {course.name} (Code: {course.code})")
        return course.id

    except Exception as e:
        print(f"Error creating course: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_create_section(institution_id: int, course_id: int):
    """Test creating a section."""
    db: Session = SessionLocal()

    try:
        section = Section(
            institution_id=institution_id,
            course_id=course_id,
            code="CS101-A",
            name="Section A",
            semester="Fall",
            year=2024,
            student_count=45
        )

        db.add(section)
        db.commit()
        db.refresh(section)

        print(f"Section created: {section.code} ({section.student_count} students)")
        return section.id

    except Exception as e:
        print(f"Error creating section: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_query_data():
    """Test querying data with relationships."""
    db: Session = SessionLocal()

    try:
        # Query institution with all related data
        institution = db.query(Institution).filter(Institution.code == "TEST_UNIV").first()

        if institution:
            print(f"\nInstitution: {institution.name}")
            print(f"   Users: {len(institution.users)}")
            print(f"   Rooms: {len(institution.rooms)}")
            print(f"   Teachers: {len(institution.teachers)}")
            print(f"   Courses: {len(institution.courses)}")
            print(f"   Sections: {len(institution.sections)}")

            # Query course with teacher relationship
            if institution.courses:
                course = institution.courses[0]
                print(f"\nCourse: {course.name}")
                print(f"   Teacher: {course.teacher.name}")
                print(f"   Duration: {course.duration_minutes} minutes")
                print(f"   Sessions/week: {course.sessions_per_week}")

    except Exception as e:
        print(f"Error querying data: {e}")
    finally:
        db.close()


def run_all_tests():
    """Run all database tests."""
    print("=" * 60)
    print("Testing ClassSync AI Database Models")
    print("=" * 60)
    print()

    # Create test data
    institution_id = test_create_institution()
    if not institution_id:
        print("\nFailed to create institution. Stopping tests.")
        return

    user_id = test_create_user(institution_id)
    room_id = test_create_room(institution_id)
    teacher_id = test_create_teacher(institution_id)

    if teacher_id:
        course_id = test_create_course(institution_id, teacher_id)
        if course_id:
            section_id = test_create_section(institution_id, course_id)

    # Query and display relationships
    print()
    test_query_data()

    print()
    print("=" * 60)
    print("All database tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()