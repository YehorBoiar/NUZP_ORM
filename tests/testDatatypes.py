import unittest
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM.datatypes import Field, CharField, IntegerField, DateTimeField

class TestFieldTypes(unittest.TestCase):

    def test_field_get_db_type(self):
        """Test the get_db_type method of the base Field class."""
        # Default (null=True, unique=False)
        field_default = Field("TEXT")
        self.assertEqual(field_default.get_db_type(), "TEXT")

        # Not Null (null=False, unique=False)
        field_not_null = Field("INTEGER", null=False)
        self.assertEqual(field_not_null.get_db_type(), "INTEGER NOT NULL")

        # Unique and Null (null=True, unique=True)
        field_unique_null = Field("REAL", unique=True)
        self.assertEqual(field_unique_null.get_db_type(), "REAL UNIQUE")

        # Unique and Not Null (null=False, unique=True)
        field_unique_not_null = Field("BLOB", null=False, unique=True)
        self.assertEqual(field_unique_not_null.get_db_type(), "BLOB NOT NULL UNIQUE") # This line fails

    def test_char_field(self):
        """Test CharField initialization and db_type."""
        # Default (null=True)
        char_default = CharField()
        self.assertEqual(char_default.db_type, "TEXT")
        self.assertTrue(char_default.null)
        self.assertEqual(char_default.get_db_type(), "TEXT")

        # Not Null (null=False)
        char_not_null = CharField(null=False)
        self.assertEqual(char_not_null.db_type, "TEXT")
        self.assertFalse(char_not_null.null)
        self.assertEqual(char_not_null.get_db_type(), "TEXT NOT NULL")

    def test_integer_field(self):
        """Test IntegerField initialization and db_type including default."""
        # Default (null=True, default=0)
        int_default = IntegerField()
        self.assertEqual(int_default.db_type, "INTEGER")
        self.assertTrue(int_default.null)
        self.assertEqual(int_default.default, 0)
        # Check get_db_type includes default
        self.assertEqual(int_default.get_db_type(), "INTEGER DEFAULT 0")

        # Not Null with different default
        int_not_null_default_5 = IntegerField(null=False, default=5)
        self.assertEqual(int_not_null_default_5.db_type, "INTEGER")
        self.assertFalse(int_not_null_default_5.null)
        self.assertEqual(int_not_null_default_5.default, 5)
        self.assertEqual(int_not_null_default_5.get_db_type(), "INTEGER NOT NULL DEFAULT 5")

        # Nullable without explicit default (should still have default=0 from init)
        int_nullable = IntegerField(null=True)
        self.assertEqual(int_nullable.get_db_type(), "INTEGER DEFAULT 0")

        # Nullable with None default (should not add DEFAULT clause)
        # Note: The current implementation correctly omits DEFAULT when the value is None.
        int_none_default = IntegerField(null=True, default=None)
        self.assertEqual(int_none_default.default, None)
        # Assert that no DEFAULT clause is added when default is None
        self.assertEqual(int_none_default.get_db_type(), "INTEGER") # Changed expected value

    def test_datetime_field(self):
        """Test DateTimeField initialization and db_type."""
        # Default (null=True)
        dt_default = DateTimeField()
        self.assertEqual(dt_default.db_type, "DATETIME")
        self.assertTrue(dt_default.null)
        self.assertEqual(dt_default.get_db_type(), "DATETIME")

        # Not Null (null=False)
        dt_not_null = DateTimeField(null=False)
        self.assertEqual(dt_not_null.db_type, "DATETIME")
        self.assertFalse(dt_not_null.null)
        self.assertEqual(dt_not_null.get_db_type(), "DATETIME NOT NULL")

if __name__ == '__main__':
    unittest.main()