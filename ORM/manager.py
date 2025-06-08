"""
Provides command-line utilities for managing database migrations,
including generating, applying, and showing migration status.
"""
import sqlite3
import os
import sys
import importlib
import inspect
import argparse
from pathlib import Path

from ORM.base import BaseModel, DB_PATH


def find_models(project_root, models_folder='myapp'):
    """Find all model classes in the specified folder that inherit from BaseModel."""
    models = []

    # Construct the path to the models folder
    models_path = os.path.join(project_root, models_folder)

    # Check if the folder exists
    if not os.path.exists(models_path):
        print(
            f"The folder '{models_folder}' does not exist in the project root.")
        return models

    # Walk only through the models folder
    for root, dirs, files in os.walk(models_path):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(root, file)
                module_path = os.path.relpath(file_path, project_root).replace(
                    '/', '.').replace('\\', '.')[:-3]

                print(f"Examining {file_path} -> module path: {module_path}")

                try:
                    # Import the module
                    module = importlib.import_module(module_path)

                    # Find model classes in the module
                    classes_found = False
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseModel)
                            and obj != BaseModel
                            and obj.__module__ == module.__name__ 
                        ):
                            print(f"  --> {name} is a model!")
                            models.append(obj)
                            classes_found = True

                    if not classes_found:
                        print(f"  No model classes found in {file_path}")

                except (ImportError, ModuleNotFoundError) as e:
                    print(f"  Error importing {module_path}: {e}")
                except Exception as e:
                    print(f"  Unexpected error with {module_path}: {e}")

    return models

def generate_migrations(models):
    """Generate versioned migration files for all models."""
    if not models:
        print("No models provided. Skipping migration generation.")
        return

    migrations_dir = Path('migrations')
    migrations_dir.mkdir(exist_ok=True)

    # Get the next migration number
    existing_migrations = [f for f in migrations_dir.glob('????_*.py')]
    next_number = 1
    if existing_migrations:
        latest = max(existing_migrations)
        next_number = int(latest.name[:4]) + 1

    # Enhanced model change detection
    from hashlib import sha256

    # Create detailed signatures that include field information
    model_signatures = {}
    for model in models:
        # Capture basic model info
        model_info = f"{model.__name__}:{model.__module__}"

        # Add regular fields
        fields_info = []
        for field_name, field in model._fields.items():
            # Get field type
            field_type = type(field).__name__

            # Get field attributes
            attrs = {}
            for attr_name in ['db_type', 'null', 'unique', 'default']:
                if hasattr(field, attr_name):
                    attrs[attr_name] = getattr(field, attr_name)

            # For foreign key fields, include target model
            if hasattr(field, 'to'):
                attrs['to'] = field.to.__name__

            # Create field signature
            field_signature = f"{field_name}:{field_type}:{attrs}"
            fields_info.append(field_signature)

        # Add many-to-many fields if present
        if hasattr(model, '_many_to_many'):
            for field_name, field in model._many_to_many.items():
                field_type = "ManyToManyField"
                attrs = {
                    'to': field.to.__name__,
                }
                if field.through:
                    attrs['through'] = field.through

                field_signature = f"{field_name}:{field_type}:{attrs}"
                fields_info.append(field_signature)

        # Create complete model signature
        model_signature = f"{model_info}:{','.join(sorted(fields_info))}"
        model_signatures[model.__name__] = sha256(
            model_signature.encode()).hexdigest()

    # Load the last migration's signature if it exists
    signature_file = migrations_dir / 'last_signature.txt'
    if signature_file.exists():
        with open(signature_file, 'r') as f:
            last_signature = f.read().strip()
        current_signature = sha256(str(model_signatures).encode()).hexdigest()

        if last_signature == current_signature:
            print("No changes detected in models. Skipping migration generation.")
            return
    else:
        current_signature = sha256(str(model_signatures).encode()).hexdigest()

    # Create a migration file with timestamp and sequential number
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    migration_file = migrations_dir / \
        f"{next_number:04d}_migration_{timestamp}.py"

    with open(migration_file, 'w') as f:
        f.write(f"# Auto-generated migration file\n\n")
        f.write("def migrate():\n")

        for model in models:
            f.write(f"    # Create table for {model.__name__}\n")
            f.write(f"    from {model.__module__} import {model.__name__}\n")
            f.write(f"    {model.__name__}.create_table()\n\n")

    # Save the current signature
    with open(signature_file, 'w') as f:
        f.write(current_signature)

    print(f"Generated migration file: {migration_file}")


def create_migrations_table():
    """Create a table to track applied migrations if it doesn't exist."""
    # Ensure databases directory exists
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orm_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()
    print("Migration tracking table ensured.")


def record_migration(migration_name):
    """Record that a migration has been applied."""
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO orm_migrations (migration_name) VALUES (?)", (migration_name,))
        connection.commit()
        print(f"Recorded migration: {migration_name}")
    except sqlite3.IntegrityError:
        # Migration already recorded (unique constraint)
        print(f"Migration {migration_name} already recorded.")
    except Exception as e:
        print(f"Error recording migration {migration_name}: {e}")
    finally:
        connection.close()


def get_applied_migrations():
    """Get a list of migrations that have already been applied."""
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute("SELECT migration_name FROM orm_migrations ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]
        connection.close()
        return applied
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return []
    except Exception as e:
        print(f"Error retrieving applied migrations: {e}")
        return []


def apply_migrations(specific_migration=None):
    """Apply all migrations or a specific migration in sequential order."""
    # Ensure migrations table exists
    create_migrations_table()

    # Get list of applied migrations
    applied_migrations = get_applied_migrations()
    print(f"Already applied migrations: {', '.join(applied_migrations) if applied_migrations else 'None'}")

    migrations_dir = Path('migrations')
    if not migrations_dir.exists():
        print("No migrations directory found. Run 'generate' first.")
        return

    # Get all migration files in sorted order
    migration_files = sorted(migrations_dir.glob('????_*.py'))
    if not migration_files:
        print("No migration files found. Run 'generate' first.")
        return

    sys.path.insert(0, str(migrations_dir.parent))

    # If applying a specific migration
    if specific_migration:
        migration_file = next((f for f in migration_files if f.stem == specific_migration), None)
        if not migration_file:
            print(f"Migration '{specific_migration}' not found.")
            return
            
        # Skip if already applied
        if specific_migration in applied_migrations:
            print(f"Migration {specific_migration} already applied, skipping.")
            return
            
        try:
            print(f"Applying specific migration: {specific_migration}")
            migration_module = importlib.import_module(f'migrations.{specific_migration}')
            migration_module.migrate()
            # Record the migration as applied
            record_migration(specific_migration)
            print(f"Migration {specific_migration} applied successfully!")
        except Exception as e:
            print(f"Error applying migration {specific_migration}: {e}")
            raise  # Re-raise the exception for test cases
        return

    # Apply all migrations in sequence
    for migration_file in migration_files:
        module_name = migration_file.stem

        # Skip if already applied
        if module_name in applied_migrations:
            print(f"Migration {module_name} already applied, skipping.")
            continue

        try:
            print(f"Applying migration: {module_name}")
            migration_module = importlib.import_module(f'migrations.{module_name}')
            migration_module.migrate()
            # Record the migration as applied
            record_migration(module_name)
            print(f"Migration {module_name} applied successfully!")
        except Exception as e:
            print(f"Error applying migration {module_name}: {e}")
            raise  # Re-raise the exception for test cases


def show_migrations():
    """Display migration status - which are applied and which are pending."""
    applied_migrations = get_applied_migrations()

    migrations_dir = Path('migrations')
    if not migrations_dir.exists():
        print("No migrations directory found.")
        return

    migration_files = sorted(migrations_dir.glob('????_*.py'))
    if not migration_files:
        print("No migration files found.")
        return

    print("\nMigration status:")
    print("-" * 50)
    for migration_file in migration_files:
        name = migration_file.stem
        status = "[X]" if name in applied_migrations else "[ ]"
        print(f"{status} {name}")
    print("-" * 50)


def main():
    """
    Parses command-line arguments and executes the corresponding
    migration command (generate, migrate, showmigrations).
    """
    parser = argparse.ArgumentParser(
        description='ORM CLI for database management')
    parser.add_argument('command', choices=['generate', 'migrate', 'showmigrations'],
                        help='Command to execute (generate: create migrations, migrate: apply migrations, showmigrations: list migration status)')
    parser.add_argument('--app', default='myapp',
                        help='Specific app folder to search for models (default: myapp)')

    args = parser.parse_args()

    # Get the project root (one level up from the ORM package)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.command == 'generate':
        models = find_models(project_root, args.app)
        if not models:
            print(f"No models found in the '{args.app}' folder.")
            return

        print(
            f"Found {len(models)} model(s) in '{args.app}': {', '.join(model.__name__ for model in models)}")
        generate_migrations(models)

    elif args.command == 'migrate':
        apply_migrations()

    elif args.command == 'showmigrations':
        show_migrations()


if __name__ == '__main__':
    main()
