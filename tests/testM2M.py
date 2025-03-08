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

class CustomBook(model.BaseModel):
    title = datatypes.CharField()
    authors = model.ManyToManyField(Author, through="customjunction")


class TestManyToManyRelationships(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create tables
        Author.create_table()
        Book.create_table()
        CustomBook.create_table()

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
        """Clean up all tables before each test."""
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("DELETE FROM book_author")
        cursor_obj.execute("DELETE FROM customjunction")
        cursor_obj.execute("DELETE FROM author")
        cursor_obj.execute("DELETE FROM book")
        cursor_obj.execute("DELETE FROM custombook")
        connection_obj.commit()
        connection_obj.close()
        
        # Reinsert base data
        Author.insert_entries([
            {"name": "J.K. Rowling"},
            {"name": "George Orwell"},
            {"name": "Agatha Christie"}
        ])
        Book.insert_entries([
            {"title": "Harry Potter"},
            {"title": "1984"}
        ])

    
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
    
    def test_m2m_cascade_delete_source(self):
        """Test M2M relationships are deleted when source is deleted."""
        # Add relationship
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")
        Book.add_m2m('authors', harry_potter, rowling)

        # Delete source record
        Book.delete_entries(harry_potter)

        # Verify relationships are gone
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM book_author WHERE book_id = ?", (harry_potter["id"],))
        self.assertEqual(len(cursor_obj.fetchall()), 0)
        connection_obj.close()

    def test_m2m_cascade_delete_target(self):
        """Test M2M relationships are deleted when target is deleted."""
        # Add relationship
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")
        Book.add_m2m('authors', harry_potter, rowling)

        # Delete target record
        Author.delete_entries(rowling)

        # Verify relationships are gone
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM book_author WHERE author_id = ?", (rowling["id"],))
        self.assertEqual(len(cursor_obj.fetchall()), 0)
        connection_obj.close()

    def test_m2m_custom_junction_table(self):
        """Test M2M relationships with custom junction table."""
        # Create records
        rowling = Author.objects.get(name="J.K. Rowling")
        CustomBook.insert_entries([{"title": "Custom Book"}])
        custom_book = CustomBook.objects.get(title="Custom Book")
        # Add relationship
        CustomBook.add_m2m('authors', custom_book, rowling)

        # Verify relationship exists in custom table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM customjunction")
        self.assertEqual(len(cursor_obj.fetchall()), 1)
        connection_obj.close()

    def test_m2m_invalid_relationship(self):
        """Test adding relationship with non-existent record."""
        invalid_author = {"id": 999, "name": "Invalid Author"}
        harry_potter = Book.objects.get(title="Harry Potter")

        with self.assertRaises(ValueError):
            Book.add_m2m('authors', harry_potter, invalid_author)

    def test_remove_nonexistent_relationship(self):
        """Test removing a relationship that doesn't exist."""
        rowling = Author.objects.get(name="J.K. Rowling")
        harry_potter = Book.objects.get(title="Harry Potter")

        # Should complete without errors
        Book.remove_m2m('authors', harry_potter, rowling)
        harry_authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(harry_authors), 0)

    def test_m2m_multiple_operations(self):
        """Test complex add/remove sequences."""
        rowling = Author.objects.get(name="J.K. Rowling")
        orwell = Author.objects.get(name="George Orwell")
        harry_potter = Book.objects.get(title="Harry Potter")

        # Add two authors
        Book.add_m2m('authors', harry_potter, rowling)
        Book.add_m2m('authors', harry_potter, orwell)
        self.assertEqual(len(Book.get_m2m('authors', harry_potter)), 2)

        # Remove one author
        Book.remove_m2m('authors', harry_potter, rowling)
        authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0]["name"], "George Orwell")

    def test_empty_relationships(self):
        """Test retrieving relationships when none exist."""
        harry_potter = Book.objects.get(title="Harry Potter")
        authors = Book.get_m2m('authors', harry_potter)
        self.assertEqual(len(authors), 0)

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()