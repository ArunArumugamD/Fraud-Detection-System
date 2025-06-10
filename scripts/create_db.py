import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def create_database():
    """
    Create the database if it doesn't exist
    """
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database="postgres"  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (settings.DB_NAME,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute(f"CREATE DATABASE {settings.DB_NAME}")
            print(f"Database '{settings.DB_NAME}' created successfully!")
        else:
            print(f"Database '{settings.DB_NAME}' already exists.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_database()