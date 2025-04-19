import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORM import base, datatypes

DB_PATH = "databases/main.sqlite3"

class Customers(base.BaseModel):
    name = datatypes.CharField()
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

        # Insert test data
        Customers.insert_entries([
            {"name": "Yehor", "age": 18},
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
        ])
        self.yehor = Customers.objects.get(name="Yehor")
        self.alice = Customers.objects.get(name="Alice")
        self.bob = Customers.objects.get(name="Bob")

        ContactInfo.insert_entries([
            {"phone": "123-456-7890", "city": "New York", "customer": self.yehor},
            {"phone": "987-654-3210", "city": "Los Angeles", "customer": self.alice},
        ])


    def test_multiple_customers_with_contact_info(self):
        # Fetch all customers and their contact info
        yehor = Customers.objects.get(name="Yehor")
        alice = Customers.objects.get(name="Alice")
        bob = Customers.objects.get(name="Bob")

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
        bob = Customers.objects.get(name="Bob")

        # Attempt to fetch contact info for Bob
        with self.assertRaises(Exception):
            ContactInfo.objects.get(customer_id=bob["id"])

    def test_contact_info_without_customer(self):
        # Attempt to insert contact info without a valid customer
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.insert_entries([{"phone": "555-555-5555", "city": "Chicago", "customer": 999}])  # Invalid customer ID

    def test_duplicate_contact_info_for_customer(self):
        # Fetch Yehor
        yehor = Customers.objects.get(name="Yehor")
 
        # Attempt to insert another contact info for Yehor
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.insert_entries([{"phone": "111-222-3333", "city": "San Francisco", "customer": yehor["id"]}])

    def test_updating_contact_info(self):
        # Fetch Yehor and his contact info
        yehor = Customers.objects.get(name="Yehor")
        yehor_contact = ContactInfo.objects.get(customer_id=yehor.id)

        # Update Yehor's contact info
        ContactInfo.replace_entries({"id": yehor_contact.id}, {"phone": "999-999-9999", "city": "Boston"})

        # Fetch updated contact info
        updated_contact = ContactInfo.objects.get(customer_id=yehor.id)
        self.assertEqual(updated_contact.phone, "999-999-9999")
        self.assertEqual(updated_contact.city, "Boston")

    def test_deleting_customer_cascades_to_contact_info(self):
        # Fetch Alice and her contact info
        alice = Customers.objects.get(name="Alice")
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
        yehor = self.yehor
        alice = self.alice
        bob = self.bob # Bob has no contact info

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

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()