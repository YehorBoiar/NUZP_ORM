import sqlite3

import os


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

def insert_entries(model_class, entries):
    """
    Inserts multiple entries (rows) into the database table of a given model.

    :param model_class: The class (model) where entries should be added.
    :param entries: A list of dictionaries, where each dictionary represents a row.
    """
    if not hasattr(model_class, "_fields"):
        raise ValueError(f"{model_class.__name__} is not a valid model class.")

    # Ensure database and table exist
    db_path = f"databases/{model_class.__name__.lower()}.sqlite3"
    if not os.path.exists("databases"):
        raise ValueError(f"Table {model_class.__name__} doesn't exist")

    connection_obj = sqlite3.connect(db_path)
    cursor_obj = connection_obj.cursor()

    # Extract field names (excluding 'id' since it's auto-incremented)
    field_names = [field for field in model_class._fields.keys()]
    placeholders = ", ".join(["?" for _ in field_names])  # Generates "?, ?, ?" for SQL query
    columns = ", ".join(field_names)

    query = f"INSERT INTO {model_class.__name__.lower()} ({columns}) VALUES ({placeholders})"

    # Convert dictionary values to tuples for execution
    values = [tuple(entry[field] for field in field_names) for entry in entries]

    try:
        cursor_obj.executemany(query, values)
        connection_obj.commit()
        print(f"Successfully inserted {len(entries)} entries into {model_class.__name__}")
    except Exception as e:
        print(f"Error inserting entries: {e}")
    finally:
        connection_obj.close()

    