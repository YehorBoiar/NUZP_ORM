from myapp.test import Student, Course

if __name__ == "__main__":
    # Insert sample students
    students = [
        {"name": "John Smith"},
        {"name": "Emma Johnson"},
        {"name": "Michael Davis"},
        {"name": "Sophia Martinez"},
        {"name": "William Thompson"}
    ]
    Student.insert_entries(students)

    # Insert sample courses
    courses = [
        {"title": "Introduction to Computer Science"},
        {"title": "Data Structures and Algorithms"},
        {"title": "Database Systems"},
        {"title": "Machine Learning"}
    ]
    Course.insert_entries(courses)

    # Retrieve students and courses to establish relationships
    john = Student.objects.get(name="John Smith")
    emma = Student.objects.get(name="Emma Johnson")
    michael = Student.objects.get(name="Michael Davis")
    sophia = Student.objects.get(name="Sophia Martinez")
    william = Student.objects.get(name="William Thompson")

    cs_intro = Course.objects.get(title="Introduction to Computer Science")
    data_structures = Course.objects.get(title="Data Structures and Algorithms")
    databases = Course.objects.get(title="Database Systems")
    ml = Course.objects.get(title="Machine Learning")

    # Establish many-to-many relationships
    # John takes CS Intro and Data Structures
    Course.add_m2m('students', cs_intro, john)
    Course.add_m2m('students', data_structures, john)

    # Emma takes CS Intro, Data Structures, and Databases
    Course.add_m2m('students', cs_intro, emma)
    Course.add_m2m('students', data_structures, emma)
    Course.add_m2m('students', databases, emma)

    # Michael takes Data Structures and Machine Learning
    Course.add_m2m('students', data_structures, michael)
    Course.add_m2m('students', ml, michael)

    # Sophia takes Databases and Machine Learning
    Course.add_m2m('students', databases, sophia)
    Course.add_m2m('students', ml, sophia)

    # William takes all courses
    Course.add_m2m('students', cs_intro, william)
    Course.add_m2m('students', data_structures, william)
    Course.add_m2m('students', databases, william)
    Course.add_m2m('students', ml, william)

    print("Database populated successfully!")

    # Display course enrollment counts
    for course in Course.objects.all():
        students = Course.get_m2m('students', course)
        print(f"Course: {course['title']} - {len(students)} students enrolled")

    # Display student course counts
    for student in Student.objects.all():
        courses = []
        for course in Course.objects.all():
            if student in Course.get_m2m('students', course):
                courses.append(course['title'])
        print(f"Student: {student['name']} - Enrolled in {len(courses)} courses: {', '.join(courses)}")

