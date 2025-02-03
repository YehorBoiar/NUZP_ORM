import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 manage.py [makemigrations | migrate]")
        return

    command = sys.argv[1]
    print(command)

if __name__ == "__main__":
    main()