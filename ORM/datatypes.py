class Field:
    """Represents a database field."""
    def __init__(self, db_type, null=True):
        """
        Initialize a field.

        :param db_type: The database type (e.g., TEXT, INTEGER, DATETIME).
        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        """
        self.db_type = db_type
        self.null = null

    def get_db_type(self):
        """Return the full database type, including NOT NULL if applicable."""
        if not self.null:
            return f"{self.db_type} NOT NULL"
        return self.db_type


class CharField(Field):
    def __init__(self, null=True):
        """
        Initialize a character field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        """
        super().__init__("TEXT", null)


class IntegerField(Field):
    def __init__(self, null=True, default=0):
        """
        Initialize an integer field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        :param default: The default value for the field.
        """
        super().__init__("INTEGER", null)
        self.default = default

    def get_db_type(self):
        """Return the full database type, including NOT NULL and DEFAULT if applicable."""
        db_type = super().get_db_type()
        if hasattr(self, 'default'):
            db_type += f" DEFAULT {self.default}"
        return db_type


class DateTimeField(Field):
    def __init__(self, null=True):
        """
        Initialize a datetime field.

        :param null: If True, the field is nullable. If False, the field is NOT NULL.
        """
        super().__init__("DATETIME", null)