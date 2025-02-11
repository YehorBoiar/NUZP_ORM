from ORM.datatypes import Field, IntegerField, CharField
from ORM.model import BaseModel

class User(BaseModel):
    name = CharField()
    age = IntegerField()

# Create the table (drops if exists, for demo)
User.create_table()

# Insert some entries
User.insert_entries([
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35},
])

# Querying examples:
# Get all users
all_users = User.objects.all()
print(all_users)

# Filter users by name
alice = User.objects.filter(name="Alice").all()
print(alice)

# Get a single record (raises error if not exactly one match)
try:
    bob = User.objects.get(name="Bob")
    print(bob)
except Exception as e:
    print(e)

# Order results
ordered_users = User.objects.order_by("-age").all()
print(ordered_users)

# Slicing (e.g., get the first two users)
first_two = User.objects.all()[0:2]
print(first_two)
