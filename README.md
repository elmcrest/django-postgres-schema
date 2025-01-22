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

## makemigrations
by default postgres_schema wraps migration operations according to your settings.py but it's advised to check them manually to be sure things are applied as expected.

### for tenant apps
To run migrations in the template schema (by default named `__template__`) you'll have to wrap operations in `RunInTemplate`. This also runs the migrations in existing Schemas.
```python
# ...
from postgres_schema.operations import RunInTemplate


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        RunInTemplate(
            migrations.CreateModel(
#...
```

### for public apps
For the initial schema defining model or any other "public" model, wrap in `RunInPublic` like so:
```python
#...
from postgres_schema.operations import RunInPublic


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        RunInPublic(
            migrations.CreateModel(
#...
```