import unittest
from ORM import model, datatypes
import os
import sqlite3

DB_PATH = "databases/main.sqlite3"

class Customers(model.BaseModel):
    name = datatypes.CharField()
    age = datatypes.IntegerField()
    
class ContactInfo(model.BaseModel):
    phone = datatypes.CharField()
    city = datatypes.CharField()
    customer = model.OneToOneField(Customers)

class Orders(model.BaseModel):
    item = datatypes.CharField()
    customer = model.ForeignKey(to=Customers) 

class Author(model.BaseModel):
    name = datatypes.CharField()

class Book(model.BaseModel):
    title = datatypes.CharField()
    authors = model.ManyToManyField(to=Author)


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
            {"item": "item1", "customer": customer["id"]},
            {"item": "item2", "customer": customer["id"]},
            {"item": "item3", "customer": customer["id"]},
            {"item": "item4", "customer": customer["id"]}
        ])

    def test_customer_orders(self):
        # Fetch the customer
        customer = Customers.objects.get(id=1)

        # Fetch all orders for the customer
        orders = Orders.objects.filter(customer_id=customer["id"]).all()

        # Assert that the customer has 4 orders
        self.assertEqual(len(orders), 4)
        self.assertEqual(orders[0]["item"], "item1")
        self.assertEqual(orders[1]["item"], "item2")
        self.assertEqual(orders[2]["item"], "item3")
        self.assertEqual(orders[3]["item"], "item4")

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
            {"phone": "123-456-7890", "city": "New York", "customer": self.yehor["id"]},
            {"phone": "987-654-3210", "city": "Los Angeles", "customer": self.alice["id"]},
        ])


    def test_multiple_customers_with_contact_info(self):
        # Fetch all customers and their contact info
        yehor = Customers.objects.get(name="Yehor")
        alice = Customers.objects.get(name="Alice")
        bob = Customers.objects.get(name="Bob")

        yehor_contact = ContactInfo.objects.get(customer_id=yehor["id"])
        alice_contact = ContactInfo.objects.get(customer_id=alice["id"])

        # Assert contact info matches
        self.assertEqual(yehor_contact["phone"], "123-456-7890")
        self.assertEqual(alice_contact["city"], "Los Angeles")

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
        yehor_contact = ContactInfo.objects.get(customer_id=yehor["id"])

        # Update Yehor's contact info
        ContactInfo.replace_entries({"id": yehor_contact["id"]}, {"phone": "999-999-9999", "city": "Boston"})

        # Fetch updated contact info
        updated_contact = ContactInfo.objects.get(customer_id=yehor["id"])
        self.assertEqual(updated_contact["phone"], "999-999-9999")
        self.assertEqual(updated_contact["city"], "Boston")

    def test_deleting_customer_cascades_to_contact_info(self):
        # Fetch Alice and her contact info
        alice = Customers.objects.get(name="Alice")
        alice_contact = ContactInfo.objects.get(customer_id=alice["id"])

        # Delete Alice
        Customers.delete_entries({'id':alice["id"]}) 
        # fix : passing a dictionnary 

        # Ensure Alice's contact info is also deleted
        with self.assertRaises(Exception):  # Replace with the specific exception your ORM raises
            ContactInfo.objects.get(id=alice_contact["id"])

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists('databases'):
            os.rmdir('databases')

if __name__ == '__main__':
    unittest.main()