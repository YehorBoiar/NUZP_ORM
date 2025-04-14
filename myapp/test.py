from ORM import base
from ORM.datatypes import CharField
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Student(base.BaseModel):
    name = CharField()

class Course(base.BaseModel):
    title = CharField()
    students = base.ManyToManyField(Student)
