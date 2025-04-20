"""
Defines the basic data types (Field, CharField, IntegerField, DateTimeField)
used for model fields and their corresponding SQL representation.
"""
class Field:
    """Represents a database field."""
    def __init__(self, db_type, null=True, unique=False, default=None, max_length=None):
        """
        Initialize a field.

        :param db_type: The database type (e.g., TEXT, INTEGER, DATETIME).
        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        """
        self.db_type = db_type
        self.null = null
        self.unique = unique
        self.default = default
        self.max_length = max_length

    def get_db_type(self):
        """
        Returns the SQL data type string for this field, including constraints
        like NOT NULL and UNIQUE based on the field's options.
        """
        parts = [self.db_type]
        if not self.null:
            parts.append("NOT NULL")
        # Ensure UNIQUE is checked independently of NULL
        if self.unique: # Changed from potential 'elif' or faulty logic
            parts.append("UNIQUE")
        # Handle default value if applicable (might be in subclass)
        if hasattr(self, 'default') and self.default is not None:
             # Ensure proper formatting for SQL DEFAULT clause, e.g., strings need quotes
             default_val = self.default
             if isinstance(default_val, str):
                 default_val = f"'{default_val}'" # Add quotes for string defaults
             parts.append(f"DEFAULT {default_val}")

        return " ".join(parts)


class CharField(Field):
    """Represents a character string field (VARCHAR) in the database."""
    db_type = 'VARCHAR'
    def __init__(self, null=True, unique=False, default=None, max_length=None):
        """
        Initialize a character field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        :param unique: If True, add a UNIQUE constraint.
        """
        super().__init__("TEXT", null=null, unique=unique)
        self.default = default
        self.max_length = max_length


class IntegerField(Field):
    """Represents an integer field (INTEGER) in the database."""
    db_type = 'INTEGER'
    def __init__(self, null=True, default=0, unique=False):
        """
        Initialize an integer field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        :param default: The default value for the field.
        :param unique: If True, add a UNIQUE constraint.
        """
        super().__init__("INTEGER", null=null, unique=unique)
        self.default = default

class DateTimeField(Field):
    """Represents a date/time field (DATETIME) in the database."""
    db_type = 'DATETIME'
    def __init__(self, null=True, unique=False, default=None):
        """
        Initialize a datetime field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        :param unique: If True, add a UNIQUE constraint.
        """
        super().__init__("DATETIME", null=null, unique=unique)
        self.default = default