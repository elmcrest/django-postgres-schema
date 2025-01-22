import os
from pathlib import Path

from django.db import migrations

SQL_FUNCTIONS = list()
for sql_function in ["clone_schema.001.sql", "delete_schema.001.sql"]:
    with open((Path(__file__) / ".." / ".." / "sql" / sql_function).resolve()) as fp:
        SQL_FUNCTIONS.append(fp.read())


class Migration(migrations.Migration):
    initial = True

    # run_before = [
    #    migrations.swappable_dependency(settings.POSTGRES_SCHEMA_MODEL),
    #    migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    # ]

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=SQL_FUNCTIONS[0], reverse_sql="DROP FUNCTION clone_schema(text, text)"
        ),
        migrations.RunSQL(
            sql=SQL_FUNCTIONS[1], reverse_sql="DROP FUNCTION delete_schema(text)"
        ),
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS __template__",
            reverse_sql="DROP SCHEMA __template__ CASCADE",
        ),
    ]
