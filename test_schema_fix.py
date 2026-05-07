
from classsync_api.schemas import CourseDataRow
from pydantic import ValidationError

print("--- Testing Schema Fixes ---")

# Test 0 hours
try:
    row = CourseDataRow(
        course_name="Test",
        program="CS",
        type="Theory",
        hours_per_week=0,
        # missing section
        # missing instructor
    )
    print("✅ Validation PASSED for 0 hours and missing section/instructor")
except ValidationError as e:
    print(f"❌ Validation FAILED: {e}")

