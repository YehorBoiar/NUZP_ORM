from ORM.datatypes import CharField
from ORM.model import * 

# Import the necessary classes from your ORM
class Author(BaseModel):
    name = CharField()

class Book(BaseModel):
    title = CharField()
    author = ForeignKey(Author)  # One-to-Many: A book belongs to one author

class Tag(BaseModel):
    name = CharField()

class BookTag(BaseModel):
    book = ForeignKey(Book)  # Many-to-Many Relationship via an explicit join table
    tag = ForeignKey(Tag)

# Create the database tables
Author.create_table()
Book.create_table()
Tag.create_table()
BookTag.create_table()


# Insert authors
Author.insert_entries([
    {"name": "J.K. Rowling"},
    {"name": "George Orwell"}
])

# Insert books (associating them with authors)
author1 = Author.objects.get(name="J.K. Rowling")
author2 = Author.objects.get(name="George Orwell")

Book.insert_entries([
    {"title": "Harry Potter and the Sorcerer's Stone", "author": author1['id']},
    {"title": "Harry Potter and the Chamber of Secrets", "author": author1['id']},
    {"title": "1984", "author": author2['id']},
    {"title": "Animal Farm", "author": author2['id']}
])

# Insert tags
Tag.insert_entries([
    {"name": "Fantasy"},
    {"name": "Dystopian"},
    {"name": "Classic"}
])

# Retrieve books and tags to use in the BookTag (join table)
book1 = Book.objects.get(title="Harry Potter and the Sorcerer's Stone")
book2 = Book.objects.get(title="1984")

tag1 = Tag.objects.get(name="Fantasy")
tag2 = Tag.objects.get(name="Dystopian")

# Create many-to-many relationships manually using the join table
BookTag.insert_entries([
    {"book": book1['id'], "tag": tag1['id']},  # "Harry Potter" -> Fantasy
    {"book": book2['id'], "tag": tag2['id']}   # "1984" -> Dystopian
])

authors = Author.objects.all()
for i in authors:
    print(i)
    
author = Author.objects.get(name="J.K. Rowling")
books = Book.objects.filter(author_id=author["id"])
for book in books:
    print(book)

book = Book.objects.get(title="Harry Potter and the Sorcerer's Stone")
book_tags = BookTag.objects.filter(book_id=book['id'])
for book_tag in book_tags:
    tag = Tag.objects.get(id=book_tag['id'])
    print(tag)
    
tag = Tag.objects.get(name="Fantasy")
book_tags = BookTag.objects.filter(id=tag['id'])
for book_tag in book_tags:
    book = Book.objects.get(id=book_tag['id'])
    print(book)
    