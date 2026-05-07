"""Test database connection"""
import psycopg2
from classsync_api.config import settings

try:
    # Connect to database
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()

    # Execute test query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()

    print("Database connection successful!")
    print(f"PostgreSQL version: {version[0]}")

    cursor.close()
    conn.close()

except Exception as e:
    print("Database connection failed!")
    print(f"Error: {e}")