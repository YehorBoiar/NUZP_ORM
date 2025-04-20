from ORM.fields import ManyToManyRelatedManager
import sys
import os
import unittest
import sqlite3
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes, fields

DB_PATH = "databases/main.sqlite3"

class Customers(base.BaseModel):
    name = datatypes.CharField(unique=True)
    age = datatypes.IntegerField()
    
class ContactInfo(base.BaseModel):
    phone = datatypes.CharField()
    city = datatypes.CharField()
    customer = base.OneToOneField(Customers)

class Orders(base.BaseModel):
    item = datatypes.CharField()
    customer = base.ForeignKey(to=Customers) 

class Author(base.BaseModel):
    name = datatypes.CharField()

class Book(base.BaseModel):
    title = datatypes.CharField()
    authors = base.ManyToManyField(to=Author)


class TestOneToManyRelationship(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create tables
        Customers.create_table()
        Orders.create_table()
        
        # Insert a customer
        Customers.insert_entries([{"name": "Yehor", "age": 18}])

        customer = Customers.objects.get(name="Yehor")
        # Insert multiple orders for the customer
        Orders.insert_entries([
            {"item": "item1", "customer": customer.id},
            {"item": "item2", "customer": customer.id},
            {"item": "item3", "customer": customer.id},
            {"item": "item4", "customer": customer.id}
        ])

    def test_customer_orders(self):
        # Fetch the customer
        customer = Customers.objects.get(id=1)

        # Fetch all orders for the customer
        orders = Orders.objects.filter(customer_id=customer.id).all()

        # Assert that the customer has 4 orders
        self.assertEqual(len(orders), 4)
        self.assertEqual(orders[0].item, "item1")
        self.assertEqual(orders[1].item, "item2")
        self.assertEqual(orders[2].item, "item3")
        self.assertEqual(orders[3].item, "item4")

    def test_as_dict_foreign_key(self):
        """Test as_dict() for a model with a ForeignKey."""
        # Fetch the customer and one of their orders
        customer = Customers.objects.get(name="Yehor")
        order = Orders.objects.filter(customer_id=customer.id).all()[0]

        # Get dict representation of the order
        order_dict = order.as_dict()

        # Expected dict for the order
        expected_order_dict = {
            'id': order.id,
            'item': order.item, # e.g., "item1"
            'customer_id': customer.id # Should contain the related customer's ID
        }
        self.assertDictEqual(order_dict, expected_order_dict)

        # Test as_dict on the customer (which has no outgoing FK/O2O in this test)
        customer_dict = customer.as_dict()
        expected_customer_dict = {
            'id': customer.id,
            'name': "Yehor",
            'age': 18
        }
        self.assertDictEqual(customer_dict, expected_customer_dict)

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

        

class TestOneToOneRelationshipEdgeCases(unittest.TestCase):
    def setUp(self):
        # Ensure tables exist before deleting entries
        Customers.create_table()
        ContactInfo.create_table()

        # Skip confirmation prompt in tests
        Customers.delete_entries({}, confirm_delete_all=True)
        ContactInfo.delete_entries({}, confirm_delete_all=True)

        # Reset sequences
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN (?, ?);",
                           (Customers.__name__.lower(), ContactInfo.__name__.lower()))
            connection.commit()
        except sqlite3.OperationalError as e:
            print(f"Info: Could not reset sequences - {e}")
            connection.rollback()
        finally:
            connection.close()


        # Insert test data
        self.cust1 = Customers(name="Yehor", age=18)
        self.cust2 = Customers(name="Alice", age=25)
        self.cust3 = Customers(name="Bob", age=30)
        Customers.insert_entries([self.cust1, self.cust2, self.cust3])

        # Use instances for FK assignment
        self.contact1 = ContactInfo(phone="123-456-7890", city="New York", customer=self.cust1)
        self.contact2 = ContactInfo(phone="987-654-3210", city="Los Angeles", customer=self.cust2)
        ContactInfo.insert_entries([self.contact1, self.contact2])


    def test_multiple_customers_with_contact_info(self):
        # Fetch all customers and their contact info
        yehor = self.cust1
        alice = self.cust2
        bob = self.cust3

        yehor_contact = ContactInfo.objects.get(customer_id=yehor.id)
        alice_contact = ContactInfo.objects.get(customer_id=alice.id)

        # Assert contact info matches
        self.assertEqual(yehor_contact.phone, "123-456-7890")
        self.assertEqual(alice_contact.city, "Los Angeles")

        # Bob has no contact info
        with self.assertRaises(Exception): 
            ContactInfo.objects.get(customer_id=bob["id"])

    def test_customer_without_contact_info(self):
        # Fetch Bob, who has no contact info
        bob = self.cust3

        # Attempt to fetch contact info for Bob
        with self.assertRaises(Exception):
            ContactInfo.objects.get(customer_id=bob["id"])

    def test_contact_info_without_customer(self):
        # Attempt to insert contact info without a valid customer
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.insert_entries([{"phone": "555-555-5555", "city": "Chicago", "customer": 999}])  # Invalid customer ID

    def test_duplicate_contact_info_for_customer(self):
        # Fetch Yehor
        yehor = self.cust1
 
        # Attempt to insert another contact info for Yehor
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.insert_entries([{"phone": "111-222-3333", "city": "San Francisco", "customer": yehor["id"]}])

    def test_updating_contact_info(self):
        # Fetch Yehor and his contact info
        yehor = self.cust1
        yehor_contact = ContactInfo.objects.get(customer_id=yehor.id)

        # Update Yehor's contact info
        ContactInfo.replace_entries({"id": yehor_contact.id}, {"phone": "999-999-9999", "city": "Boston"})

        # Fetch updated contact info
        updated_contact = ContactInfo.objects.get(customer_id=yehor.id)
        self.assertEqual(updated_contact.phone, "999-999-9999")
        self.assertEqual(updated_contact.city, "Boston")

    def test_deleting_customer_cascades_to_contact_info(self):
        # Fetch Alice and her contact info
        alice = self.cust2
        alice_contact = ContactInfo.objects.get(customer_id=alice.id)

        # Delete Alice
        Customers.delete_entries({'id':alice.id}) 
        # fix : passing a dictionnary 

        # Ensure Alice's contact info is also deleted
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.objects.get(id=alice_contact.id)

    def test_as_dict_one_to_one(self):
        """Test as_dict() for models involved in a OneToOne relationship."""
        # Use instances from setUp
        yehor = self.cust1
        alice = self.cust2
        bob = self.cust3 # Bob has no contact info

        # Fetch contact info for Yehor
        yehor_contact = ContactInfo.objects.get(customer_id=yehor.id)

        # Get dict representation of Yehor's contact info
        contact_dict = yehor_contact.as_dict()
        expected_contact_dict = {
            'id': yehor_contact.id,
            'phone': "123-456-7890",
            'city': "New York",
            'customer_id': yehor.id # Should contain the related customer's ID
        }
        self.assertDictEqual(contact_dict, expected_contact_dict)

        # Get dict representation of Yehor (Customer)
        # Customer model itself doesn't define the O2O field pointing *to* ContactInfo
        # So its dict should only contain its own fields.
        yehor_dict = yehor.as_dict()
        expected_yehor_dict = {
            'id': yehor.id,
            'name': "Yehor",
            'age': 18
        }
        self.assertDictEqual(yehor_dict, expected_yehor_dict)

        # Get dict representation of Bob (no related ContactInfo)
        bob_dict = bob.as_dict()
        expected_bob_dict = {
            'id': bob.id,
            'name': "Bob",
            'age': 30
        }
        self.assertDictEqual(bob_dict, expected_bob_dict)

    def test_as_dict_unsaved_one_to_one(self):
        """Test as_dict() on unsaved instances with FK/O2O fields."""
        # Unsaved ContactInfo (customer_id should be None)
        unsaved_contact = ContactInfo(phone="111-000", city="Nowhere")
        contact_dict = unsaved_contact.as_dict()
        expected_contact_dict = {
            'id': None,
            'phone': "111-000",
            'city': "Nowhere",
            'customer_id': None # FK/O2O ID should be None if instance/relation not set
        }
        self.assertDictEqual(contact_dict, expected_contact_dict)

        # Unsaved ContactInfo with unsaved Customer assigned
        unsaved_customer = Customers(name="Temp", age=1)
        unsaved_contact_with_rel = ContactInfo(phone="222-000", city="Somewhere", customer=unsaved_customer)
        contact_dict_rel = unsaved_contact_with_rel.as_dict()
        expected_contact_dict_rel = {
            'id': None,
            'phone': "222-000",
            'city': "Somewhere",
            'customer_id': None # Related customer has no ID yet
        }
        self.assertDictEqual(contact_dict_rel, expected_contact_dict_rel)

    def test_insert_onetoone_violation_in_batch(self):
        """Test O2O violation check within _process_entries_for_values (line 210)."""
        # Try inserting two ContactInfo entries for self.cust3 in the same batch
        contact_batch = [
            ContactInfo(phone="111", city="CityA", customer=self.cust3),
            ContactInfo(phone="222", city="CityB", customer=self.cust3) # Duplicate customer FK
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate entry detected within the batch for OneToOne field 'customer' with value 3 at index 1"):
            ContactInfo.insert_entries(contact_batch)

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

# Add test for M2M as_dict error
class TestM2MAsDictError(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists('databases'):
            os.makedirs('databases')
        Author.create_table()
        Book.create_table()

    def setUp(self):
        Author.delete_entries({}, confirm_delete_all=True)
        Book.delete_entries({}, confirm_delete_all=True)
        # Clear junction table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        try: cursor_obj.execute("DELETE FROM book_author")
        except sqlite3.OperationalError: pass
        try: cursor_obj.execute("DELETE FROM sqlite_sequence WHERE name IN ('author', 'book')")
        except sqlite3.OperationalError: pass
        connection_obj.commit()
        connection_obj.close()

    @patch('ORM.fields.ManyToManyRelatedManager.all')
    def test_as_dict_m2m_error(self, mock_m2m_all):
        """Test as_dict M2M error handling (lines 108-111)."""
        # Setup data
        author = Author(name="Test Author")
        Author.insert_entries([author])
        book = Book(title="Test Book")
        Book.insert_entries([book])
        book.authors.add(author) # Add relationship

        # Configure mock to raise error when .all() is called within as_dict
        mock_m2m_all.side_effect = Exception("Simulated M2M fetch error")

        # Call as_dict and check output
        book_dict = book.as_dict()

        # Expect 'authors' to be an empty list due to error handling
        expected_dict = {
            'id': book.id,
            'title': "Test Book",
            'authors': [] # Should default to empty list on error
        }
        self.assertDictEqual(book_dict, expected_dict)
        # Optionally check if the warning was printed (requires more setup)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            try: os.rmdir('databases')
            except OSError: pass

class TestFieldFeatures(unittest.TestCase):
    """Tests for basic Field class features like default values."""
    @classmethod
    def setUpClass(cls):
        # Define a simple model for testing field defaults
        class DefaultModel(base.BaseModel):
            name = datatypes.CharField(default="DefaultName")
            value = datatypes.IntegerField(default=100)
            nullable_int = datatypes.IntegerField(null=True, default=None) # Test None default

        cls.DefaultModel = DefaultModel
        # No table creation needed as we only test instance initialization

    def test_field_default_init(self):
        """Test Field __init__ default handling (line 37 in base.py)."""
        # BaseModel.__init__ does NOT apply defaults from Field definition
        # It defaults to None if kwarg is missing.
        instance = self.DefaultModel()
        self.assertIsNone(instance.name, "CharField default should not be applied by __init__")
        self.assertIsNone(instance.value, "IntegerField default should not be applied by __init__")
        self.assertIsNone(instance.nullable_int, "IntegerField(default=None) should be None")


        # Test providing values overrides the None default from __init__
        instance_override = self.DefaultModel(name="SpecificName", value=50, nullable_int=5)
        self.assertEqual(instance_override.name, "SpecificName")
        self.assertEqual(instance_override.value, 50)
        self.assertEqual(instance_override.nullable_int, 5)

    def test_charfield_init(self):
        """Test CharField __init__ (line 68 in datatypes.py)."""
        # Primarily testing instantiation works and attributes are stored
        field = datatypes.CharField(max_length=10, unique=True, default="test", null=False)
        self.assertEqual(field.max_length, 10)
        self.assertTrue(field.unique)
        self.assertEqual(field.default, "test")
        self.assertFalse(field.null)
        self.assertEqual(field.db_type, "TEXT")
        # Note: max_length validation isn't typically done on assignment in simple ORMs
        # It's usually a database constraint.

    def test_integerfield_init(self):
        """Test IntegerField __init__ (line 87 in datatypes.py)."""
        instance = datatypes.IntegerField(default=0, null=False, unique=True)
        self.assertEqual(instance.default, 0)
        self.assertFalse(instance.null)
        self.assertTrue(instance.unique)
        self.assertEqual(instance.db_type, "INTEGER")
        # No specific validation on assignment is implemented in the Field base class

class TestForeignKeyFeatures(unittest.TestCase):
    """Tests specific ForeignKey features."""
    @classmethod
    def setUpClass(cls):
        class Country(base.BaseModel):
            name = datatypes.CharField(unique=True)
            # Removed 'cities' CharField - reverse relations aren't automatic

        class City(base.BaseModel):
            name = datatypes.CharField()
            # ForeignKey definition
            country = fields.ForeignKey(to=Country, null=False) # Make it non-nullable for testing

        cls.Country = Country
        cls.City = City
        if not os.path.exists('databases'):
            os.makedirs('databases')
        cls.Country.create_table()
        cls.City.create_table()

    def setUp(self):
        # Clear tables before each test
        self.City.delete_entries({}, confirm_delete_all=True) # Delete dependent table first
        self.Country.delete_entries({}, confirm_delete_all=True)

        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN (?, ?);",
                           (self.Country.__name__.lower(), self.City.__name__.lower()))
            connection.commit()
        except sqlite3.OperationalError: pass # Ignore if sequence table doesn't exist
        finally: connection.close()

        # Insert a country instance
        self.country1 = self.Country(name="Testland")
        self.Country.insert_entries([self.country1]) # ID gets updated

    def test_foreignkey_reverse_access_not_implemented(self):
        """Test that reverse ForeignKey access is not automatically created."""
        city1 = self.City(name="Capital", country=self.country1)
        self.City.insert_entries([city1])

        # Accessing 'city_set' (or similar) should fail as it's not defined
        self.assertFalse(hasattr(self.country1, 'city_set'))
        self.assertFalse(hasattr(self.country1, 'cities')) # Check original name too
        with self.assertRaises(AttributeError):
            _ = self.country1.city_set # Or whatever default name might be expected

        # To get related cities, query the City model directly
        related_cities_qs = self.City.objects.filter(country_id=self.country1.id)
        related_cities = list(related_cities_qs)
        self.assertEqual(len(related_cities), 1)
        self.assertEqual(related_cities[0].name, "Capital")


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            try: os.rmdir('databases')
            except OSError: pass


class TestManyToManyFieldFeatures(unittest.TestCase):
    """Tests specific ManyToManyField features."""
    @classmethod
    def setUpClass(cls):
        class Tag(base.BaseModel):
            name = datatypes.CharField(unique=True)
            # No automatic reverse relation 'posts'

        class Post(base.BaseModel):
            title = datatypes.CharField()
            tags = fields.ManyToManyField(to=Tag) # Use fields.ManyToManyField

        cls.Tag = Tag
        cls.Post = Post
        if not os.path.exists('databases'):
            os.makedirs('databases')
        cls.Tag.create_table()
        cls.Post.create_table() # This should also create the junction table

    def setUp(self):
        # Determine junction table name dynamically
        m2m_field = self.Post._many_to_many['tags']
        self.junction_table = m2m_field.through or f"{self.Post.__name__.lower()}_{self.Tag.__name__.lower()}"

        # Clear tables and junction table
        connection_obj = sqlite3.connect(DB_PATH)
        cursor_obj = connection_obj.cursor()
        try: cursor_obj.execute(f"DELETE FROM {self.junction_table}")
        except sqlite3.OperationalError: pass # Ignore if table doesn't exist yet
        connection_obj.commit() # Commit deletion before deleting main tables

        self.Post.delete_entries({}, confirm_delete_all=True) # Delete Post first if Tag has FKs to it (it doesn't here)
        self.Tag.delete_entries({}, confirm_delete_all=True)

        try:
            cursor_obj.execute("DELETE FROM sqlite_sequence WHERE name IN (?, ?, ?);",
                           (self.Tag.__name__.lower(), self.Post.__name__.lower(), self.junction_table)) # Include junction table if it has own sequence
            connection_obj.commit()
        except sqlite3.OperationalError: pass # Ignore if sequence table doesn't exist
        finally: connection_obj.close()

        # Insert base data
        self.tag1 = self.Tag(name="Tech")
        self.tag2 = self.Tag(name="News")
        self.Tag.insert_entries([self.tag1, self.tag2])
        self.post1 = self.Post(title="Post 1")
        self.Post.insert_entries([self.post1])

    def test_manytomanyfield_init_no_related_name(self):
        """Test ManyToManyField __init__ doesn't store related_name."""
        # The implementation in fields.py doesn't accept/store related_name
        m2m_field = fields.ManyToManyField(self.Tag) # No related_name arg
        self.assertFalse(hasattr(m2m_field, 'related_name'))

    def test_manytomany_get_manager(self):
        """Test ManyToManyField __get__ returns manager."""
        manager = self.post1.tags
        self.assertIsInstance(manager, ManyToManyRelatedManager)
        # Check manager attributes based on fields.py implementation
        self.assertIs(manager.instance, self.post1)
        self.assertIsInstance(manager.field, fields.ManyToManyField)
        self.assertIs(manager.source_class, self.Post)
        self.assertIs(manager.target_class, self.Tag)
        self.assertEqual(manager.junction_table, self.junction_table)

    def test_manytomany_direct_assignment_possible(self):
        """Test that direct assignment to M2M field replaces the manager (not recommended)."""
        # The descriptor doesn't define __set__, so assignment replaces the manager
        original_manager = self.post1.tags
        self.post1.tags = [self.tag1] # Assign a list
        self.assertNotIsInstance(self.post1.tags, ManyToManyRelatedManager)
        self.assertEqual(self.post1.tags, [self.tag1])
        # Restore manager for subsequent tests if needed (though setUp handles it)
        setattr(self.post1, '_tags_manager', original_manager)


    def test_manytomany_reverse_access_not_implemented(self):
        """Test accessing reverse M2M relationship is not automatic."""
        self.post1.tags.add(self.tag1)
        post2 = self.Post(title="Post 2")
        self.Post.insert_entries([post2])
        post2.tags.add(self.tag1)

        # Accessing tag1.posts should fail
        self.assertFalse(hasattr(self.tag1, 'posts'))
        with self.assertRaises(AttributeError):
            _ = self.tag1.posts

        # To get related posts, query the Post model and filter via the junction table
        # This requires a more complex query or a helper method not shown in the base ORM
        # Simplest is to iterate through posts and check their tags
        related_posts = []
        for post in self.Post.objects.all():
             if self.tag1.id in [tag.id for tag in post.tags.all()]:
                 related_posts.append(post)

        self.assertEqual(len(related_posts), 2)
        post_titles = {p.title for p in related_posts}
        self.assertEqual(post_titles, {"Post 1", "Post 2"})


    def test_m2m_manager_add_invalid_type(self):
        """Test ManyToManyRelatedManager add() type validation (line 193 in fields.py)."""
        # The add method checks isinstance(target_obj, self.target_class)
        with self.assertRaisesRegex(TypeError, f"Can only add '{self.Tag.__name__}' instances."):
            self.post1.tags.add("not a tag instance")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            try: os.rmdir('databases')
            except OSError: pass

if __name__ == '__main__':
    unittest.main()