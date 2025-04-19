import sys
import os
import unittest
import sqlite3
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes

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
        Customers.delete_entries({}, confirm=True)
        ContactInfo.delete_entries({}, confirm=True)

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
        Author.delete_entries({}, confirm=True)
        Book.delete_entries({}, confirm=True)
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

if __name__ == '__main__':
    unittest.main()