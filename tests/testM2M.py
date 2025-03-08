import unittest
import sqlite3
import os
from ORM import model, datatypes

DB_PATH = "databases/main.sqlite3"

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

    def setUp(self):
        """
        Set up before each test.
        """
        # Ensure the junction table is empty before each test
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("DELETE FROM book_author")
        connection_obj.commit()
        connection_obj.close()
    
    def test_add_m2m_relationship(self):
        """Test adding authors to a book."""
        # Retrieve records as dictionaries
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")

        # Add J.K. Rowling to Harry Potter
        Book.add_m2m('authors', harry_potter, rowling)

        # Retrieve authors for Harry Potter
        harry_authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(harry_authors), 1)
        self.assertEqual(harry_authors[0]["name"], "J.K. Rowling")

    def test_remove_m2m_relationship(self):
        """Test removing an author from a book."""
        # Retrieve records as dictionaries
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")

        # Add and then remove J.K. Rowling from Harry Potter
        Book.add_m2m('authors', harry_potter, rowling)
        Book.remove_m2m('authors', harry_potter, rowling)

        # Retrieve authors for Harry Potter
        harry_authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(harry_authors), 0)

    def test_m2m_relationship_uniqueness(self):
        """Test that the same relationship cannot be added twice."""
        # Retrieve records as dictionaries
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")

        # Add J.K. Rowling to Harry Potter twice
        Book.add_m2m('authors', harry_potter, rowling)
        Book.add_m2m('authors', harry_potter, rowling)

        # Retrieve authors for Harry Potter
        harry_authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(harry_authors), 1)  # Should only have one entry
    
    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()