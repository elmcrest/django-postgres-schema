# django-postgres-schema
![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/elmcrest/fa3b7a390c6f18f66a41fbc73b349a3d/raw/django_postgres_schema.json)
![badge](https://img.shields.io/pypi/v/django-postgres-schema.svg)

**django-postgres-schema** makes it possible to use postgres schemas with Django to build SaaS applications where each customer's data lives in an isolated schema.

## usage

in your `settings.py` set the correct database engine, f.e. like so:

```python

INSTALLED_APPS = [
    # existing django installed apps, recommended to add postgres_schema "early"
    "postgres_schema",
]

DATABASES = {
    "default": {
        "ENGINE": "postgres_schema.engine",
        "HOST": os.environ("POSTGRES_HOST"),
        "NAME": os.environ("POSTGRES_DB"),
        "PORT": os.environ("POSTGRES_PORT"),
        "USER": os.environ("POSTGRES_USER"),
        "PASSWORD": os.environ("POSTGRES_PASSWORD"),
    },
}

# one tenant model, f.e. a Company model
# one or more tenant apps which are dedicated "per tenant"

POSTGRES_SCHEMA_MODEL = "company.Company"
POSTGRES_SCHEMA_APPS = (
    "company.Labor",
    "project",
    "inventory",
)
```
