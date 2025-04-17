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
        # Initialize all defined fields to None or their default
        for field_name in self._fields:
            setattr(self, field_name, None)
        # Also initialize M2M fields (though they won't store simple values)
        for field_name in self._many_to_many:
             setattr(self, field_name, None) # Or perhaps an empty manager/list later

        # Assign provided keyword arguments to attributes
        for key, value in kwargs.items():
            if key == 'id':
                self.id = value
            elif key in self._fields or key in self._many_to_many:
                setattr(self, key, value)
            else:
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}' corresponding to a model field")

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
    def insert_entries(cls, entries):
        if not entries:
            print("No entries provided to insert.")
            return # Nothing to insert

        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database for {cls.__name__} does not exist!")

        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")

        field_names_db = [] # Field names as they appear in the DB (e.g., 'author_id')
        field_names_model = [] # Field names as they appear in the Model (e.g., 'author')

        for field_name, field in cls._fields.items():
            field_names_model.append(field_name)
            if isinstance(field, (ForeignKey, OneToOneField)):
                field_names_db.append(field_name + "_id")
            else:
                field_names_db.append(field_name)

        placeholders = ", ".join(["?" for _ in field_names_db])
        columns = ", ".join(field_names_db)
        query = f"INSERT INTO {cls.__name__.lower()} ({columns}) VALUES ({placeholders})"

        values = []
        first_entry = entries[0]
        is_dict_input = isinstance(first_entry, dict)
        is_model_instance_input = isinstance(first_entry, BaseModel)

        if not is_dict_input and not is_model_instance_input:
             connection_obj.close()
             raise TypeError("Entries must be a list of dictionaries or BaseModel instances.")

        for entry in entries:
            row = []
            # Ensure all entries are of the same type as the first one
            if is_dict_input and not isinstance(entry, dict):
                connection_obj.close()
                raise TypeError("All entries must be dictionaries.")
            if is_model_instance_input and not isinstance(entry, BaseModel):
                connection_obj.close()
                raise TypeError("All entries must be BaseModel instances.")
            if is_model_instance_input and not isinstance(entry, cls):
                 connection_obj.close()
                 raise TypeError(f"All entries must be instances of {cls.__name__}")


            for model_field_name, db_field_name in zip(field_names_model, field_names_db):
                field = cls._fields[model_field_name]
                value = None

                if is_dict_input:
                    raw_value = entry.get(model_field_name) # Use .get for safety
                    if isinstance(field, (ForeignKey, OneToOneField)):
                        # Handle dicts, instances, or direct IDs passed in the dictionary
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
                        # Get the id from the related model instance
                        value = getattr(raw_value, 'id', None) if raw_value else None
                    else:
                        value = raw_value

                # OneToOne check (applies to both dict and instance inputs)
                if isinstance(field, OneToOneField) and value is not None:
                    check_query = f"SELECT COUNT(*) FROM {cls.__name__.lower()} WHERE {db_field_name} = ?"
                    cursor_obj.execute(check_query, (value,))
                    if cursor_obj.fetchone()[0] > 0:
                        connection_obj.rollback() # Rollback before raising
                        connection_obj.close()
                        raise ValueError(
                            f"Duplicate entry detected for {model_field_name} (OneToOneField) with id {value}")

                row.append(value)

            values.append(tuple(row))
        try:
            cursor_obj.executemany(query, values)
            connection_obj.commit()
            print(
                f"Successfully inserted {len(entries)} entries into {cls.__name__}")
        except Exception as e:
            connection_obj.rollback() # Rollback on error
            raise # Re-raise the exception
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
