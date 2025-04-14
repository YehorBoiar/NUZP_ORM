import unittest
import os
import shutil
from pathlib import Path
from ORM.manager import find_models, generate_migrations, apply_migrations
from ORM.base import BaseModel
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
from ORM.base import BaseModel
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
    """
    TestMigrationGeneration is a test suite for verifying the behavior of the migration generation system.
    It ensures that migrations are generated correctly based on model changes, handles edge cases, and validates
    expected outcomes.

    Test cases included:
        1. `test_generate_migrations`:
           Verifies that migrations are generated correctly for new models and that no duplicate migrations
           are created when models remain unchanged.
        2. `test_field_modification`:
           Ensures that modifying field attributes (e.g., nullability) generates a new migration.
        3. `test_removing_field`:
           Tests that removing a field from a model generates a new migration.
        4. `test_multiple_models`:
           Verifies that migrations can handle multiple models and that changes to one model generate a new migration.
        5. `test_consecutive_changes`:
           Tests the behavior of consecutive changes to the same model, ensuring each change generates a new migration.
        6. `test_empty_models_list`:
           Ensures that no migrations are generated when the models list is empty.
        7. `test_unchanged_migration_signature`:
           Verifies that non-model-changing updates (e.g., comments) do not trigger a new migration.

    Each test case sets up a controlled environment, generates migrations, and verifies the expected migration files
    and their contents.
    """

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

    def test_field_modification(self):
        """Test that changing field attributes generates a new migration."""
        class TestModel(BaseModel):
            name = CharField(null=False)

        # Generate initial migration
        generate_migrations([TestModel])
        initial_migrations = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(initial_migrations), 1)

        # Modify field attribute
        class TestModel(BaseModel):
            name = CharField(null=True)  # Changed null attribute

        # Generate another migration
        generate_migrations([TestModel])

        # Should have a new migration
        updated_migrations = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(updated_migrations), 2,
                         "Changing field attributes should create a new migration")

    def test_removing_field(self):
        """Test that removing a field generates a new migration."""
        class TestModel(BaseModel):
            name = CharField()
            age = CharField()

        # Generate initial migration
        generate_migrations([TestModel])

        # Remove a field
        class TestModel(BaseModel):
            name = CharField()  # age field removed

        # Generate another migration
        generate_migrations([TestModel])

        # Should have a new migration
        migrations = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migrations), 2,
                         "Removing a field should create a new migration")

    def test_multiple_models(self):
        """Test handling multiple models at once."""
        class FirstModel(BaseModel):
            title = CharField()

        class SecondModel(BaseModel):
            name = CharField()

        # Generate migration with two models
        generate_migrations([FirstModel, SecondModel])

        # Check that one migration file is created
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 1)

        # Check both models are in the migration
        with open(migration_files[0], "r") as f:
            content = f.read()
            self.assertIn("FirstModel.create_table()", content)
            self.assertIn("SecondModel.create_table()", content)

        # Change only one model
        class FirstModel(BaseModel):
            title = CharField()
            content = CharField()  # Added field

        class SecondModel(BaseModel):
            name = CharField()  # Unchanged

        # Generate a new migration
        generate_migrations([FirstModel, SecondModel])

        # Should have a new migration
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 2,
                         "Changing one model should create a new migration")

    def test_consecutive_changes(self):
        """Test multiple consecutive changes to the same model."""
        class TestModel(BaseModel):
            name = CharField()

        # Initial migration
        generate_migrations([TestModel])

        # First change - add a field
        class TestModel(BaseModel):
            name = CharField()
            description = CharField()

        generate_migrations([TestModel])

        # Second change - add another field
        class TestModel(BaseModel):
            name = CharField()
            description = CharField()
            created_at = CharField()

        generate_migrations([TestModel])

        # Third change - remove a field
        class TestModel(BaseModel):
            name = CharField()
            created_at = CharField()  # description removed

        generate_migrations([TestModel])

        # Should have four migrations total
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 4,
                         "Each model change should create a new migration")

    def test_empty_models_list(self):
        """Test behavior with an empty models list."""
        # Generate with empty list
        generate_migrations([])

        # Should not create any migrations
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 0,
                         "No migrations should be created for empty models list")

    def test_unchanged_migration_signature(self):
        """Test that adding a non-model changing comment doesn't trigger a migration."""
        # Define a model with a comment
        class TestModel(BaseModel):
            name = CharField()
            # This is a comment that doesn't affect the model

        # Generate initial migration
        generate_migrations([TestModel])

        # Update the comment only
        class TestModel(BaseModel):
            name = CharField()
            # This is a different comment that still doesn't affect the model

        # This shouldn't generate a new migration
        generate_migrations([TestModel])

        # Should still have only one migration
        migration_files = list(self.migrations_dir.glob("????_*.py"))
        self.assertEqual(len(migration_files), 1,
                         "Comments and whitespace shouldn't trigger new migrations")

    def tearDown(self):
        """Clean up the migrations directory."""
        if self.migrations_dir.exists():
            shutil.rmtree(self.migrations_dir)

class TestMigrationApplication(unittest.TestCase):
    """
    TestMigrationApplication is a test suite for verifying the behavior of a database migration system. 
    It ensures that migrations are applied correctly, handles edge cases, and validates expected outcomes.
    
    Test cases included:
        1. `test_apply_migrations`: 
           Verifies that migrations are applied successfully and the corresponding database tables are created.
        2. `test_empty_migrations_directory`: 
           Tests the behavior when the migrations directory is empty, ensuring no errors occur.
        3. `test_failed_migration`: 
           Ensures that failed migrations are handled gracefully and are not recorded in the database.
        4. `test_duplicate_application`: 
           Confirms that applying migrations multiple times does not result in duplicate entries or errors.
        5. `test_out_of_order_migrations`: 
           Tests that migrations are applied in the correct numerical order, even if the files are out of order.
        6. `test_migration_with_dependencies`: 
           Verifies that migrations with dependencies on previous migrations are applied correctly.
        7. `test_non_existent_migrations_dir`: 
           Ensures that the system handles the absence of a migrations directory gracefully.
        8. `test_apply_specific_migration`: 
           Tests the ability to apply a specific migration by name without affecting other migrations.
    
    Each test case sets up a controlled environment, applies migrations, and verifies the expected database state or behavior.
    """

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
from ORM.base import BaseModel
from ORM.datatypes import CharField

class TestModel(BaseModel):
    name = CharField()

def migrate():
    TestModel.create_table()
""")

    def test_apply_migrations(self):
        """Test that apply_migrations successfully applies migrations."""
        apply_migrations()

        # Verify that the table was created
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(
            table_exists, "The 'testmodel' table should be created.")
        connection.close()

    def test_empty_migrations_directory(self):
        """Test behavior when migrations directory is empty."""
        # Remove any migration files
        for file in self.migrations_dir.glob("*.py"):
            os.remove(file)

        # Apply migrations with empty directory
        apply_migrations()

        # This should not error and should simply report no migrations to apply
        # We just verify that the function returns without error

    def test_failed_migration(self):
        """Test handling of a failed migration."""
        # Create a migration file with an error
        bad_migration = self.migrations_dir / "0002_bad_migration.py"
        with open(bad_migration, "w") as f:
            f.write("""
def migrate():
    # This will raise a NameError
    undefined_variable + 1
""")

        # Apply migrations
        with self.assertRaises(Exception):
            apply_migrations()

        # Check that no record of the bad migration exists
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()
        cursor.execute("SELECT migration_name FROM orm_migrations;")
        recorded_migrations = [row[0] for row in cursor.fetchall()]
        self.assertNotIn("0002_bad_migration", recorded_migrations,
                         "Failed migrations should not be recorded")
        connection.close()

    def test_duplicate_application(self):
        """Test that applying migrations multiple times is safe."""
        # First application
        apply_migrations()

        # Second application should skip already applied migrations
        apply_migrations()

        # Third application still shouldn't error
        apply_migrations()

        # Check that the migration is only recorded once
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()
        cursor.execute(
            "SELECT migration_name, COUNT(*) FROM orm_migrations GROUP BY migration_name;")
        counts = cursor.fetchall()
        for migration, count in counts:
            self.assertEqual(
                count, 1, f"Migration {migration} should only be recorded once")
        connection.close()

    def test_out_of_order_migrations(self):
        """Test behavior with out-of-order migration files."""
        # Create migrations out of numerical order
        third_migration = self.migrations_dir / "0003_third_migration.py"
        with open(third_migration, "w") as f:
            f.write("""
from ORM.base import BaseModel
from ORM.datatypes import CharField

class ThirdModel(BaseModel):
    content = CharField()

def migrate():
    ThirdModel.create_table()
""")

        # Apply migrations - they should be applied in numerical order
        apply_migrations()

        # Verify tables exist in expected order
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()

        # Check all tables were created
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        self.assertIsNotNone(
            cursor.fetchone(), "First migration table should be created")

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='thirdmodel';")
        self.assertIsNotNone(
            cursor.fetchone(), "Third migration table should be created")

        # Check order in which migrations were applied
        cursor.execute(
            "SELECT migration_name FROM orm_migrations ORDER BY id;")
        migration_order = [row[0] for row in cursor.fetchall()]
        self.assertEqual(migration_order[0], "0001_initial_migration",
                         "First migration should be applied first")
        self.assertEqual(migration_order[1], "0003_third_migration",
                         "Third migration should be applied next")

        connection.close()

    def test_migration_with_dependencies(self):
        """Test migrations that depend on previous migrations."""
        # Create a migration that depends on a previous migration
        second_migration = self.migrations_dir / "0002_dependent_migration.py"
        with open(second_migration, "w") as f:
            f.write("""
from ORM.base import BaseModel
from ORM.datatypes import CharField

class TestModel(BaseModel):
    # This model is defined in the first migration
    # We're adding a method that depends on the table existing
    pass

def migrate():
    # This migration only works if TestModel table already exists
    import sqlite3
    connection = sqlite3.connect("databases/main.sqlite3")
    cursor = connection.cursor()
    cursor.execute("ALTER TABLE testmodel ADD COLUMN description TEXT;")
    connection.commit()
    connection.close()
""")

        # Apply migrations
        apply_migrations()

        # Check that the column was added
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(testmodel);")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("description", columns,
                      "The dependent migration should add a column")
        connection.close()

    def test_non_existent_migrations_dir(self):
        """Test behavior when migrations directory doesn't exist."""
        # Remove migrations directory
        shutil.rmtree(self.migrations_dir)

        # Apply migrations should handle this gracefully
        apply_migrations()
        # We just verify that no exception is raised

    def test_apply_specific_migration(self):
        """Test applying a specific migration by name."""
        # Create a second migration
        second_migration = self.migrations_dir / "0002_second_migration.py"
        with open(second_migration, "w") as f:
            f.write("""
from ORM.base import BaseModel
from ORM.datatypes import CharField

class SecondModel(BaseModel):
    title = CharField()

def migrate():
    SecondModel.create_table()
""")

        # Apply only the second migration directly
        apply_migrations(specific_migration="0002_second_migration")

        # Verify only the second model table exists
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='secondmodel';")
        self.assertIsNotNone(
            cursor.fetchone(), "Second model table should be created")

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        self.assertIsNone(cursor.fetchone(),
                          "First model table should not be created")

        # Check that only the specific migration is recorded
        cursor.execute("SELECT migration_name FROM orm_migrations;")
        recorded_migrations = [row[0] for row in cursor.fetchall()]
        self.assertEqual(len(recorded_migrations), 1,
                         "Only one migration should be recorded")
        self.assertEqual(recorded_migrations[0], "0002_second_migration",
                         "The specific migration should be recorded")

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
