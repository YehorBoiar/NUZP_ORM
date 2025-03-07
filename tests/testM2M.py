import unittest
import sqlite3
import os
from ORM import model, datatypes


class Author(model.BaseModel):
    name = datatypes.CharField()
    
class Book(model.BaseModel):
    title = datatypes.CharField()
    authors = model.ManyToManyField(to=Author)

class TestManyToManyRelationships(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create tables
        Author.create_table()
        Book.create_table()

        # Insert test data
        Author.insert_entries([
            {"name": "J.K. Rowling"},
            {"name": "George Orwell"},
            {"name": "Agatha Christie"}
        ])
        
        Book.insert_entries([
            {"title": "Harry Potter"},
            {"title": "1984"}
        ])


if __name__ == '__main__':
    unittest.main()