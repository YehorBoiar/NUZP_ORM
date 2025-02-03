from ORM.ORM import create_table, insert_entries, delete_entries, replace_entries
from ORM.datatypes import CharField, DateTimeField
from ORM.model import ModelMeta

students_to_add = [
    {"name": "Alice", "bd": "2000-01-01"},
    {"name": "Bob", "bd": "1999-05-15"},
    {"name": "Charlie", "bd": "2001-12-22"}
]

class Student(metaclass=ModelMeta):
    name = CharField()
    bd = DateTimeField()

create_table(Student)
insert_entries(Student, students_to_add)
delete_entries(Student, {"bd": "1999-05-15"})
replace_entries(Student, {"name": "Alice"}, {"bd": "2001-01-01"})
