import os
import sqlite3
from ORM.fields import ForeignKey, OneToOneField, ManyToManyField
from ORM.datatypes import Field
from ORM.query import Manager

DB_PATH = "databases/main.sqlite3"


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
                if hasattr(attr_value, '__set_name__'):
                    attr_value.__set_name__(None, attr_name)

        attrs["_fields"] = fields
        attrs["_many_to_many"] = many_to_many
        new_class = super().__new__(cls, name, bases, attrs)

        return new_class

# ====================================================
# 5. BaseModel: Create tables, insert data, etc.
# ====================================================


class BaseModel(metaclass=ModelMeta):
    objects = Manager()
    id = None # Initialize id attribute

    def __init__(self, **kwargs):
        """
        Initializes a model instance. Expects keyword arguments matching
        the model's defined *non-relational* fields (plus 'id').
        Relational fields (FK, O2O, M2M) are handled separately or via descriptors.
        """
        # Assign provided keyword arguments to attributes
        for key, value in kwargs.items():
            if key == 'id':
                self.id = value
            # Only set attributes for keys that are in _fields (non-relational or FK/O2O)
            # This prevents overwriting M2M descriptors.
            elif key in self._fields:
                 setattr(self, key, value)
            else:
                print(f"Warning: Ignoring unexpected keyword argument '{key}' for {self.__class__.__name__}")

        # Ensure essential attributes like 'id' exist even if not in kwargs
        if 'id' not in kwargs:
            self.id = None
        # Ensure field attributes exist, defaulting to None if not in kwargs
        # This ensures attributes exist even if not provided in kwargs
        for field_name in self._fields:
            if not hasattr(self, field_name):
                setattr(self, field_name, None)


    def __repr__(self):
        """Return a string representation of the model instance."""
        # Use the instance's ID if available, otherwise indicate it's unsaved
        pk = self.id if self.id is not None else '(unsaved)'
        return f"<{self.__class__.__name__}: {pk}>"

    def as_dict(self):
        """Return a dictionary representation of the model instance."""
        data = {'id': self.id}
        # Handle regular fields and FK/O2O fields
        for field_name, field in self._fields.items():
            if isinstance(field, (ForeignKey, OneToOneField)):
                # For FK/O2O, store the related object's ID
                # Check for the _id attribute first (set during loading)
                fk_id_attr = field_name + '_id'
                fk_id = getattr(self, fk_id_attr, None)
                
                if fk_id is None and hasattr(self, field_name): # Check fk_id is still None
                    potential_related_obj = getattr(self, field_name)
                    if isinstance(potential_related_obj, field.to) and potential_related_obj.id is not None:
                         fk_id = potential_related_obj.id

                data[fk_id_attr] = fk_id
            else:
                # Regular field
                data[field_name] = getattr(self, field_name, None)

        # Handle M2M fields
        for field_name in self._many_to_many: # Iterate through field names
            # M2M relationships require the instance to have an ID
            if self.id is not None:
                try:
                    # Get the manager instance for this field on this specific object
                    # Accessing self.<field_name> (e.g., self.courses) triggers the descriptor's __get__
                    manager = getattr(self, field_name)

                    # Call the manager's all() method, which returns a QuerySet
                    related_queryset = manager.all()

                    # Extract the IDs from the related instances in the QuerySet
                    data[field_name] = [instance.id for instance in related_queryset if instance.id is not None]
                except Exception as e:
                    # Handle potential errors during M2M fetch gracefully
                    print(f"Warning: Could not fetch M2M field '{field_name}' for {self}: {e}")
                    data[field_name] = [] # Represent as empty list on error
            else:
                # If the instance isn't saved, it can't have M2M relations yet
                data[field_name] = [] # Represent as empty list

        return data

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
                ref_table = field.to.__name__.lower()  # get referenced table
                # delete everything if id deleted
                fields_sql.append(
                    f"{column_name} {field.db_type} REFERENCES {ref_table}(id) ON DELETE CASCADE")
            else:
                fields_sql.append(f"{field_name} {field.db_type}")
        cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor_obj.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(fields_sql)});")

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

    # TODO: M2M and insert entries are separate functions. Merge them.
    @classmethod
    def _validate_insert_input(cls, entries) -> bool:
        """
        Validate the list of entries for insertion.
        
        Returns True if entries are dictionaries, False if they are model instances.
        Raises TypeError if entries are neither dictionaries nor model instances.
        """
        if not entries:
            print("No entries provided to insert.")
            return None, None # Indicate no processing needed

        first_entry = entries[0]
        is_dict_input = isinstance(first_entry, dict)
        is_model_instance_input = isinstance(first_entry, BaseModel)

        if not is_dict_input and not is_model_instance_input:
             raise TypeError("Entries must be a list of dictionaries or BaseModel instances.")

        # Check type consistency
        for entry in entries:
            if is_dict_input and not isinstance(entry, dict):
                raise TypeError("All entries must be dictionaries.")
            if is_model_instance_input and not isinstance(entry, BaseModel):
                raise TypeError("All entries must be BaseModel instances.")
            if is_model_instance_input and not isinstance(entry, cls):
                 raise TypeError(f"All entries must be instances of {cls.__name__}")

        return is_dict_input

    @classmethod
    def _prepare_insert_sql(cls):
        """Prepare SQL query components for insertion."""
        field_names_db = []
        field_names_model = []
        for field_name, field in cls._fields.items():
            field_names_model.append(field_name)
            if isinstance(field, (ForeignKey, OneToOneField)):
                field_names_db.append(field_name + "_id")
            else:
                field_names_db.append(field_name)

        placeholders = ", ".join(["?" for _ in field_names_db])
        columns = ", ".join(field_names_db)
        query = f"INSERT INTO {cls.__name__.lower()} ({columns}) VALUES ({placeholders})"
        return field_names_model, field_names_db, query

    @classmethod
    def _extract_value_for_db(cls, entry, model_field_name, field, is_dict_input):
        """Extract and process a single value from an entry for DB insertion."""
        value = None
        if is_dict_input:
            raw_value = entry.get(model_field_name)
            if isinstance(field, (ForeignKey, OneToOneField)):
                if isinstance(raw_value, dict):
                    value = raw_value.get('id')
                elif isinstance(raw_value, BaseModel):
                     value = getattr(raw_value, 'id', None)
                else: # Assume it's the ID
                    value = raw_value
            else:
                value = raw_value
        else: # is_model_instance_input
            raw_value = getattr(entry, model_field_name, None)
            if isinstance(field, (ForeignKey, OneToOneField)):
                value = getattr(raw_value, 'id', None) if raw_value else None
            else:
                value = raw_value
        return value

    @classmethod
    def _check_onetoone_constraint(cls, cursor_obj, db_field_name, model_field_name, value):
        """Check for OneToOne constraint violation."""
        check_query = f"SELECT COUNT(*) FROM {cls.__name__.lower()} WHERE {db_field_name} = ?"
        cursor_obj.execute(check_query, (value,))
        if cursor_obj.fetchone()[0] > 0:
            raise ValueError(
                f"Duplicate entry detected for {model_field_name} (OneToOneField) with id {value}")

    @classmethod
    def _process_entries_for_values(cls, entries, is_dict_input, field_names_model, field_names_db, cursor_obj):
        """Process all entries to generate the list of value tuples for executemany."""
        values = []
        for entry in entries:
            row = []
            for model_field_name, db_field_name in zip(field_names_model, field_names_db):
                field = cls._fields[model_field_name]
                value = cls._extract_value_for_db(entry, model_field_name, field, is_dict_input)
                if isinstance(field, OneToOneField) and value is not None:
                    try:
                        cls._check_onetoone_constraint(cursor_obj, db_field_name, model_field_name, value)
                    except ValueError as e:
                        # Re-raise with more context or handle as needed
                        raise ValueError(f"Error processing entry {entry}: {e}") from e

                row.append(value)
            values.append(tuple(row))
        return values

    @classmethod
    def _execute_insert(cls, connection_obj, cursor_obj, query, entries, values_list, is_dict_input):
        """
        Execute the insert query and handle commit/rollback.
        Updates instance IDs if inserting model instances one by one.
        """
        try:
            if is_dict_input:
                # Use executemany for dictionary inputs (bulk insert)
                cursor_obj.executemany(query, values_list)
                print(f"Successfully inserted {len(values_list)} entries into {cls.__name__}")
            else:
                # Insert instances one by one to get lastrowid
                inserted_count = 0
                for i, entry_instance in enumerate(entries):
                    values_tuple = values_list[i] # Get the pre-processed values for this instance
                    cursor_obj.execute(query, values_tuple)
                    # Get the last inserted ID and update the instance
                    last_id = cursor_obj.lastrowid
                    entry_instance.id = last_id
                    inserted_count += 1
                print(f"Successfully inserted {inserted_count} entries into {cls.__name__} and updated instance IDs.")

            connection_obj.commit()

        except Exception as e:
            connection_obj.rollback()
            print(f"Error during insert into {cls.__name__}: {e}") # Log or print error
            raise # Re-raise the exception after rollback

    @classmethod
    def insert_entries(cls, entries):
        is_dict_input = cls._validate_insert_input(entries)
        if is_dict_input is None: # Handle case where entries list is empty
             print("No entries to insert.")
             return

        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")

        connection_obj = None # Initialize to None for finally block
        try:
            connection_obj = sqlite3.connect(DB_PATH)
            cursor_obj = connection_obj.cursor()
            cursor_obj.execute("PRAGMA foreign_keys = ON;")

            field_names_model, field_names_db, query = cls._prepare_insert_sql()

            # Process entries to get values list (needed for both dicts and instances)
            values_list = cls._process_entries_for_values(
                entries, is_dict_input, field_names_model, field_names_db, cursor_obj
            )

            # Pass entries list along with values_list to _execute_insert
            cls._execute_insert(connection_obj, cursor_obj, query, entries, values_list, is_dict_input)

        except Exception as e:
            # Catch potential errors during validation, SQL prep, or processing
            if connection_obj:
                try:
                    connection_obj.rollback()
                except Exception as rb_e:
                    print(f"Error during rollback: {rb_e}") # Log rollback error
            print(f"Failed to insert entries into {cls.__name__}: {e}") # Log or print error
            # Re-raise the original exception to signal failure
            raise
        finally:
            if connection_obj:
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
            where_clause = " AND ".join(
                [f"{field} = ?" for field in conditions.keys()])
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
            print(
                "Error: You must provide at least one condition to update specific rows.")
            return
        if not new_values:
            print("Error: No new values provided to update.")
            return
        set_clause = ", ".join([f"{field} = ?" for field in new_values.keys()])
        where_clause = " AND ".join(
            [f"{field} = ?" for field in conditions.keys()])
        query = f"UPDATE {cls.__name__.lower()} SET {set_clause} WHERE {where_clause}"
        values = tuple(new_values.values()) + tuple(conditions.values())
        try:
            cursor_obj.execute(query, values)
            connection_obj.commit()
            print(
                f"Updated entries in {cls.__name__} where {conditions} with {new_values}")
        except Exception as e:
            print(f"Error updating entries: {e}")
        finally:
            connection_obj.close()