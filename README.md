##Implementation: 

## Release Notes:

  * The mentioned bug is fixed, and several other related cases are found and fixed. Many new tests for positive and negative scenarios are added.
  * The new API to PATCH existing booking is implemented. This API can be used to extend a number of nights. Similar logic from booking creation to find date conflicts is applied. Many tests for positive and negative scenarios are added.
  * In crud.py the legacy query() method was replaced with select.where(). See the SQLAlchemy docs: https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html
  * Introduced pyproject.toml, Poetry and Make for easier dependency management and project execution.
  * Added linter rules and ensured the codebase is free of linter issues.
  * Added pre-commit hook to run tests locally before pushing to the repository.
  * Refactored model code to follow SQLAlchemy 2.0 style.
  * Added validation to prevent booking of zero or fewer nights.
  * Added GitHub Actions. 
  * Added code coverage verification. Current code coverage is 100%.
  * Updated Swagger documentation.

## TODO Improvements:

* Move code from the synchronous engine to the asynchronous engine if another database is used in production.
* Add logging and monitoring.
* Split tests into smaller units.

## Assumptions:
   
   * I assumed it is valid for the same guest to book the same or different properties for different time periods. For example, a guest may travel to Berlin for a few days, then go to Cologne for a few days, and finally return to Berlin before flying back.
   * I didn't address an edge case when the same guest books the same unit without gaps. I.e., it's allowed for the same guest to book unit from 24-09-2025 to 28-09-2025 and from 28-09-2025 to 30-09-2025.
   * I did not implement a check for maximum number of nights per unit. In a real development process, I would clarify this requirement in the specifications.
   * I assumed than new API takes the total number of nights as a parameter, rather than the number of additional nights.

## How to run:

### URLs
The urls that are accessible from localhost:
* Service: http://localhost:8000
* OpenAPI docs of Service: http://localhost:8000/docs

## Docker only 
Prerequisites:
* Docker Compose V2 (aka `docker compose` without the `-` in between)
* Make

### Essentials
Get everything up and running:
```
make start
```
This starts the Docker container for the app.

Bring everything down:
```
make stop
```

For convenience, there's also `make restart` which runs `stop` and `start`.

### Testing
To run the pytest test:
```
make test
```

### Linting
I  used `ruff` for linting, `ruff format` for automatic code formatting, and `mypy` for static type checking.
You can run all of them with:
```
make lint
```

### Python dependencies
To add or remove dependencies, modify _pyproject.toml_ and generate a fresh lock file with: 
```
make update-dependencies
```
After doing changes related to the dependencies, containers should be restarted.

## Development (local Python environment)

### Essentials

#### Creating the local Python environment
Create a poetry environment, activate it and install the dependencies:
```
pip install poetry
poetry env use python3.13
poetry install
poetry env activate
````

#### Running the service

Run the service locally with hot reload enabled:
```
poetry run uvicorn app.main:app --reload
```

### Linting with pre-commit
I added a pre-commit to automatically run on each commit:
Install pre-commte
```
pre-commit install
```

Run over all codebase:
```
pre-commit run --all-files
```

## Continuous integration aka CI

There's a GitHub workflow (ci.yml) which runs pre-commit (`ruff`, `ruff format`, and `mypy`) for the whole codebase and the pytest test suite on each push.

## Run Coverage

Coverage can be run locally using the following command.
```
 coverage run -m --branch pytest --cov . --cov-report term-missing
```
