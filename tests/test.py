import unittest
import sqlite3
import os
from ORM import model, datatypes


DB_PATH = "databases/main.sqlite3"

class Student(model.BaseModel):
    full_name = datatypes.CharField()
    degree = datatypes.CharField()

class Course(model.BaseModel):
    name = datatypes.CharField()
        
class TestCreateTable(unittest.TestCase):
    """
    A test case class to verify the creation and schema of the 'student' table in the SQLite database.

    This class contains methods to test the following:
    1. Whether the 'student' table exists in the database after creation.
    2. Whether the schema of the 'student' table matches the expected schema, including column names and data types.
    3. Whether the table is correctly populated with initial data entries.

    The `setUpClass` method is used to initialize the database and create the 'student' table before any tests are run.
    The `tearDownClass` method is used to clean up the database after all tests have been executed.

    Methods:
    - `test_table_exists`: Verifies that the 'student' table exists in the database.
    - `test_table_schema`: Verifies that the schema of the 'student' table matches the expected schema.
    - `test_populate_schema`: Verifies that the table is correctly populated with the expected initial data entries.
    """
    @classmethod
    def setUpClass(cls):
        """Set up the database and create the table before running tests."""
        if not os.path.exists('databases'):
            os.makedirs('databases')
        Student.create_table()

        Student.insert_entries([
            {"full_name": "Yehor Boiar", "degree": "Computer Science"},
            {"full_name": "Anastasia Martison", "degree": "Computer Science"}
        ])


    def test_table_exists(self):
        """Test if the table was created in the database."""
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists, "Table 'student' was not created.")

        connection.close()

    def test_table_schema(self):
        """Test if the table schema matches the expected schema."""
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        # Check the schema of the table
        cursor.execute("PRAGMA table_info(student);")
        columns = cursor.fetchall()

        # Expected schema
        expected_columns = [
            (0, 'id', 'INTEGER', 1, None, 1),  # Primary key
            (1, 'full_name', 'TEXT', 0, None, 0),
            (2, 'degree', 'TEXT', 0, None, 0)
        ]
        self.assertEqual(columns, expected_columns, "Table schema does not match expected schema.")

        connection.close()

    def test_populate_schema(self):
        connection = sqlite3.connect(DB_PATH)

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM student")

        students = cursor.fetchall()
        expected_entries = [(1, 'Yehor Boiar', 'Computer Science'), (2, 'Anastasia Martison', 'Computer Science')]

        self.assertEqual(students, expected_entries, "Table schema does not match expected schema.")

        connection.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

class TestConnectionsTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the database and create the table before running tests."""
        if not os.path.exists('databases'):
            os.makedirs('databases')
        Student.create_table()

        Student.insert_entries([
            {"full_name": "Yehor Boiar", "degree": "Computer Science"},
            {"full_name": "Anastasia Martison", "degree": "Computer Science"}
        ])

    def test_many_to_many_connections(self):
        """Test M2M relationship join table creation and queries."""

        Student.create_table()
        Course.create_table()
        
        
        Course.insert_entries([{"name": "Math"}])
        student = Student.objects.get(name="Yehor Boiar")
        
        
        # Verify join table exists and has entries
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%student_courses%'")
            self.assertTrue(cursor.fetchone())


if __name__ == '__main__':
    unittest.main() 