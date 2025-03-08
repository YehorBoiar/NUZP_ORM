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
        many_to_many = {}
        for attr_name, attr_value in list(attrs.items()):
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            elif isinstance(attr_value, ManyToManyField):
                many_to_many[attr_name] = attr_value
        attrs["_fields"] = fields
        attrs["_many_to_many"] = many_to_many
        new_class = super().__new__(cls, name, bases, attrs)

        return new_class

# ====================================================
# 2. Relationship Field Types
# ====================================================

class ManyToManyField:
    def __init__(self, to, through=None):
        self.to = to  # Target model class
        self.through = through  # Optional custom junction table

    def add(self, source_class, source_dict, target_dict):
        """
        Add a relationship between two records (represented as dictionaries).
        If the relationship already exists, it will be skipped.
        """
        # Determine the junction table name
        source_class_name = source_class.__name__.lower()
        target_class_name = self.to.__name__.lower()
        junction_table = self.through or f"{source_class_name}_{target_class_name}"

        # Check if the relationship already exists
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(f"""
            SELECT 1 FROM {junction_table}
            WHERE {source_class_name}_id = ? AND {target_class_name}_id = ?
        """, (source_dict["id"], target_dict["id"]))
        exists = cursor_obj.fetchone()

        if exists:
            # Relationship already exists, so we skip the insertion
            connection_obj.close()
            return

        # Insert into the junction table
        try:
            cursor_obj.execute(f"""
                INSERT INTO {junction_table} ({source_class_name}_id, {target_class_name}_id)
                VALUES (?, ?)
            """, (source_dict["id"], target_dict["id"]))
            connection_obj.commit()
        except sqlite3.IntegrityError as e:
            # Handle the UNIQUE constraint error gracefully
            if "UNIQUE constraint failed" in str(e):
                # Relationship already exists, so we skip the insertion
                pass
            else:
                # Re-raise other IntegrityError exceptions
                raise e
        finally:
            connection_obj.close()

    def remove(self, source_class, source_dict, target_dict):
        """
        Remove a relationship between two records (represented as dictionaries).
        """
        # Determine the junction table name
        source_class_name = source_class.__name__.lower()
        target_class_name = self.to.__name__.lower()
        junction_table = self.through or f"{source_class_name}_{target_class_name}"

        # Delete from the junction table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(f"""
            DELETE FROM {junction_table}
            WHERE {source_class_name}_id = ? AND {target_class_name}_id = ?
        """, (source_dict["id"], target_dict["id"]))
        connection_obj.commit()
        connection_obj.close()

    def all(self, source_class, source_dict):
        """
        Retrieve all related records for a source record (represented as a dictionary).
        """
        # Determine the junction table name
        source_class_name = source_class.__name__.lower()
        target_class_name = self.to.__name__.lower()
        junction_table = self.through or f"{source_class_name}_{target_class_name}"

        # Query the junction table and join with the target table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(f"""
            SELECT {target_class_name}.*
            FROM {target_class_name}
            JOIN {junction_table} ON {target_class_name}.id = {junction_table}.{target_class_name}_id
            WHERE {junction_table}.{source_class_name}_id = ?
        """, (source_dict["id"],))
        rows = cursor_obj.fetchall()
        connection_obj.close()

        # Convert rows to dictionaries
        columns = [column[0] for column in cursor_obj.description]
        return [dict(zip(columns, row)) for row in rows]
    
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
            if(query.__contains__("LIMIT")):
                query += f" OFFSET {self.offset_val}"
            else:
                query += f" LIMIT -1 OFFSET {self.offset_val}"
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
        Supports lookup operators like __exact, __like, __gt, etc.

        Args:
            **conditions: Keyword arguments representing field lookups and values.

        Returns:
            QuerySet: A new QuerySet instance with the combined filter conditions.

        Example:
            .filter(name__like='John%', age__gt=21)
            → WHERE name LIKE 'John%' AND age > 21
        """
        clauses = []
        params = []
        
        # Parse conditions and build SQL clauses
        for key, value in conditions.items():
            # Split field and lookup operator
            parts = key.split('__', 1)
            field = parts[0]
            lookup = parts[1] if len(parts) > 1 else 'exact'

            # Handle different lookup types
            if lookup == 'exact':
                clause = f"{field} = ?"
            elif lookup == 'like':
                clause = f"{field} LIKE ?"
            elif lookup == 'gt':
                clause = f"{field} > ?"
            elif lookup == 'gte':
                clause = f"{field} >= ?"
            elif lookup == 'lt':
                clause = f"{field} < ?"
            elif lookup == 'lte':
                clause = f"{field} <= ?"
            elif lookup == 'in':
                placeholders = ', '.join(['?'] * len(value))
                clause = f"{field} IN ({placeholders})"
                params.extend(value)
            elif lookup == 'neq':
                clause = f"{field} != ?"
            else:
                raise ValueError(f"Invalid lookup operator: {lookup}")

            # Add value to params (unless handled by IN clause)
            if lookup != 'in':
                params.append(value)

            clauses.append(clause)

        # Combine with existing WHERE clause
        new_where = " AND ".join(clauses)
        if self.where_clause:
            new_where = f"({self.where_clause}) AND ({new_where})"

        # Combine parameters
        new_params = self.parameters + params

        return QuerySet(
            model=self.model,
            where_clause=new_where,
            parameters=new_params,
            order_clause=self.order_clause,
            limit_val=self.limit_val,
            offset_val=self.offset_val
        )
        
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
    
    def __getitem__(self, index):
        return QuerySet(self.model)[index]

    def __iter__(self):
        return QuerySet(self.model).__iter__()

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
                ref_table = field.to.__name__.lower() # get referenced table 
                fields_sql.append(f"{column_name} {field.db_type} REFERENCES {ref_table}(id) ON DELETE CASCADE") # delete everything if id deleted 
            else:
                fields_sql.append(f"{field_name} {field.db_type}")
        cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor_obj.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(fields_sql)});")
        
        for field_name, field in cls._many_to_many.items():
            junction_table = field.through or f"{table_name}_{field.to.__name__.lower()}"
            cursor_obj.execute(f"""
                CREATE TABLE IF NOT EXISTS {junction_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    {table_name}_id INTEGER REFERENCES {table_name}(id) ON DELETE CASCADE,
                    {field.to.__name__.lower()}_id INTEGER REFERENCES {field.to.__name__.lower()}(id) ON DELETE CASCADE,
                    UNIQUE({table_name}_id, {field.to.__name__.lower()}_id)
                );
            """)
        connection_obj.close()

    @classmethod
    def insert_entries(cls, entries):
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")
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
                if isinstance(field, ForeignKey) or isinstance(field, OneToOneField):
                    value = entry[field_name]
                    if isinstance(value, dict):
                        related_id = value.get('id')
                    else:
                        related_id = value
                    
                    if isinstance(field, OneToOneField):
                        check_query = f"SELECT COUNT(*) FROM {cls.__name__.lower()} WHERE {field_name}_id = ?"
                        cursor_obj.execute(check_query, (related_id,))
                        if cursor_obj.fetchone()[0] > 0:
                            raise ValueError(f"Duplicate entry detected for {field_name} (OneToOneField) with id {related_id}")

                    row.append(related_id)
                else:
                    row.append(entry[field_name])
            
            values.append(tuple(row))
        try:
            cursor_obj.executemany(query, values)
            connection_obj.commit()
            print(f"Successfully inserted {len(entries)} entries into {cls.__name__}")
        except Exception as e:
            raise
        finally:
            connection_obj.close()

    @classmethod
    def delete_entries(cls, conditions, confirm=False):
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")
        
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;") 
        
        if not conditions:
            if confirm or input(f"Are you sure you want to delete ALL records from {cls.__name__}? (yes/no): ").lower() == "yes":
                query = f"DELETE FROM {cls.__name__.lower()}"
                cursor_obj.execute(query)
            else:
                print("Deletion cancelled.")
                return
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
        cursor_obj.execute("PRAGMA foreign_keys = ON;") 
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


    @classmethod
    def add_m2m(cls, field_name, source_dict, target_dict):
        """
        Add a M2M relationship between two records (represented as dictionaries).
        """
        # Retrieve the ManyToManyField instance
        m2m_field = getattr(cls, field_name)
        m2m_field.add(cls, source_dict, target_dict)

    @classmethod
    def remove_m2m(cls, field_name, source_dict, target_dict):
        """
        Remove a M2M relationship between two records (represented as dictionaries).
        """
        # Retrieve the ManyToManyField instance
        m2m_field = getattr(cls, field_name)
        m2m_field.remove(cls, source_dict, target_dict)

    @classmethod
    def get_m2m(cls, field_name, source_dict):
        """
        Retrieve all related records for a source record (represented as a dictionary).
        """
        # Retrieve the ManyToManyField instance
        m2m_field = getattr(cls, field_name)
        return m2m_field.all(cls, source_dict)