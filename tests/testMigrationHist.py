import unittest
import os
import shutil
from pathlib import Path


class TestMigrationHistory(unittest.TestCase):
    def setUp(self):
        """Set up temporary migrations directory and database."""
        self.migrations_dir = Path("migrations")
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)
        self.migrations_dir.mkdir()

        # Create a migration file
        migration_file = self.migrations_dir / "0001_initial_migration.py"
        with open(migration_file, "w") as f:
            f.write("""
from ORM.base import BaseModel
from ORM.datatypes import CharField

class TestModel(BaseModel):
    name = CharField()

def migrate():
    TestModel.create_table()
""")

    def test_migration_tracking(self):
        """Test that migrations are properly tracked once applied."""
        from ORM.manager import apply_migrations, get_applied_migrations

        # Apply the migration
        apply_migrations()

        # Check that migration is recorded as applied
        applied = get_applied_migrations()
        self.assertIn("0001_initial_migration", applied,
                      "Migration should be recorded in tracking table")

        # Reapplying migrations should not error and should skip already applied ones
        apply_migrations()  # This should run without errors

        # Verify table exists in database
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()

        # Check the model table was created
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(
            table_exists, "The model table should be created.")

        # Check the migrations table was created
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='orm_migrations';")
        migrations_table_exists = cursor.fetchone()
        self.assertIsNotNone(migrations_table_exists,
                             "The migrations tracking table should be created.")

        # Check the migration is recorded in the table
        cursor.execute("SELECT migration_name FROM orm_migrations;")
        recorded_migrations = cursor.fetchall()
        self.assertEqual(len(recorded_migrations), 1,
                         "One migration should be recorded")
        self.assertEqual(recorded_migrations[0][0], "0001_initial_migration",
                         "The correct migration name should be recorded")

        connection.close()

    def tearDown(self):
        """Clean up the migrations directory and database."""
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)
        if os.path.exists("databases/main.sqlite3"):
            os.remove("databases/main.sqlite3")
        if os.path.exists("databases"):
            os.rmdir("databases")


if __name__ == "__main__":
    unittest.main()