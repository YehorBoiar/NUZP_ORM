import sqlite3
from ORM.datatypes import Field

DB_PATH = "databases/main.sqlite3"

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
        If the relationship already exists or the target record is invalid, it will be skipped.
        """
        # Determine the junction table name
        source_class_name = source_class.__name__.lower()
        target_class_name = self.to.__name__.lower()
        junction_table = self.through or f"{source_class_name}_{target_class_name}"

        # Check if the target record exists in the target table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(f"""
            SELECT 1 FROM {target_class_name}
            WHERE id = ?
        """, (target_dict["id"],))
        target_exists = cursor_obj.fetchone()

        if not target_exists:
            # Target record does not exist, so we skip the insertion
            connection_obj.close()
            raise ValueError(
                f"Target record with id={target_dict['id']} does not exist in {target_class_name} table.")

        # Check if the relationship already exists in the junction table
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
