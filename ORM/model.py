from ORM.datatypes import Field
import os
import sqlite3

DB_PATH = "databases/main.sqlite3"

class ModelMeta(type):
    """
    Metaclass to register model fields.
    """
    def __new__(cls, name, bases, attrs):
        fields = {}
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        attrs["_fields"] = fields
        return super().__new__(cls, name, bases, attrs)

# ----------------------------
# QuerySet: Build and execute queries
# ----------------------------
class QuerySet:
    def __init__(self, model, where_clause=None, parameters=None, order_clause=None, limit_val=None, offset_val=None):
        """
        :param model: The model class (e.g. User)
        :param where_clause: A SQL string for the WHERE clause.
        :param parameters: A list of parameters for parameterized queries.
        :param order_clause: A SQL string for ORDER BY.
        :param limit_val: Limit value.
        :param offset_val: Offset value.
        """
        self.model = model
        self.where_clause = where_clause
        self.parameters = parameters if parameters is not None else []
        self.order_clause = order_clause
        self.limit_val = limit_val
        self.offset_val = offset_val

    def _build_query(self):
        query = f"SELECT * FROM {self.model.__name__.lower()}"
        if self.where_clause:
            query += " WHERE " + self.where_clause
        if self.order_clause:
            query += " ORDER BY " + self.order_clause
        if self.limit_val is not None:
            query += f" LIMIT {self.limit_val}"
        if self.offset_val is not None:
            query += f" OFFSET {self.offset_val}"
        return query

    def _execute(self):
        query = self._build_query()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        # Debug: print("Executing query:", query, self.parameters)
        cursor_obj.execute(query, tuple(self.parameters))
        # Get column names from the description
        column_names = [desc[0] for desc in cursor_obj.description]
        results = [dict(zip(column_names, row)) for row in cursor_obj.fetchall()]
        connection_obj.close()
        return results

    def filter(self, **conditions):
        """
        Add filtering conditions.
        Example: .filter(name="Alice", age=25)
        """
        clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])
        params = list(conditions.values())
        # If there is already a WHERE clause, combine with AND.
        if self.where_clause:
            new_clause = f"({self.where_clause}) AND ({clause})"
            new_params = self.parameters + params
        else:
            new_clause = clause
            new_params = params
        return QuerySet(self.model, new_clause, new_params, self.order_clause, self.limit_val, self.offset_val)

    def get(self, **conditions):
        """
        Returns a single record. Raises an exception if no record or multiple records are found.
        """
        qs = self.filter(**conditions).limit(2)
        results = qs._execute()
        if len(results) == 0:
            raise Exception("DoesNotExist: No matching record found.")
        elif len(results) > 1:
            raise Exception("MultipleObjectsReturned: More than one record found.")
        return results[0]

    def order_by(self, *fields):
        """
        Specify ordering. Example: .order_by("name") or .order_by("name", "-age")
        (A '-' prefix can be used to indicate descending order.)
        """
        order_clause = []
        for field in fields:
            if field.startswith("-"):
                order_clause.append(f"{field[1:]} DESC")
            else:
                order_clause.append(f"{field} ASC")
        return QuerySet(self.model, self.where_clause, self.parameters, ", ".join(order_clause), self.limit_val, self.offset_val)

    def limit(self, limit_val):
        """Limit the number of returned records."""
        return QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, limit_val, self.offset_val)

    def offset(self, offset_val):
        """Skip a given number of records."""
        return QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, self.limit_val, offset_val)

    def all(self):
        """Execute the query and return all results as a list of dicts."""
        return self._execute()

    def __iter__(self):
        return iter(self._execute())

    def __getitem__(self, index):
        # Allow slicing (e.g., qs[2:5])
        if isinstance(index, slice):
            offset = index.start if index.start is not None else 0
            if index.stop is not None:
                limit_val = index.stop - offset
            else:
                limit_val = None
            qs = QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, limit_val, offset)
            return qs._execute()
        elif isinstance(index, int):
            qs = QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, 1, index)
            result = qs._execute()
            if result:
                return result[0]
            raise IndexError("Index out of range")
        else:
            raise TypeError("Invalid argument type.")

# ----------------------------
# Manager: Provides the starting point for queries
# ----------------------------
class Manager:
    def __get__(self, instance, owner):
        self.model = owner
        return self

    def all(self):
        return QuerySet(self.model)

    def filter(self, **conditions):
        return QuerySet(self.model).filter(**conditions)

    def get(self, **conditions):
        return QuerySet(self.model).get(**conditions)

    def order_by(self, *fields):
        return QuerySet(self.model).order_by(*fields)

# ----------------------------
# BaseModel: Includes CRUD and table creation methods.
# Now, every model will also have an "objects" attribute for querying.
# ----------------------------
class BaseModel(metaclass=ModelMeta):
    # Attach the default manager
    objects = Manager()

    @classmethod
    def create_table(cls):
        if not os.path.exists('databases'):
            os.makedirs('databases')

        table_name = cls.__name__.lower()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        fields_sql = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for field_name, field in cls._fields.items():
            fields_sql.append(f"{field_name} {field.db_type}")

        # For demo purposes, drop the table first
        cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor_obj.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(fields_sql)});")
        connection_obj.close()

    @classmethod
    def insert_entries(cls, entries):
        """
        Inserts multiple entries (rows) into the database table.
        :param entries: A list of dictionaries.
        """
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")

        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()

        field_names = list(cls._fields.keys())
        placeholders = ", ".join(["?" for _ in field_names])
        columns = ", ".join(field_names)
        query = f"INSERT INTO {cls.__name__.lower()} ({columns}) VALUES ({placeholders})"
        values = [tuple(entry[field] for field in field_names) for entry in entries]

        try:
            cursor_obj.executemany(query, values)
            connection_obj.commit()
            print(f"Successfully inserted {len(entries)} entries into {cls.__name__}")
        except Exception as e:
            print(f"Error inserting entries: {e}")
        finally:
            connection_obj.close()

    @classmethod
    def delete_entries(cls, conditions):
        """
        Deletes entries from the database based on conditions.
        :param conditions: A dictionary of conditions (e.g., {"name": "Alice"}).
        """
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")

        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()

        if not conditions:
            confirmation = input(f"Are you sure you want to delete ALL records from {cls.__name__}? (yes/no): ")
            if confirmation.lower() == "no":
                print("Deletion cancelled.")
                return
            query = f"DELETE FROM {cls.__name__.lower()}"
            cursor_obj.execute(query)
        else:
            where_clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])
            query = f"DELETE FROM {cls.__name__.lower()} WHERE {where_clause}"
            values = tuple(conditions.values())
            cursor_obj.execute(query, values)

        connection_obj.commit()
        print(f"Deleted entries from {cls.__name__} where {conditions}")
        connection_obj.close()

    @classmethod
    def replace_entries(cls, conditions, new_values):
        """
        Updates entries based on conditions.
        :param conditions: A dictionary to match rows.
        :param new_values: A dictionary of new values.
        """
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")

        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()

        if not conditions:
            print("Error: You must provide at least one condition to update specific rows.")
            return

        if not new_values:
            print("Error: No new values provided to update.")
            return

        set_clause = ", ".join([f"{field} = ?" for field in new_values.keys()])
        where_clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])
        query = f"UPDATE {cls.__name__.lower()} SET {set_clause} WHERE {where_clause}"
        values = tuple(new_values.values()) + tuple(conditions.values())

        try:
            cursor_obj.execute(query, values)
            connection_obj.commit()
            print(f"Updated entries in {cls.__name__} where {conditions} with {new_values}")
        except Exception as e:
            print(f"Error updating entries: {e}")
        finally:
            connection_obj.close()
