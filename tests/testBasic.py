import sys
import os
import unittest
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes

DB_PATH = "databases/main.sqlite3"

class Student(base.BaseModel):
    name = datatypes.CharField()
    degree = datatypes.CharField()

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
            {"name": "Yehor Boiar", "degree": "Computer Science"},
            {"name": "Anastasia Martison", "degree": "Computer Science"}
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
            (1, 'name', 'TEXT', 0, None, 0),
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

    def test_slicing(self):
        self.assertEqual({'id': 1, 'name': 'Yehor Boiar', 'degree': 'Computer Science'}, Student.objects[0], "First entry of students table doesn't match the slice")
        
        self.assertEqual([
            {'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"},
            {'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"}
        ], Student.objects[:2], "First entry of students table doesn't match the slice")
    
    def test_iter(self):
        iter_objects = [
            {'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"},
            {'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"}
        ]
        for i,j in enumerate(Student.objects.__iter__()):
            self.assertEqual(iter_objects[i], j)

    def test_all(self):
        expected = [
            {'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"},
            {'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"}
        ]
        self.assertEqual(Student.objects.all(), expected, "All() did not return expected results")

    def test_filter(self):
        expected = [{'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"}]
        result = Student.objects.filter(name="Yehor Boiar").all()
        self.assertEqual(result, expected, "Filter() did not return expected results")

    def test_get(self):
        expected = {'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"}
        result = Student.objects.get(id=2)
        self.assertEqual(result, expected, "Get() did not return the correct record")

    def test_get_no_match(self):
        with self.assertRaises(Exception) as context:
            Student.objects.get(id=999)  # No such ID
        self.assertIn("DoesNotExist", str(context.exception))

    def test_get_multiple_results(self):
        with self.assertRaises(Exception) as context:
            Student.objects.get(degree="Computer Science")  # Multiple students have this degree
        self.assertIn("MultipleObjectsReturned", str(context.exception))

    def test_order_by(self):
        expected = [
            {'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"},
            {'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"}
        ]
        result = Student.objects.order_by("-id").all()
        self.assertEqual(result, expected, "Order_by() did not sort results correctly")

    def test_limit(self):
        expected = [{'id': 1, "name": "Yehor Boiar", "degree": "Computer Science"}]
        result = Student.objects.limit(1).all()
        self.assertEqual(result, expected, "Limit() did not return correct number of records")

    def test_offset(self):
        expected = [{'id': 2, "name": "Anastasia Martison", "degree": "Computer Science"}]
        result = Student.objects.offset(1).all()
        self.assertEqual(result, expected, "Offset() did not return expected result")

    def test_chained_operations(self):
        result = Student.objects.filter(degree="Computer Science").order_by("-id").limit(1).offset(1).all()
        expected = [{'id': 1, 'name': 'Yehor Boiar', 'degree': 'Computer Science'}]
        self.assertEqual(result, expected)
    
    def test_complex_filter(self):
        # Test multiple WHERE conditions
        result = Student.objects.filter(degree="Computer Science", name__like="Y%").all()
        expected = [{'id': 1, 'name': 'Yehor Boiar', 'degree': 'Computer Science'}]
        self.assertEqual(result, expected)
        
    def test_limit_zero(self):
        result = Student.objects.limit(0).all()
        self.assertEqual(result, [])

    def test_large_offset(self):
        result = Student.objects.offset(100).all()
        self.assertEqual(result, [])
    
    def test_sql_injection_safety(self):
        """
        Test that SQL injection attempts are safely handled.
        """
        # Attempt to inject SQL via a field value
        results = Student.objects.filter(name__exact="'; DROP TABLE student; --").all()
        self.assertEqual(len(results), 0)  # Ensure no results are returned

        # Attempt to inject SQL via a field name
        with self.assertRaises(ValueError):
            Student.objects.filter(**{"invalid_field; DROP TABLE student; --": "value"}).all()

        # Attempt to use an invalid lookup operator
        with self.assertRaises(ValueError):
            Student.objects.filter(name__invalid_lookup="value").all()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main() 