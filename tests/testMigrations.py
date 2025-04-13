import unittest
import os
import shutil
from pathlib import Path
from ORM.models import find_models, generate_migrations, apply_migrations
from ORM.model import BaseModel
from ORM.datatypes import CharField

# Temporary test directory for models
TEST_APP_DIR = "test_app"


class TestModelDiscovery(unittest.TestCase):
    """
    Test case for discovering models in a specified directory.
    This test case creates a temporary directory with a test model
    and verifies that the model is correctly discovered by the find_models function.
    """
    @classmethod
    def setUpClass(cls):
        """Set up a temporary app directory with test models."""
        if not os.path.exists(TEST_APP_DIR):
            os.makedirs(TEST_APP_DIR)

        # Create a test model file
        with open(os.path.join(TEST_APP_DIR, "test_model.py"), "w") as f:
            f.write("""
from ORM.model import BaseModel
from ORM.datatypes import CharField

class TestModel(BaseModel):
    name = CharField()
""")

    def test_find_models(self):
        """Test that find_models correctly identifies models inheriting from BaseModel."""
        project_root = os.getcwd()
        models = find_models(project_root, models_folder=TEST_APP_DIR)
        self.assertEqual(
            len(models), 1, "find_models should discover one model.")
        self.assertEqual(models[0].__name__, "TestModel",
                         "The discovered model should be 'TestModel'.")

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary app directory."""
        if os.path.exists(TEST_APP_DIR):
            shutil.rmtree(TEST_APP_DIR)


class TestMigrationGeneration(unittest.TestCase):
    def setUp(self):
        """Set up a temporary migrations directory."""
        self.migrations_dir = Path("migrations")
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)
        self.migrations_dir.mkdir()

    def test_generate_migrations(self):
        """Test that generate_migrations creates a valid migration file."""
        class TestModel(BaseModel):
            name = CharField()

        # First migration should be generated
        generate_migrations([TestModel])

        # Find the generated migration file (should have format like 0001_migration_*.py)
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 1,
                         "One migration file should be created")

        migration_file = migration_files[0]
        self.assertTrue(migration_file.exists(),
                        "Migration file should be created.")

        with open(migration_file, "r") as f:
            content = f.read()
            self.assertIn("def migrate():", content,
                          "Migration file should contain a migrate function.")
            self.assertIn("TestModel.create_table()", content,
                          "Migration file should include table creation for TestModel.")

        # Capture the files before the second generation attempt
        files_before = set(self.migrations_dir.glob("*.py"))

        # Running again with the same model should NOT generate a new migration
        generate_migrations([TestModel])

        # Verify no new migrations were created
        files_after = set(self.migrations_dir.glob("*.py"))
        self.assertEqual(files_before, files_after,
                         "No new migration should be generated when models haven't changed")

        # Now, modify the model
        class TestModel(BaseModel):
            name = CharField()
            description = CharField()  # Added field

        # This should generate a new migration
        generate_migrations([TestModel])

        # There should now be two migration files
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 2,
                         "A second migration should be created when models change")

    def tearDown(self):
        """Clean up the migrations directory."""
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)


class TestMigrationApplication(unittest.TestCase):
    def setUp(self):
        """Set up a temporary migrations directory and database."""
        self.migrations_dir = Path("migrations")
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)
        self.migrations_dir.mkdir()

        # Create a migration file
        migration_file = self.migrations_dir / "0001_initial_migration.py"
        with open(migration_file, "w") as f:
            f.write("""
from ORM.model import BaseModel
from ORM.datatypes import CharField

class TestModel(BaseModel):
    name = CharField()

def migrate():
    TestModel.create_table()
""")

    def test_apply_migrations(self):
        """Test that apply_migrations successfully applies migrations and tracks them."""
        # Apply the migration for the first time
        apply_migrations()

        # Verify that the table was created
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()

        # Check the model table was created
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(
            table_exists, "The 'testmodel' table should be created.")

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

        # Create a second migration file to test sequential application
        second_migration = self.migrations_dir / "0002_second_migration.py"
        with open(second_migration, "w") as f:
            f.write("""
from ORM.model import BaseModel
from ORM.datatypes import CharField

class SecondModel(BaseModel):
    title = CharField()

def migrate():
    SecondModel.create_table()
""")

        # Apply migrations again - first should be skipped, second should be applied
        apply_migrations()

        # Verify both tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='secondmodel';")
        second_table_exists = cursor.fetchone()
        self.assertIsNotNone(second_table_exists,
                             "The 'secondmodel' table should be created.")

        # Verify both migrations are recorded
        cursor.execute(
            "SELECT migration_name FROM orm_migrations ORDER BY id;")
        recorded_migrations = cursor.fetchall()
        self.assertEqual(len(recorded_migrations), 2,
                         "Two migrations should be recorded")
        self.assertEqual(recorded_migrations[0][0], "0001_initial_migration")
        self.assertEqual(recorded_migrations[1][0], "0002_second_migration")

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
