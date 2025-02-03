class Field:
    """ Represents a database field. """
    def __init__(self, db_type):
        self.db_type = db_type

class CharField(Field):
    def __init__(self):
        super().__init__(f"TEXT NOT NULL")  # SQLite doesn't enforce max_length

class IntegerField(Field):
    def __init__(self):
        super().__init__("INTEGER NOT NULL DEFAULT 0")

class DateTimeField(Field):
    def __init__(self):
        super().__init__("DATETIME NOT NULL")
