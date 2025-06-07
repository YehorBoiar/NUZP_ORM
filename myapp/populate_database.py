from myapp.test import Student, Course

def wait():
    input("\nPress Enter to continue...\n")

def run_demo():
    print("=== ORM DEMO START ===")
    wait()

    # 1. Migrations
    print("\n--- Generating and applying migrations ---")
    print("python3 -m ORM.manager generate --app myapp")
    print("python3 -m ORM.manager migrate")
    print("python3 -m ORM.manager showmigrations")
    wait()

    # 2. Create: Insert students and courses
    print("\n--- Inserting students and courses ---")
    students = [
        Student(name="Alice"),
        Student(name="Bob"),
        Student(name="Charlie"),
    ]
    Student.insert_entries(students)
    courses = [
        {"title": "Physics"},
        {"title": "Math"},
    ]
    Course.insert_entries(courses)
    print("Inserted students and courses.")
    wait()

    # 3. Read: Query students and courses
    print("\n--- Querying students and courses ---")
    for student in Student.objects.all():
        print(f"Student: {student.name} (id={student.id})")
    for course in Course.objects.all():
        print(f"Course: {course.title} (id={course.id})")
    wait()

    # 4. Update: Change a student's name
    print("\n--- Updating a student ---")
    Student.replace_entries({"name": "Alice"}, {"name": "Alicia"})
    updated = Student.objects.get(name="Alicia")
    print(f"Updated student: {updated.name}")
    wait()

    # 5. Delete: Remove a student
    print("\n--- Deleting a student ---")
    Student.delete_entries({"name": "Bob"})
    print("Remaining students:", [s.name for s in Student.objects.all()])
    wait()

    # 6. Relationships: Enroll students in courses (ManyToMany)
    print("\n--- Enrolling students in courses ---")
    math = Course.objects.get(title="Math")
    physics = Course.objects.get(title="Physics")
    charlie = Student.objects.get(name="Charlie")
    alicia = Student.objects.get(name="Alicia")
    math.students.add(charlie, alicia)
    physics.students.add(charlie)
    print(f"Math enrolled: {[s.name for s in math.students.all()]}")
    print(f"Physics enrolled: {[s.name for s in physics.students.all()]}")
    wait()

    # 7. Querying with filters and lookups
    print("\n--- Querying with filters and lookups ---")
    print("Students with id > 1:", [s.name for s in Student.objects.filter(id__gt=1)])
    print("Courses with 'Math' in title:", [c.title for c in Course.objects.filter(title__like="Math")])
    wait()

    # 8. Serialization
    print("\n--- Serializing a student ---")
    print(alicia.as_dict())
    wait()

    # 9. Cleanup
    print("\n--- Cleaning up: Deleting all students and courses ---")
    Student.delete_entries({})
    Course.delete_entries({})
    print("All students and courses deleted.")
    wait()

    print("\n=== ORM DEMO END ===")

if __name__ == "__main__":
    run_demo()