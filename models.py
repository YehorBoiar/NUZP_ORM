from ORM.ORM import create_table
from ORM.datatypes import CharField, DateTimeField
from ORM.model import ModelMeta

class Student(metaclass=ModelMeta):
    name = CharField()
    bd = DateTimeField()

create_table(Student)
