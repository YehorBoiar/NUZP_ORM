from ORM.datatypes import CharField, DateTimeField
from ORM.model import BaseModel

class Student(BaseModel):
    name = CharField()
    bd = DateTimeField()

class Course(BaseModel):
    title = CharField()
    instructor = CharField()

Student.create_table()
Course.create_table()

students_to_add = [
    {"name": "Alice", "bd": "2000-01-01"},
    {"name": "Bob", "bd": "1999-05-15"},
    {"name": "Charlie", "bd": "2001-12-22"},
    {"name": "David", "bd": "1998-03-10"}
]

Student.insert_entries(students_to_add)

courses_to_add = [
    {"title": "Math 101", "instructor": "Dr. Smith"},
    {"title": "History 202", "instructor": "Prof. Johnson"},
    {"title": "Physics 303", "instructor": "Dr. Brown"}
]

Course.insert_entries(courses_to_add)