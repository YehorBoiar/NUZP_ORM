import csv
from myapp.test import Student, Course


def wait():
    input("\nPress Enter to continue...\n")

def populate_from_csv(csv_path):
    students = {}
    courses = {}
    enrollments = []

    # Read CSV and collect data
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            student_name = row['student'].strip()
            course_title = row['course'].strip()
            # Collect unique students and courses
            if student_name not in students:
                students[student_name] = Student(name=student_name)
            if course_title not in courses:
                courses[course_title] = {"title": course_title}
            enrollments.append((student_name, course_title))

    # Insert students and courses
    Student.insert_entries(list(students.values()))
    Course.insert_entries(list(courses.values()))

    # Build mapping from names to objects
    student_objs = {s.name: s for s in Student.objects.all()}
    course_objs = {c.title: c for c in Course.objects.all()}

    # Enroll students in courses
    for student_name, course_title in enrollments:
        course = course_objs[course_title]
        student = student_objs[student_name]
        course.students.add(student)

    print("Database populated from CSV.")

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
    print("\n--- Inserting students and courses from CSV ---")
    populate_from_csv("myapp/data/demo_data.csv")
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
    print("Students with id > 6:", [s.name for s in Student.objects.filter(id__gt=6)])
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