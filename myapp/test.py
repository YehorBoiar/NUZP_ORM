from ORM import model
from ORM.datatypes import CharField
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Student(model.BaseModel):
    name = CharField()
