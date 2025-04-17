import sqlite3
import re


DB_PATH = "databases/main.sqlite3"
REPR_OUTPUT_SIZE = 10

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

    def _fetch_for_repr(self):
        """Fetch a limited number of results for representation."""
        # Fetch one more than the limit to check if there are more results
        qs_limited = QuerySet(
            model=self.model,
            where_clause=self.where_clause,
            parameters=self.parameters,
            order_clause=self.order_clause,
            limit_val=REPR_OUTPUT_SIZE + 1, # Fetch one extra
            offset_val=self.offset_val
        )
        return qs_limited._execute() # Returns list of dicts currently

    def __repr__(self):
        """Return a string representation of the QuerySet, showing limited results."""
        data = self._fetch_for_repr()
        # Check if there were more results than the limit
        has_more = len(data) > REPR_OUTPUT_SIZE
        # Slice data to the display limit
        data_to_display = data[:REPR_OUTPUT_SIZE]

        # Convert dicts to model instances for better repr (if .get() returned objects)
        # Since _execute currently returns dicts, we'll represent them as dicts for now.
        # Ideally, _execute would return model instances.
        # For now, just format the list of dicts.
        items_repr = ",\n ".join(repr(item) for item in data_to_display)

        if has_more:
            return f"<QuerySet [\n {items_repr},\n ...\n]>"
        else:
            return f"<QuerySet [\n {items_repr}\n]>"


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
            if (query.__contains__("LIMIT")):
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
        connection_obj.execute("PRAGMA foreign_keys = ON;")
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(query, tuple(self.parameters))
        column_names = [desc[0] for desc in cursor_obj.description]
        results = [dict(zip(column_names, row))
                   for row in cursor_obj.fetchall()]
        connection_obj.close()
        return results

    def sanitize_field_name(self, field_name):
        """
        Sanitizes a field name to ensure it is a valid SQL identifier.
        Raises ValueError if the field name is invalid.
        """
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", field_name):
            raise ValueError(f"Invalid field name: {field_name}")
        return field_name

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

            try:
                field = self.sanitize_field_name(field)
            except ValueError as e:
                raise ValueError(
                    f"Invalid field name in condition: {key}") from e

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
            raise Exception(
                "MultipleObjectsReturned: More than one record found.")
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
            qs = QuerySet(self.model, self.where_clause,
                          self.parameters, self.order_clause, limit_val, offset)
            return qs._execute()
        elif isinstance(index, int):
            qs = QuerySet(self.model, self.where_clause,
                          self.parameters, self.order_clause, 1, index)
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
