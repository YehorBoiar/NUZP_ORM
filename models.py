import ORM
import datatypes
from model import ModelMeta

class Student(metaclass=ModelMeta):
    name = datatypes.CharField(255)
    bd = datatypes.DateTimeField()

ORM.create_table(Student)
