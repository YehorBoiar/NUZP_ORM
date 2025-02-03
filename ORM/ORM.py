import sqlite3

import os


def create_table(table_object):
    if not os.path.exists('databases'):
        os.makedirs('databases')
    table_name = table_object.__name__
    connection_obj = sqlite3.connect('databases/' + table_object.__name__.lower() + '.sqlite3')
    
    for field_name, field in table_object._fields.items():
            print(f"{field_name} {field.db_type}")
    cursor_obj = connection_obj.cursor()
    fields_sql = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for field_name, field in table_object._fields.items():
        fields_sql.append(f"{field_name} {field.db_type}")
    

    cursor_obj.execute(f"DROP TABLE IF EXISTS {table_name}")
 
    cursor_obj.execute(f"CREATE TABLE IF NOT EXISTS {table_object.__name__.lower()} ({', '.join(fields_sql)});")
    
    connection_obj.close()