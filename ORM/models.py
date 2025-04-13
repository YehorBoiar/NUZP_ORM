import os
import sys
import importlib
import inspect
import argparse
from pathlib import Path

from ORM.model import BaseModel

def find_models(project_root, models_folder='myapp'):
    """Find all model classes in the specified folder that inherit from BaseModel."""
    models = []
    
    # Construct the path to the models folder
    models_path = os.path.join(project_root, models_folder)
    
    # Check if the folder exists
    if not os.path.exists(models_path):
        print(f"The folder '{models_folder}' does not exist in the project root.")
        return models
    
    # Walk only through the models folder
    for root, dirs, files in os.walk(models_path):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(root, file)
                module_path = os.path.relpath(file_path, project_root).replace('/', '.').replace('\\', '.')[:-3]
                
                print(f"Examining {file_path} -> module path: {module_path}")
                
                try:
                    # Import the module
                    module = importlib.import_module(module_path)
                    
                    # Find model classes in the module
                    classes_found = False
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj):
                            print(f"  Found class: {name}")
                            if issubclass(obj, BaseModel) and obj != BaseModel:
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
    migrations_dir = Path('migrations')
    migrations_dir.mkdir(exist_ok=True)
    
    # Get the next migration number
    existing_migrations = [f for f in migrations_dir.glob('????_*.py')]
    next_number = 1
    if existing_migrations:
        latest = max(existing_migrations)
        next_number = int(latest.name[:4]) + 1
    
    # Create a migration file with timestamp and sequential number
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    migration_file = migrations_dir / f"{next_number:04d}_migration_{timestamp}.py"
    
    with open(migration_file, 'w') as f:
        f.write(f"# Auto-generated migration file\n\n")
        f.write("def migrate():\n")
        
        for model in models:
            f.write(f"    # Create table for {model.__name__}\n")
            f.write(f"    from {model.__module__} import {model.__name__}\n")
            f.write(f"    {model.__name__}.create_table()\n\n")
    
    print(f"Generated migration file: {migration_file}")

def apply_migrations():
    """Apply all migrations in sequential order."""
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
    
    for migration_file in migration_files:
        module_name = migration_file.stem
        try:
            print(f"Applying migration: {module_name}")
            migration_module = importlib.import_module(f'migrations.{module_name}')
            migration_module.migrate()
            print(f"Migration {module_name} applied successfully!")
        except Exception as e:
            print(f"Error applying migration {module_name}: {e}")
            break

def main():
    parser = argparse.ArgumentParser(description='ORM CLI for database management')
    parser.add_argument('command', choices=['generate', 'migrate'], 
                        help='Command to execute (generate: create migrations, migrate: apply migrations)')
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
        
        print(f"Found {len(models)} model(s) in '{args.app}': {', '.join(model.__name__ for model in models)}")
        generate_migrations(models)
    
    elif args.command == 'migrate':
        apply_migrations()

if __name__ == '__main__':
    main()