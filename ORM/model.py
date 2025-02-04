from ORM.datatypes import Field
import os
import sqlite3


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

class BaseModel(metaclass=ModelMeta):
    @classmethod
    def create_table(table_object):
        if not os.path.exists('databases'):
            os.makedirs('databases')
        table_name = table_object.__name__
        connection_obj = sqlite3.connect('databases/' + table_object.__name__.lower() + '.sqlite3')
        
        cursor_obj = connection_obj.cursor()
        fields_sql = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for field_name, field in table_object._fields.items():
            fields_sql.append(f"{field_name} {field.db_type}")
        

        cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
    
        cursor_obj.execute(f"CREATE TABLE IF NOT EXISTS {table_object.__name__.lower()} ({', '.join(fields_sql)});")
        
        connection_obj.close()
    @classmethod
    def insert_entries(self, entries):
        """
        Inserts multiple entries (rows) into the database table of a given model.

        :param entries: A list of dictionaries, where each dictionary represents a row.
        """
        if not hasattr(self, "_fields"):
            raise ValueError(f"{self.__name__} is not a valid model class.")

        # Ensure database and table exist
        db_path = f"databases/{self.__name__.lower()}.sqlite3"
        if not os.path.exists("databases"):
            raise ValueError(f"Table {self.__name__} doesn't exist")

        connection_obj = sqlite3.connect(db_path)
        cursor_obj = connection_obj.cursor()

        # Extract field names (excluding 'id' since it's auto-incremented)
        field_names = [field for field in self._fields.keys()]
        placeholders = ", ".join(["?" for _ in field_names])  # Generates "?, ?, ?" for SQL query
        columns = ", ".join(field_names)

        query = f"INSERT INTO {self.__name__.lower()} ({columns}) VALUES ({placeholders})"

        # Convert dictionary values to tuples for execution
        values = [tuple(entry[field] for field in field_names) for entry in entries]

        try:
            cursor_obj.executemany(query, values)
            connection_obj.commit()
            print(f"Successfully inserted {len(entries)} entries into {self.__name__}")
        except Exception as e:
            print(f"Error inserting entries: {e}")
        finally:
            connection_obj.close()

    @classmethod
    def delete_entries(self, conditions):
        """
        Deletes entries from the database table of a given model based on conditions.

        :param self: The class (model) from which entries should be deleted.
        :param conditions: A dictionary of conditions (e.g., {"name": "Alice"}) to match entries.
        """
        if not hasattr(self, "_fields"):
            raise ValueError(f"{self.__name__} is not a valid model class.")

        # Ensure database exists
        db_path = f"databases/{self.__name__.lower()}.sqlite3"
        if not os.path.exists(db_path):
            raise ValueError(f"Database for {self.__name__} does not exist!")

        connection_obj = sqlite3.connect(db_path)
        cursor_obj = connection_obj.cursor()

        # If no conditions are given, delete ALL rows (DANGEROUS!)
        if not conditions:
            confirmation = input(f"Are you sure you want to delete ALL records from {self.__name__}? (yes/no): ")
            if confirmation.lower() == "no":
                print("Deletion cancelled.")
                return
            query = f"DELETE FROM {self.__name__.lower()}"
            cursor_obj.execute(query)
        else:
            # Construct the WHERE clause dynamically
            where_clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])
            query = f"DELETE FROM {self.__name__.lower()} WHERE {where_clause}"
            values = tuple(conditions.values())

            cursor_obj.execute(query, values)

        connection_obj.commit()
        print(f"Deleted entries from {self.__name__} where {conditions}")
        connection_obj.close()

    @classmethod
    def replace_entries(self, conditions, new_values):
        """
        Updates (replaces) entries in the database table of a given model based on conditions.

        :param model_class: The class (model) where entries should be updated.
        :param conditions: A dictionary of conditions (e.g., {"name": "Alice"}) to match entries.
        :param new_values: A dictionary of new values to update (e.g., {"bd": "2001-01-01"}).
        """
        if not hasattr(self, "_fields"):
            raise ValueError(f"{self.__name__} is not a valid model class.")

        # Ensure database exists
        db_path = f"databases/{self.__name__.lower()}.sqlite3"
        if not os.path.exists(db_path):
            raise ValueError(f"Database for {self.__name__} does not exist!")

        connection_obj = sqlite3.connect(db_path)
        cursor_obj = connection_obj.cursor()

        # Ensure there are conditions (to avoid updating all rows accidentally)
        if not conditions:
            print("Error: You must provide at least one condition to update specific rows.")
            return

        # Ensure there are values to update
        if not new_values:
            print("Error: No new values provided to update.")
            return

        # Construct the SET clause dynamically
        set_clause = ", ".join([f"{field} = ?" for field in new_values.keys()])
        where_clause = " AND ".join([f"{field} = ?" for field in conditions.keys()])

        query = f"UPDATE {self.__name__.lower()} SET {set_clause} WHERE {where_clause}"
        values = tuple(new_values.values()) + tuple(conditions.values())

        try:
            cursor_obj.execute(query, values)
            connection_obj.commit()
            print(f"Updated entries in {self.__name__} where {conditions} with {new_values}")
        except Exception as e:
            print(f"Error updating entries: {e}")
        finally:
            connection_obj.close()