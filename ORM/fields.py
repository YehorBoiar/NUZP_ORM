import sqlite3
from ORM.datatypes import Field
from ORM.query import QuerySet


DB_PATH = "databases/main.sqlite3"

# ====================================================
# 2. Relationship Field Types
# ====================================================


class ManyToManyRelatedManager:
    """
    Manages M2M relationships for a specific instance.
    Accessed via a descriptor on the model instance (e.g., student.courses).
    """
    def __init__(self, instance, field):
        """
        Initialize the manager.

        Args:
            instance (BaseModel): The source model instance (e.g., a Student instance).
            field (ManyToManyField): The ManyToManyField descriptor instance.
        """
        self.instance = instance
        self.field = field
        self.source_class = instance.__class__
        self.target_class = field.to
        self.source_class_name = self.source_class.__name__.lower()
        self.target_class_name = self.target_class.__name__.lower()
        self.junction_table = field.through or f"{self.source_class_name}_{self.target_class_name}"

    def _check_instance_saved(self, operation="operate"):
        """Ensure the source instance is saved before performing relationship operations."""
        if self.instance.id is None:
            raise ValueError(f"Cannot {operation} on M2M relationship for an unsaved '{self.source_class_name}' instance.")

    def add(self, *target_objs):
        """
        Add one or more target objects to the relationship.
        """
        self._check_instance_saved("add")
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")
        try:
            for target_obj in target_objs:
                if not isinstance(target_obj, self.target_class):
                    raise TypeError(f"Can only add '{self.target_class.__name__}' instances.")
                if target_obj.id is None:
                    raise ValueError(f"Cannot add unsaved '{self.target_class_name}' instance to M2M relationship.")

                # Use INSERT OR IGNORE to handle potential UNIQUE constraint violations gracefully
                cursor_obj.execute(f"""
                    INSERT OR IGNORE INTO {self.junction_table} ({self.source_class_name}_id, {self.target_class_name}_id)
                    VALUES (?, ?)
                """, (self.instance.id, target_obj.id))
            connection_obj.commit()
        except sqlite3.IntegrityError as e:
             # Handle FK constraint violation if target_obj.id doesn't exist in target table
             if "FOREIGN KEY constraint failed" in str(e):
                 connection_obj.rollback()
                 # Find which object caused the error (simplified check)
                 offending_id = next((obj.id for obj in target_objs if obj.id is not None), 'unknown')
                 raise ValueError(f"Invalid target ID '{offending_id}' for M2M relationship.") from e
             else:
                 connection_obj.rollback()
                 raise e # Re-raise other IntegrityErrors
        except Exception as e:
            connection_obj.rollback()
            raise e
        finally:
            connection_obj.close()

    def remove(self, *target_objs):
        """
        Remove one or more target objects from the relationship.
        """
        self._check_instance_saved("remove")
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")
        try:
            for target_obj in target_objs:
                if not isinstance(target_obj, self.target_class):
                    raise TypeError(f"Can only remove '{self.target_class.__name__}' instances.")
                if target_obj.id is None:
                     # Cannot remove relationship if target ID is unknown
                     print(f"Warning: Cannot remove M2M relationship for unsaved '{self.target_class_name}' instance.")
                     continue

                cursor_obj.execute(f"""
                    DELETE FROM {self.junction_table}
                    WHERE {self.source_class_name}_id = ? AND {self.target_class_name}_id = ?
                """, (self.instance.id, target_obj.id))
            connection_obj.commit()
        except Exception as e:
            connection_obj.rollback()
            raise e
        finally:
            connection_obj.close()

    def clear(self):
        """Remove all relationships for this instance."""
        self._check_instance_saved("clear")
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")
        try:
            cursor_obj.execute(f"""
                DELETE FROM {self.junction_table}
                WHERE {self.source_class_name}_id = ?
            """, (self.instance.id,))
            connection_obj.commit()
        except Exception as e:
            connection_obj.rollback()
            raise e
        finally:
            connection_obj.close()

    def set(self, target_objs):
        """
        Replace the current set of related objects with the provided ones.
        """
        self._check_instance_saved("set")
        self.clear()
        if target_objs: # Only add if there are objects to add
            self.add(*target_objs)

    def all(self):
        """
        Retrieve all related target objects as a QuerySet.
        """
        self._check_instance_saved("retrieve")
        # Construct a QuerySet for the target model, filtered by the junction table
        target_ids_query = f"""
            SELECT {self.target_class_name}_id
            FROM {self.junction_table}
            WHERE {self.source_class_name}_id = ?
        """
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute(target_ids_query, (self.instance.id,))
        target_ids = [row[0] for row in cursor_obj.fetchall()]
        connection_obj.close()

        if not target_ids:
            # Return an empty QuerySet if no related objects
            return QuerySet(self.target_class).filter(id__in=[]) # Filter with empty list

        # Use the 'id__in' filter on the target model's manager
        return QuerySet(self.target_class).filter(id__in=target_ids)

    def filter(self, **kwargs):
        """Filter the set of related objects."""
        return self.all().filter(**kwargs)

    def get(self, **kwargs):
        """Get a single related object matching the criteria."""
        return self.all().get(**kwargs)

    def __iter__(self):
        """Allow iteration over related objects."""
        return iter(self.all())

    def __repr__(self):
        return f"<ManyToManyRelatedManager for {self.instance}>"


# ====================================================
# 2. Relationship Field Types
# ====================================================

class ManyToManyField:
    def __init__(self, to, through=None):
        self.to = to  # Target model class
        self.through = through  # Optional custom junction table
        # Store the name this field is assigned to on the model
        self.name = None # Will be set by ModelMeta

    def __set_name__(self, owner, name):
        # Called when the descriptor is assigned to the model class
        self.name = name

    def __get__(self, instance, owner):
        """
        Descriptor __get__ method. Returns the manager when accessed on an instance.
        """
        if instance is None:
            # Accessed on the class, maybe return a manager that works across all instances?
            # For now, let's return self or raise error, as instance access is primary goal.
            return self # Or raise AttributeError("M2M field can only be accessed via an instance")

        # Check if a manager instance is already cached on the instance
        # Use a private attribute name based on the field name
        manager_attr = f"_{self.name}_manager"
        if not hasattr(instance, manager_attr):
            # Create and cache the manager instance
            setattr(instance, manager_attr, ManyToManyRelatedManager(instance, self))
        return getattr(instance, manager_attr)


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
