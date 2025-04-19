### Coverage

To get coverage:

1. Setup venv:
	- `python3 -m venv venv`
	- `source venv/bin/activate`

2. Download coverage package and run:
```
python -m pip install coverage  # If not already installed
coverage run -m unittest discover -s tests -p 'test*.py'
coverage report -m            # View summary in terminal
coverage html                 # Generate detailed HTML report (view htmlcov/index.html)
```
