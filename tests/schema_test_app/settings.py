import os

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "postgres_schema",
    "schema_test_app",
)
DATABASES = {
    "default": {
        "ENGINE": "postgres_schema.engine",
        "NAME": os.environ["POSTGRES_DB"],
        "HOST": os.environ["POSTGRES_HOST"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "PORT": os.environ["POSTGRES_PORT"],
        "TEST": {"SERIALIZE": False},
    }
}
POSTGRES_SCHEMA_MODEL = "schema_test_app.Company"
SECRET_KEY = "test-key"
