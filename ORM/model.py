from ORM.datatypes import Field
import os
import sqlite3

DB_PATH = "databases/main.sqlite3"

# ====================================================
# 1. Extend the metaclass to capture relationship fields
# ====================================================

class ModelMeta(type):
    """
    Metaclass to register model fields including relationships.
    """
    def __new__(cls, name, bases, attrs):
        fields = {}
        m2m_fields = {}
        o2o_fields = {}
        for attr_name, attr_value in list(attrs.items()):
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            elif isinstance(attr_value, ManyToManyField):
                m2m_fields[attr_name] = attr_value
            elif isinstance(attr_name, OneToOneField):
                o2o_fields[attr_name] = attr_value
        attrs["_fields"] = fields
        attrs["_m2m_fields"] = m2m_fields
        attrs["_o2o_feilds"] = o2o_fields
        new_class = super().__new__(cls, name, bases, attrs)
        # Contribute each ManyToManyField to the class (as a descriptor)
        for m2m_name, m2m_field in m2m_fields.items():
            m2m_field.contribute_to_class(new_class, m2m_name)
        return new_class

# ====================================================
# 2. Relationship Field Types
# ====================================================

class ForeignKey(Field):
    """
    Implements a one-to-many relationship (the "many" side).
    In the database, we store the related object's id as an INTEGER.
    """
    def __init__(self, to, **kwargs):
        self.to = to  # the target model class
        super().__init__("INTEGER", **kwargs)

class OneToOneField(ForeignKey):
    """
    Implements a one-to-one relationship.
    This is just a ForeignKey with a UNIQUE constraint.
    """
    def __init__(self, to, **kwargs):
        kwargs.setdefault('unique', True)
        super().__init__(to, **kwargs)

class ManyToManyField:
    """
    Implements a many-to-many relationship.
    No column is created on the model's own table; an intermediate join table is used.
    """
    def __init__(self, to):
        self.to = to  # the target model class
        self.name = None  # will be set when the field is attached to the model

    def contribute_to_class(self, cls, name):
        self.name = name
        self.model = cls
        # Replace the attribute with a descriptor
        setattr(cls, name, ManyToManyDescriptor(self))

# ====================================================
# 3. Many-to-Many Descriptor and Manager
# ====================================================

class ManyToManyDescriptor:
    """
    When you access the many-to-many field on an instance,
    this descriptor returns a ManyToManyManager.
    """
    def __init__(self, m2m_field):
        self.m2m_field = m2m_field

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return ManyToManyManager(instance, self.m2m_field)

class ManyToManyManager:
    """
    Handles many-to-many operations (querying, adding, etc.) via a join table.
    """
    def __init__(self, instance, m2m_field):
        self.instance = instance  # e.g., a dict representing the source row
        self.m2m_field = m2m_field

    def get_join_table_name(self):
        # For example, if self.instance is of class "Book" and the field is "authors"
        # and the related model is "Author", we name the join table: book_authors_author.
        source_table = self.instance.__class__.__name__.lower()
        target_table = self.m2m_field.to.__name__.lower()
        return f"{source_table}_{self.m2m_field.name}_{target_table}"

    def create_join_table(self):
        join_table = self.get_join_table_name()
        source_table = self.instance.__class__.__name__.lower()
        target_table = self.m2m_field.to.__name__.lower()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor = connection_obj.cursor()
        # Simple join table with two INTEGER columns
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {join_table} (
            {source_table}_id INTEGER,
            {target_table}_id INTEGER
        );
        """
        cursor.execute(create_sql)
        connection_obj.commit()
        connection_obj.close()

    def add(self, *objs):
        """
        Add relationships between self.instance and the provided objects.
        (It is assumed that each related object has been inserted and has an 'id'.)
        """
        self.create_join_table()
        join_table = self.get_join_table_name()
        source_table = self.instance.__class__.__name__.lower()
        target_table = self.m2m_field.to.__name__.lower()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor = connection_obj.cursor()
        for obj in objs:
            # Here we assume that both self.instance and obj are dict-like (with an 'id' key).
            query = f"INSERT INTO {join_table} ({source_table}_id, {target_table}_id) VALUES (?, ?)"
            cursor.execute(query, (self.instance['id'], obj['id']))
        connection_obj.commit()
        connection_obj.close()

    def all(self):
        """
        Retrieve all related objects.
        """
        join_table = self.get_join_table_name()
        source_table = self.instance.__class__.__name__.lower()
        target_table = self.m2m_field.to.__name__.lower()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor = connection_obj.cursor()
        query = f"""
        SELECT t.* FROM {target_table} t
        JOIN {join_table} j ON t.id = j.{target_table}_id
        WHERE j.{source_table}_id = ?
        """
        cursor.execute(query, (self.instance['id'],))
        column_names = [desc[0] for desc in cursor.description]
        results = [dict(zip(column_names, row)) for row in cursor.fetchall()]
        connection_obj.close()
        return results

class QuerySet:
    """
    A QuerySet represents a collection of database queries for a specific model.
    It allows you to build and execute SQL queries in a Pythonic way, with support
    for filtering, ordering, limiting, and offsetting results.

    Attributes:
        model (class): The model class associated with this QuerySet.
        where_clause (str): The SQL WHERE clause for filtering results.
        parameters (list): The parameters to be used in the WHERE clause.
        order_clause (str): The SQL ORDER BY clause for sorting results.
        limit_val (int): The maximum number of results to return.
        offset_val (int): The number of results to skip before returning.

    Methods:
        filter(**conditions): Adds conditions to the WHERE clause to filter results.
        get(**conditions): Returns a single record matching the conditions or raises an exception.
        order_by(*fields): Specifies the order in which results should be returned.
        limit(limit_val): Limits the number of results returned.
        offset(offset_val): Specifies the number of results to skip.
        all(): Executes the query and returns all results.
        __iter__(): Allows iteration over the results.
        __getitem__(index): Retrieves a specific result or slice of results.

    Example Usage:
        # Assuming `User` is a model class representing a database table.

        # Get all users
        users = QuerySet(User).all()

        # Filter users by age and order by name
        users = QuerySet(User).filter(age=25).order_by("name")

        # Get a single user by ID
        user = QuerySet(User).get(id=1)

        # Get the first 10 users, skipping the first 5
        users = QuerySet(User).limit(10).offset(5).all()
    """

    def __init__(self, model, where_clause=None, parameters=None, order_clause=None, limit_val=None, offset_val=None):
        """
        Initializes a new QuerySet instance.

        Args:
            model (class): The model class associated with this QuerySet.
            where_clause (str, optional): The SQL WHERE clause for filtering results.
            parameters (list, optional): The parameters to be used in the WHERE clause.
            order_clause (str, optional): The SQL ORDER BY clause for sorting results.
            limit_val (int, optional): The maximum number of results to return.
            offset_val (int, optional): The number of results to skip before returning.
        """
        self.model = model
        self.where_clause = where_clause
        self.parameters = parameters if parameters is not None else []
        self.order_clause = order_clause
        self.limit_val = limit_val
        self.offset_val = offset_val

    def _build_query(self):
        """
        Builds the SQL query based on the current state of the QuerySet.

        Returns:
            str: The constructed SQL query.
        """
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
        """
        Executes the constructed SQL query and returns the results.

        Returns:
            list: A list of dictionaries, where each dictionary represents a row in the result set.
        """
        query = self._build_query()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(query, tuple(self.parameters))
        column_names = [desc[0] for desc in cursor_obj.description]
        results = [dict(zip(column_names, row)) for row in cursor_obj.fetchall()]
        connection_obj.close()
        return results

    def filter(self, **conditions):
        """
        Adds conditions to the WHERE clause to filter the results.

        Args:
            **conditions: Keyword arguments representing the field names and values to filter by.

        Returns:
            QuerySet: A new QuerySet instance with the added filter conditions.
        """
        clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])
        params = list(conditions.values())
        if self.where_clause:
            new_clause = f"({self.where_clause}) AND ({clause})"
            new_params = self.parameters + params
        else:
            new_clause = clause
            new_params = params
        return QuerySet(self.model, new_clause, new_params, self.order_clause, self.limit_val, self.offset_val)

    def get(self, **conditions):
        """
        Returns a single record matching the specified conditions.

        Args:
            **conditions: Keyword arguments representing the field names and values to filter by.

        Returns:
            dict: A dictionary representing the matching record.

        Raises:
            Exception: If no matching record is found or if multiple records are found.
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
        Specifies the order in which results should be returned.

        Args:
            *fields: Field names to order by. Prefix a field with "-" to sort in descending order.

        Returns:
            QuerySet: A new QuerySet instance with the specified order.
        """
        order_clause = []
        for field in fields:
            if field.startswith("-"):
                order_clause.append(f"{field[1:]} DESC")
            else:
                order_clause.append(f"{field} ASC")
        return QuerySet(self.model, self.where_clause, self.parameters, ", ".join(order_clause), self.limit_val, self.offset_val)

    def limit(self, limit_val):
        """
        Limits the number of results returned.

        Args:
            limit_val (int): The maximum number of results to return.

        Returns:
            QuerySet: A new QuerySet instance with the specified limit.
        """
        return QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, limit_val, self.offset_val)

    def offset(self, offset_val):
        """
        Specifies the number of results to skip before returning.

        Args:
            offset_val (int): The number of results to skip.

        Returns:
            QuerySet: A new QuerySet instance with the specified offset.
        """
        return QuerySet(self.model, self.where_clause, self.parameters, self.order_clause, self.limit_val, offset_val)

    def all(self):
        """
        Executes the query and returns all results.

        Returns:
            list: A list of dictionaries, where each dictionary represents a row in the result set.
        """
        return self._execute()

    def __iter__(self):
        """
        Allows iteration over the results.

        Returns:
            iter: An iterator over the results.
        """
        return iter(self._execute())

    def __getitem__(self, index):
        """
        Retrieves a specific result or slice of results.

        Args:
            index (int or slice): The index or slice to retrieve.

        Returns:
            dict or list: A dictionary representing a single result or a list of dictionaries.

        Raises:
            IndexError: If the index is out of range.
            TypeError: If the index is not an integer or slice.
        """
        if isinstance(index, slice):
            offset = index.start if index.start is not None else 0
            limit_val = index.stop - offset if index.stop is not None else None
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

class Manager:
    def __get__(self, instance, owner):
        self.model = owner
        return self

    def __getattr__(self, attr):
        return getattr(QuerySet(self.model), attr)

    def all(self):
        return QuerySet(self.model)

    def filter(self, **conditions):
        return QuerySet(self.model).filter(**conditions)

    def get(self, **conditions):
        return QuerySet(self.model).get(**conditions)

# ====================================================
# 5. BaseModel: Create tables, insert data, etc.
# ====================================================

class BaseModel(metaclass=ModelMeta):
    objects = Manager()

    @classmethod
    def create_table(cls):
        if not os.path.exists('databases'):
            os.makedirs('databases')
        table_name = cls.__name__.lower()
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        fields_sql = ["id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"]
        for field_name, field in cls._fields.items():
            if isinstance(field, (ForeignKey, OneToOneField)):
                # Store foreign keys as "<field_name>_id"
                column_name = field_name + "_id"
                fields_sql.append(f"{column_name} {field.db_type}")
            else:
                fields_sql.append(f"{field_name} {field.db_type}")
        # ManyToManyFields do not create a column in this table.
        cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor_obj.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(fields_sql)});")
        connection_obj.close()

    @classmethod
    def insert_entries(cls, entries):
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        field_names = []
        for field_name, field in cls._fields.items():
            if isinstance(field, (ForeignKey, OneToOneField)):
                field_names.append(field_name + "_id")
            else:
                field_names.append(field_name)
        placeholders = ", ".join(["?" for _ in field_names])
        columns = ", ".join(field_names)
        query = f"INSERT INTO {cls.__name__.lower()} ({columns}) VALUES ({placeholders})"
        values = []
        for entry in entries:
            row = []
            for field_name, field in cls._fields.items():
                if isinstance(field, (ForeignKey, OneToOneField)):
                    # Expecting that the related object is inserted and its id is available.
                    value = entry[field_name]
                    if isinstance(value, dict):
                        row.append(value['id'])
                    else:
                        row.append(value)
                else:
                    row.append(entry[field_name])
            values.append(tuple(row))
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
