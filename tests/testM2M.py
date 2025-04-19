import unittest
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes
# Import QuerySet to check return types if needed
from ORM.query import QuerySet

DB_PATH = "databases/main.sqlite3"

class Author(base.BaseModel):
    name = datatypes.CharField()

class Book(base.BaseModel):
    title = datatypes.CharField()
    authors = base.ManyToManyField(to=Author)

class CustomBook(base.BaseModel):
    title = datatypes.CharField()
    authors = base.ManyToManyField(Author, through="customjunction")


class TestManyToManyRelationships(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create tables only once
        if not os.path.exists('databases'):
            os.makedirs('databases')
        Author.create_table()
        Book.create_table()
        CustomBook.create_table() # Ensure custom junction table is created

    def setUp(self):
        """Clean up tables and insert fresh base data using instances before each test."""
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("PRAGMA foreign_keys = ON;")
        # Clear junction tables first
        try: cursor_obj.execute("DELETE FROM book_author")
        except sqlite3.OperationalError: pass # Ignore if table doesn't exist yet
        try: cursor_obj.execute("DELETE FROM customjunction")
        except sqlite3.OperationalError: pass # Ignore if table doesn't exist yet
        # Clear main tables
        cursor_obj.execute("DELETE FROM author")
        cursor_obj.execute("DELETE FROM book")
        cursor_obj.execute("DELETE FROM custombook")
        # Reset sequences
        try:
            cursor_obj.execute("DELETE FROM sqlite_sequence WHERE name IN ('author', 'book', 'custombook')")
        except sqlite3.OperationalError: pass # Ignore if sequence table doesn't exist
        connection_obj.commit()
        connection_obj.close()

        # Reinsert base data using instances (IDs will be updated)
        self.rowling = Author(name="J.K. Rowling")
        self.orwell = Author(name="George Orwell")
        self.christie = Author(name="Agatha Christie")
        Author.insert_entries([self.rowling, self.orwell, self.christie])

        self.harry_potter = Book(title="Harry Potter")
        self.nineteen_eighty_four = Book(title="1984")
        Book.insert_entries([self.harry_potter, self.nineteen_eighty_four])

    def test_add_m2m_relationship(self):
        """Test adding authors to a book using instance manager."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter

        # Add J.K. Rowling to Harry Potter using the instance manager
        harry_potter.authors.add(rowling)

        # Retrieve authors for Harry Potter (should return Author instances via QuerySet)
        harry_authors_qs = harry_potter.authors.all()
        self.assertIsInstance(harry_authors_qs, QuerySet)
        harry_authors = list(harry_authors_qs) # Execute QuerySet
        self.assertEqual(len(harry_authors), 1)
        self.assertIsInstance(harry_authors[0], Author)
        self.assertEqual(harry_authors[0].name, "J.K. Rowling")
        self.assertEqual(harry_authors[0].id, rowling.id)

    def test_remove_m2m_relationship(self):
        """Test removing an author from a book using instance manager."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter

        # Add and then remove J.K. Rowling from Harry Potter
        harry_potter.authors.add(rowling)
        harry_potter.authors.remove(rowling)

        # Retrieve authors for Harry Potter
        harry_authors = list(harry_potter.authors.all())
        self.assertEqual(len(harry_authors), 0)

    def test_m2m_relationship_uniqueness(self):
        """Test that the same relationship cannot be added twice via manager."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter

        # Add J.K. Rowling to Harry Potter twice (second add should be ignored)
        harry_potter.authors.add(rowling)
        harry_potter.authors.add(rowling) # Should be ignored due to INSERT OR IGNORE

        # Retrieve authors for Harry Potter
        harry_authors = list(harry_potter.authors.all())
        self.assertEqual(len(harry_authors), 1)  # Should only have one entry

    def test_m2m_cascade_delete_source(self):
        """Test M2M relationships are deleted when source is deleted."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter
        harry_potter.authors.add(rowling)
        hp_id = harry_potter.id # Store ID before deleting

        # Delete source record (Book instance)
        Book.delete_entries({'id': hp_id}) # Pass condition dict

        # Verify relationships are gone from junction table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM book_author WHERE book_id = ?", (hp_id,))
        self.assertEqual(len(cursor_obj.fetchall()), 0)
        connection_obj.close()

    def test_m2m_cascade_delete_target(self):
        """Test M2M relationships are deleted when target is deleted."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter
        harry_potter.authors.add(rowling)
        rowling_id = rowling.id # Store ID before deleting

        # Delete target record (Author instance)
        Author.delete_entries({'id': rowling_id}) # Pass condition dict

        # Verify relationships are gone from junction table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM book_author WHERE author_id = ?", (rowling_id,))
        self.assertEqual(len(cursor_obj.fetchall()), 0)
        connection_obj.close()

        # Also verify trying to access via manager reflects the deletion
        # Re-fetch harry_potter as the original instance might be stale if caching were involved
        harry_potter_refetched = Book.objects.get(id=harry_potter.id)
        remaining_authors = list(harry_potter_refetched.authors.all())
        self.assertEqual(len(remaining_authors), 0)


    def test_m2m_custom_junction_table(self):
        """Test M2M relationships with custom junction table using manager."""
        # Use instance from setUp
        rowling = self.rowling
        # Create CustomBook instance
        custom_book_inst = CustomBook(title="Custom Book")
        CustomBook.insert_entries([custom_book_inst]) # Insert and update ID

        # Add relationship using instance manager
        custom_book_inst.authors.add(rowling)

        # Verify relationship exists in custom table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        cursor_obj.execute("SELECT * FROM customjunction WHERE custombook_id = ? AND author_id = ?", (custom_book_inst.id, rowling.id))
        self.assertEqual(len(cursor_obj.fetchall()), 1)
        connection_obj.close()

        # Verify retrieval via manager's all()
        authors = list(custom_book_inst.authors.all())
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0].id, rowling.id)
        self.assertEqual(authors[0].name, rowling.name)

    def test_m2m_invalid_relationship(self):
        """Test adding relationship with non-existent target ID using manager."""
        # Create an Author instance but don't save it (no ID)
        unsaved_author = Author(name="Unsaved Author")
        harry_potter = self.harry_potter # Use instance from setUp

        # Adding unsaved instance should raise ValueError
        with self.assertRaisesRegex(ValueError, "Cannot add unsaved 'author' instance"):
            harry_potter.authors.add(unsaved_author)

        # Create an Author instance with a fake ID that doesn't exist in DB
        invalid_author = Author(id=999, name="Invalid Author")
        # Adding instance with non-existent ID should raise ValueError (due to FK constraint)
        with self.assertRaisesRegex(ValueError, "Invalid target ID"):
            harry_potter.authors.add(invalid_author)


    def test_remove_nonexistent_relationship(self):
        """Test removing a relationship that doesn't exist using manager."""
        # Use instances from setUp
        rowling = self.rowling
        harry_potter = self.harry_potter

        # Should complete without errors
        harry_potter.authors.remove(rowling)
        harry_authors = list(harry_potter.authors.all())
        self.assertEqual(len(harry_authors), 0)

    def test_m2m_multiple_operations(self):
        """Test complex add/remove sequences using manager."""
        # Use instances from setUp
        rowling = self.rowling
        orwell = self.orwell
        harry_potter = self.harry_potter

        # Add two authors (can add multiple at once)
        harry_potter.authors.add(rowling, orwell)
        authors = list(harry_potter.authors.all())
        self.assertEqual(len(authors), 2)
        author_ids = {a.id for a in authors}
        self.assertIn(rowling.id, author_ids)
        self.assertIn(orwell.id, author_ids)

        # Remove one author
        harry_potter.authors.remove(rowling)
        authors = list(harry_potter.authors.all())
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0].id, orwell.id)
        self.assertEqual(authors[0].name, "George Orwell")

    def test_empty_relationships(self):
        """Test retrieving relationships when none exist using manager."""
        # Use instance from setUp
        harry_potter = self.harry_potter
        authors_qs = harry_potter.authors.all()
        self.assertIsInstance(authors_qs, QuerySet)
        authors = list(authors_qs)
        self.assertEqual(len(authors), 0)

    @classmethod
    def tearDownClass(cls):
        """Clean up the database file after all tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        # Attempt to remove directory if empty
        if os.path.exists('databases'):
            try:
                os.rmdir('databases')
            except OSError:
                pass # Ignore if not empty

if __name__ == '__main__':
    unittest.main()