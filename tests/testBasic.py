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
        """Set up the database and create the table once before all tests."""
        if not os.path.exists('databases'):
            os.makedirs('databases')
        # Only create the table here
        Student.create_table()

    def setUp(self):
        """Insert fresh data and reset sequence before each test."""
        # Clear any data from previous tests first
        Student.delete_entries({}, confirm=True)

        # Reset the auto-increment sequence for the student table
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        try:
            # This command resets the counter for the specified table
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?;", (Student.__name__.lower(),))
            connection.commit()
        except sqlite3.OperationalError as e:
            # Handle case where sqlite_sequence table might not exist yet (e.g., first run)
            # or if the table wasn't using AUTOINCREMENT (though it should be)
            print(f"Info: Could not reset sequence for {Student.__name__.lower()} - {e}")
            connection.rollback() # Rollback any potential transaction state change
        finally:
            connection.close()

        # Insert the standard test data - IDs should now start from 1
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
        # This test now verifies the data inserted by setUp
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, degree FROM student ORDER BY id") # Order by ID for consistency
        students = cursor.fetchall()
        # Adjust expected IDs if delete/insert changes auto-increment behavior across tests
        # Assuming fresh inserts start from 1 each time due to delete_entries in setUp
        expected_entries = [(1, 'Yehor Boiar', 'Computer Science'), (2, 'Anastasia Martison', 'Computer Science')]
        self.assertEqual(students, expected_entries, "Data inserted in setUp does not match expected.")
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
    
    def test_insert_model_instances(self):
        """Test inserting data using BaseModel instances."""
        # setUp already ran and inserted data, but this test needs a clean slate
        # So, the delete here is still useful.
        Student.delete_entries({}, confirm=True)

        # Create model instances
        student1 = Student(name="Instance User1", degree="Physics")
        student2 = Student(name="Instance User2", degree="Chemistry")

        # Insert using model instances
        Student.insert_entries([student1, student2])

        # Verify insertion
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute("SELECT name, degree FROM student ORDER BY name")
        students = cursor.fetchall()
        connection.close()

        expected_entries = [
            ('Instance User1', 'Physics'),
            ('Instance User2', 'Chemistry')
        ]
        self.assertEqual(students, expected_entries, "Inserting model instances failed.")

    def test_insert_mixed_types_raises_error(self):
        """Test that inserting a mix of dicts and instances raises TypeError."""
        # setUp inserted data, delete it for this specific test scenario
        Student.delete_entries({}, confirm=True) # Clean slate
        student_instance = Student(name="Test Instance", degree="Biology")
        student_dict = {"name": "Test Dict", "degree": "Geology"}

        with self.assertRaisesRegex(TypeError, "All entries must be dictionaries."):
             # The error message depends on which type is first in the list
             # If dict is first, it expects all dicts.
            Student.insert_entries([student_dict, student_instance])

        with self.assertRaisesRegex(TypeError, "All entries must be BaseModel instances."):
             # If instance is first, it expects all instances.
            Student.insert_entries([student_instance, student_dict])

    def test_insert_wrong_instance_type_raises_error(self):
        """Test that inserting instances of a different model raises TypeError."""
        # Define another simple model for testing purposes
        class Course(base.BaseModel):
            title = datatypes.CharField()
        # Ensure Course table exists if it doesn't (idempotent)
        Course.create_table()

        # setUp inserted Student data, delete it for this specific test scenario
        Student.delete_entries({}, confirm=True) # Clean slate for Student table
        wrong_instance = Course(title="Introduction to Testing")
        student_instance = Student(name="Correct Student", degree="Testing")

        with self.assertRaisesRegex(TypeError, f"All entries must be instances of {Student.__name__}"):
            Student.insert_entries([student_instance, wrong_instance])

        # Clean up the Course table (optional, but good practice)
        if os.path.exists(DB_PATH):
            connection = sqlite3.connect(DB_PATH)
            cursor = connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS course")
            connection.commit()
            connection.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()