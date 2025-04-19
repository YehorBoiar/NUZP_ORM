import sys
import os
import unittest
import sqlite3
from unittest.mock import patch, MagicMock # Add mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes
from ORM.fields import ForeignKey # Add ForeignKey

DB_PATH = "databases/main.sqlite3"

# Add a simple related model for FK tests
class Department(base.BaseModel):
    name = datatypes.CharField()

class Student(base.BaseModel):
    name = datatypes.CharField(unique=True) # Add unique constraint for testing errors
    degree = datatypes.CharField(null=False) # Add NOT NULL constraint for testing errors
    department = ForeignKey(to=Department, null=True) # Add FK for testing

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
        # Create tables for all models used in this test file
        Department.create_table()
        Student.create_table()

    def setUp(self):
        """Insert fresh data and reset sequence before each test."""
        # Delete from all tables used
        Student.delete_entries({}, confirm=True)
        Department.delete_entries({}, confirm=True)

        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        try:
            # Reset sequences for all tables
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN (?, ?);",
                           (Student.__name__.lower(), Department.__name__.lower()))
            connection.commit()
        except sqlite3.OperationalError as e:
            print(f"Info: Could not reset sequences - {e}")
            connection.rollback()
        finally:
            connection.close()

        # Insert base data
        self.dept1 = Department(name="Science")
        Department.insert_entries([self.dept1])

        self.student1 = Student(name="Yehor Boiar", degree="Computer Science", department=self.dept1)
        self.student2 = Student(name="Anastasia Martison", degree="Computer Science", department=self.dept1)
        Student.insert_entries([self.student1, self.student2]) # Insert instances

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
            (2, 'degree', 'TEXT', 1, None, 0),
            (3, 'department_id', 'INTEGER', 0, None, 0)
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
        # Fetch instances
        student0 = Student.objects[0]
        students_slice = Student.objects[:2]

        # Assert instance attributes for single slice item
        self.assertIsInstance(student0, Student)
        self.assertEqual(student0.id, 1)
        self.assertEqual(student0.name, 'Yehor Boiar')
        self.assertEqual(student0.degree, 'Computer Science')

        # Assert instance attributes for slice range
        self.assertEqual(len(students_slice), 2)
        self.assertIsInstance(students_slice[0], Student)
        self.assertIsInstance(students_slice[1], Student)
        self.assertEqual(students_slice[0].id, 1)
        self.assertEqual(students_slice[1].id, 2)
        self.assertEqual(students_slice[0].name, 'Yehor Boiar')
        self.assertEqual(students_slice[1].name, 'Anastasia Martison')

    def test_iter(self):
        # Expected instances (or check attributes)
        expected_students = [self.student1, self.student2]
        fetched_students = list(Student.objects.__iter__()) # Collect iterator results

        self.assertEqual(len(fetched_students), len(expected_students))
        # Sort by ID for consistent comparison if order isn't guaranteed by default iteration
        fetched_students.sort(key=lambda s: s.id)
        expected_students.sort(key=lambda s: s.id)

        for i, fetched in enumerate(fetched_students):
            self.assertIsInstance(fetched, Student)
            self.assertEqual(fetched.id, expected_students[i].id)
            self.assertEqual(fetched.name, expected_students[i].name)
            self.assertEqual(fetched.degree, expected_students[i].degree)

    def test_all(self):
        # Expected instances
        expected_students = [self.student1, self.student2]
        all_students = Student.objects.all()

        self.assertEqual(len(all_students), len(expected_students))
        # Sort by ID for consistent comparison if order isn't guaranteed
        all_students.sort(key=lambda s: s.id)
        expected_students.sort(key=lambda s: s.id)

        for i, fetched in enumerate(all_students):
            self.assertIsInstance(fetched, Student)
            self.assertEqual(fetched.id, expected_students[i].id)
            self.assertEqual(fetched.name, expected_students[i].name)
            self.assertEqual(fetched.degree, expected_students[i].degree)

    def test_filter(self):
        # Expected instance(s)
        expected_student = self.student1
        result = Student.objects.filter(name="Yehor Boiar").all()

        self.assertEqual(len(result), 1, "Filter should return one result")
        self.assertIsInstance(result[0], Student)
        self.assertEqual(result[0].id, expected_student.id)
        self.assertEqual(result[0].name, expected_student.name)
        self.assertEqual(result[0].degree, expected_student.degree)

    def test_get(self):
        # Expected instance
        expected_student = self.student2
        result = Student.objects.get(id=2)

        self.assertIsInstance(result, Student)
        self.assertEqual(result.id, expected_student.id)
        self.assertEqual(result.name, expected_student.name)
        self.assertEqual(result.degree, expected_student.degree)

    def test_get_no_match(self):
        with self.assertRaises(Exception) as context:
            Student.objects.get(id=999)  # No such ID
        self.assertIn("DoesNotExist", str(context.exception))

    def test_get_multiple_results(self):
        with self.assertRaises(Exception) as context:
            Student.objects.get(degree="Computer Science")  # Multiple students have this degree
        self.assertIn("MultipleObjectsReturned", str(context.exception))

    def test_order_by(self):
        # Expected instances in specific order
        expected_students_ordered = [self.student2, self.student1] # Ordered by -id
        result = Student.objects.order_by("-id").all()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Student)
        self.assertIsInstance(result[1], Student)
        self.assertEqual(result[0].id, expected_students_ordered[0].id)
        self.assertEqual(result[1].id, expected_students_ordered[1].id)
        self.assertEqual(result[0].name, expected_students_ordered[0].name)
        self.assertEqual(result[1].name, expected_students_ordered[1].name)

    def test_limit(self):
        # Expected instance
        expected_student = self.student1
        result = Student.objects.limit(1).all() # Should get student with id 1 by default ordering

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Student)
        self.assertEqual(result[0].id, expected_student.id)
        self.assertEqual(result[0].name, expected_student.name)

    def test_offset(self):
        # Expected instance
        expected_student = self.student2
        result = Student.objects.offset(1).all() # Skip student 1, get student 2

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Student)
        self.assertEqual(result[0].id, expected_student.id)
        self.assertEqual(result[0].name, expected_student.name)

    def test_chained_operations(self):
        # Expected instance
        expected_student = self.student1
        # Filter, Order by -id (student2, student1), limit 1 (student2), offset 1 (student1)
        result = Student.objects.filter(degree="Computer Science").order_by("-id").limit(1).offset(1).all()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Student)
        self.assertEqual(result[0].id, expected_student.id)
        self.assertEqual(result[0].name, expected_student.name)

    def test_complex_filter(self):
        # Expected instance
        expected_student = self.student1
        result = Student.objects.filter(degree="Computer Science", name__like="Y%").all()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Student)
        self.assertEqual(result[0].id, expected_student.id)
        self.assertEqual(result[0].name, expected_student.name)
        
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
        """Test inserting data using BaseModel instances and ID update."""
        Student.delete_entries({}, confirm=True)

        student1 = Student(name="Instance User1", degree="Physics")
        student2 = Student(name="Instance User2", degree="Chemistry")
        self.assertIsNone(student1.id) # ID should be None before insert
        self.assertIsNone(student2.id)

        Student.insert_entries([student1, student2])

        # Verify IDs were updated on instances
        self.assertIsNotNone(student1.id)
        self.assertIsNotNone(student2.id)
        self.assertIsInstance(student1.id, int)
        self.assertIsInstance(student2.id, int)

        # Verify insertion in DB by fetching instances
        fetched1 = Student.objects.get(id=student1.id)
        fetched2 = Student.objects.get(id=student2.id)
        self.assertIsInstance(fetched1, Student)
        self.assertIsInstance(fetched2, Student)
        self.assertEqual(fetched1.name, "Instance User1")
        self.assertEqual(fetched2.name, "Instance User2")
        self.assertEqual(fetched1.degree, "Physics")
        self.assertEqual(fetched2.degree, "Chemistry")

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

    def test_init_unexpected_kwargs(self):
        """Test initializing with unexpected keyword arguments"""
        # Capture stdout/stderr to check for warning? Or just ensure it doesn't crash.
        # For now, just ensure it runs and the unexpected kwarg is ignored.
        student = Student(name="Test", degree="Test Degree", non_existent_field="ignore_me")
        self.assertEqual(student.name, "Test")
        self.assertFalse(hasattr(student, "non_existent_field"))

    def test_init_missing_fields(self):
        """Test initializing with missing fields defaults them to None"""
        # Student has 'name', 'degree', 'department'
        student = Student(name="Only Name") # Missing degree (NOT NULL) and department (NULL)
        self.assertEqual(student.name, "Only Name")
        # Check that attributes exist and are None initially
        self.assertTrue(hasattr(student, 'degree'))
        self.assertIsNone(getattr(student, 'degree', 'Attribute missing')) # Default to None
        self.assertTrue(hasattr(student, 'department'))
        self.assertIsNone(getattr(student, 'department', 'Attribute missing')) # Default to None

    def test_as_dict_fk_none(self):
        """Test as_dict when a ForeignKey field is None"""
        student_no_dept = Student(name="No Dept", degree="Some Degree", department=None)
        Student.insert_entries([student_no_dept])
        student_dict = student_no_dept.as_dict()
        expected = {
            'id': student_no_dept.id,
            'name': "No Dept",
            'degree': "Some Degree",
            'department_id': None # Expect department_id to be None
        }
        self.assertDictEqual(student_dict, expected)

    def test_insert_empty_list(self):
        """Test insert_entries with an empty list"""
        # Should execute without error and print "No entries..."
        # We can't easily capture print output in unittest without extra libraries/setup
        # So we just check it doesn't raise an error.
        try:
            Student.insert_entries([])
        except Exception as e:
            self.fail(f"insert_entries([]) raised an exception: {e}")

    def test_insert_invalid_type_list(self):
        """Test insert_entries with list of invalid types (line 172)."""
        with self.assertRaisesRegex(TypeError, "Entries must be a list of dictionaries or BaseModel instances"):
            Student.insert_entries([1, 2, 3])

    def test_insert_constraint_violation_unique(self):
        """Test insert_entries violating UNIQUE constraint (line 220)."""
        # self.student1 (Yehor Boiar) already exists from setUp
        student_duplicate = Student(name="Yehor Boiar", degree="Another Degree")
        # This should raise an IntegrityError during _execute_insert
        with self.assertRaises(sqlite3.IntegrityError):
            Student.insert_entries([student_duplicate])

    def test_insert_constraint_violation_not_null(self):
        """Test insert_entries violating NOT NULL constraint (line 220)."""
        student_null_degree = Student(name="Null Degree Test", degree=None) # degree is NOT NULL
        # This should raise an IntegrityError during _execute_insert
        with self.assertRaises(sqlite3.IntegrityError):
            Student.insert_entries([student_null_degree])

    @patch('sqlite3.connect')
    def test_insert_connection_error(self, mock_connect):
        """Test insert_entries with a connection error (lines 246-248)."""
        # Configure the mock connection to raise an error
        mock_connect.side_effect = sqlite3.OperationalError("Cannot connect")

        student_new = Student(name="Connect Fail", degree="Test")
        with self.assertRaises(sqlite3.OperationalError):
            Student.insert_entries([student_new])
        # Verify rollback wasn't attempted (since connection failed) - tricky without more mocks

    def test_replace_no_conditions(self):
        """Test replace_entries with no conditions (lines 288-289)."""
        # Should run without error and print "Error: You must provide..."
        try:
            Student.replace_entries({}, {"degree": "Updated Degree"})
        except Exception as e:
            self.fail(f"replace_entries with no conditions raised an exception: {e}")

    def test_replace_no_values(self):
        """Test replace_entries with no new values (line 292)."""
        # Should run without error and print "Error: No new values..."
        try:
            Student.replace_entries({"id": self.student1.id}, {})
        except Exception as e:
            self.fail(f"replace_entries with no values raised an exception: {e}")

    def test_replace_basic(self):
        """Test basic functionality of replace_entries (covers finally block lines 363-364)."""
        student_id = self.student1.id
        Student.replace_entries({"id": student_id}, {"degree": "Updated CS"})
        updated_student = Student.objects.get(id=student_id)
        self.assertEqual(updated_student.degree, "Updated CS")

    def test_replace_constraint_violation(self):
        """Test replace_entries violating a constraint (lines 354, 359-361, 404-405)."""
        # Try updating student1's name to student2's name (violates UNIQUE)
        student1_id = self.student1.id
        student2_name = self.student2.name
        with self.assertRaises(sqlite3.IntegrityError):
            Student.replace_entries({"id": student1_id}, {"name": student2_name})

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()