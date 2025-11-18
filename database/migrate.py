#!/usr/bin/env python3
"""
Database Migration Script for AudioBookSync
This script initializes the PostgreSQL database schema
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handles database migration and schema setup"""

    def __init__(self, host='localhost', port=5432, database='audiobooksync',
                 user='postgres', password=None):
        """
        Initialize database connection parameters

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password or os.getenv('POSTGRES_PASSWORD', 'postgres')
        self.conn = None
        self.cursor = None

    def connect(self, database='postgres'):
        """Connect to PostgreSQL server"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=database,
                user=self.user,
                password=self.password
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to PostgreSQL server (database: {database})")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from PostgreSQL")

    def database_exists(self):
        """Check if the target database exists"""
        try:
            self.cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database,)
            )
            exists = self.cursor.fetchone() is not None
            return exists
        except psycopg2.Error as e:
            logger.error(f"Error checking database existence: {e}")
            return False

    def create_database(self):
        """Create the AudioBookSync database"""
        if self.database_exists():
            logger.info(f"Database '{self.database}' already exists")
            return True

        try:
            self.cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(self.database)
                )
            )
            logger.info(f"Database '{self.database}' created successfully")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to create database: {e}")
            return False

    def drop_database(self, confirm=False):
        """
        Drop the AudioBookSync database (use with caution!)

        Args:
            confirm: Must be True to actually drop the database
        """
        if not confirm:
            logger.warning("Database drop not confirmed. Skipping.")
            return False

        if not self.database_exists():
            logger.info(f"Database '{self.database}' does not exist")
            return True

        try:
            # Terminate existing connections
            self.cursor.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{self.database}'
                AND pid <> pg_backend_pid();
            """)

            self.cursor.execute(
                sql.SQL("DROP DATABASE {}").format(
                    sql.Identifier(self.database)
                )
            )
            logger.info(f"Database '{self.database}' dropped successfully")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to drop database: {e}")
            return False

    def run_sql_file(self, filepath):
        """
        Execute SQL commands from a file

        Args:
            filepath: Path to SQL file
        """
        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"SQL file not found: {filepath}")
            return False

        try:
            with open(filepath, 'r') as f:
                sql_commands = f.read()

            # Split by semicolons, but this is simplistic
            # For complex SQL files, consider using psycopg2's execute with the whole file
            self.cursor.execute(sql_commands)
            logger.info(f"Successfully executed SQL file: {filepath.name}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error executing SQL file {filepath.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def migrate(self, fresh=False):
        """
        Run the full migration process

        Args:
            fresh: If True, drops and recreates the database
        """
        logger.info("Starting database migration...")

        # Connect to postgres database
        if not self.connect(database='postgres'):
            return False

        # Handle fresh migration
        if fresh:
            logger.warning("Fresh migration requested - dropping existing database")
            self.drop_database(confirm=True)

        # Create database
        if not self.create_database():
            self.disconnect()
            return False

        # Disconnect and reconnect to the new database
        self.disconnect()
        if not self.connect(database=self.database):
            return False

        # Get the directory where this script is located
        script_dir = Path(__file__).parent

        # Run schema.sql
        schema_file = script_dir / 'schema.sql'
        if not self.run_sql_file(schema_file):
            logger.error("Failed to run schema.sql")
            self.disconnect()
            return False

        logger.info("Database migration completed successfully!")
        self.disconnect()
        return True

    def verify_schema(self):
        """Verify that all tables were created successfully"""
        if not self.connect(database=self.database):
            return False

        expected_tables = [
            'users', 'books', 'download_status', 'decryption_status',
            'sync_history', 'genres', 'book_genres', 'error_log',
            'user_config', 'notifications'
        ]

        try:
            self.cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)

            existing_tables = [row[0] for row in self.cursor.fetchall()]

            logger.info("Existing tables:")
            for table in existing_tables:
                logger.info(f"  ✓ {table}")

            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False

            logger.info("Schema verification passed!")
            return True

        except psycopg2.Error as e:
            logger.error(f"Error verifying schema: {e}")
            return False
        finally:
            self.disconnect()


def main():
    """Main entry point for the migration script"""
    import argparse

    parser = argparse.ArgumentParser(
        description='AudioBookSync Database Migration Tool'
    )
    parser.add_argument(
        '--host',
        default=os.getenv('POSTGRES_HOST', 'localhost'),
        help='PostgreSQL host (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('POSTGRES_PORT', 5432)),
        help='PostgreSQL port (default: 5432)'
    )
    parser.add_argument(
        '--database',
        default=os.getenv('POSTGRES_DB', 'audiobooksync'),
        help='Database name (default: audiobooksync)'
    )
    parser.add_argument(
        '--user',
        default=os.getenv('POSTGRES_USER', 'postgres'),
        help='PostgreSQL user (default: postgres)'
    )
    parser.add_argument(
        '--password',
        default=os.getenv('POSTGRES_PASSWORD'),
        help='PostgreSQL password (can also use POSTGRES_PASSWORD env var)'
    )
    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Drop and recreate database (WARNING: destroys all data!)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Only verify schema, do not run migration'
    )

    args = parser.parse_args()

    # Create migration instance
    migration = DatabaseMigration(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password
    )

    # Run verification only
    if args.verify:
        success = migration.verify_schema()
        sys.exit(0 if success else 1)

    # Confirm fresh migration
    if args.fresh:
        confirmation = input(
            f"WARNING: This will delete all data in '{args.database}'. "
            "Type 'yes' to confirm: "
        )
        if confirmation.lower() != 'yes':
            logger.info("Migration cancelled")
            sys.exit(0)

    # Run migration
    success = migration.migrate(fresh=args.fresh)

    if success:
        logger.info("Running schema verification...")
        migration.verify_schema()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
