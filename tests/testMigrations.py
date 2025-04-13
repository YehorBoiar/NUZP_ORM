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
        self.assertEqual(len(models), 1, "find_models should discover one model.")
        self.assertEqual(models[0].__name__, "TestModel", "The discovered model should be 'TestModel'.")

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

        generate_migrations([TestModel])
        migration_file = self.migrations_dir / "migration.py"
        self.assertTrue(migration_file.exists(), "Migration file should be created.")
        
        with open(migration_file, "r") as f:
            content = f.read()
            self.assertIn("def migrate():", content, "Migration file should contain a migrate function.")
            self.assertIn("TestModel.create_table()", content, "Migration file should include table creation for TestModel.")

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
        migration_file = self.migrations_dir / "migration.py"
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
        """Test that apply_migrations successfully applies migrations."""
        apply_migrations()
        # Verify that the table was created
        import sqlite3
        connection = sqlite3.connect("databases/main.sqlite3")
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='testmodel';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists, "The 'testmodel' table should be created.")
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