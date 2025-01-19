from django.core.exceptions import ValidationError
from django.db import connection, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.test import TestCase
from django.test.utils import isolate_apps

from postgres_schema.models import AbstractSchema, get_schema_model
from postgres_schema.schema import activate_schema

Schema = get_schema_model()


@isolate_apps("schema_test_app", attr_name="apps")
class MigrationTest(TestCase):
    def get_table_description(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(cursor, table)

    def get_table_list(self):
        with connection.cursor() as cursor:
            table_list = connection.introspection.get_table_list(cursor)
        return [table.name for table in table_list]

    def assertTableExists(self, table):
        self.assertIn(table, self.get_table_list())

    def assertTableNotExists(self, table):
        self.assertNotIn(table, self.get_table_list())

    def assertColumnExists(self, table, column):
        self.assertIn(column, [c.name for c in self.get_table_description(table)])

    def assertColumnNotExists(self, table, column):
        self.assertNotIn(column, [c.name for c in self.get_table_description(table)])

    def assertColumnNull(self, table, column):
        self.assertEqual(
            [c.null_ok for c in self.get_table_description(table) if c.name == column][
                0
            ],
            True,
        )

    def assertColumnNotNull(self, table, column):
        self.assertEqual(
            [c.null_ok for c in self.get_table_description(table) if c.name == column][
                0
            ],
            False,
        )

    def assertIndexExists(self, table, columns, value=True):
        with connection.cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["index"]
                    for c in connection.introspection.get_constraints(
                        cursor, table
                    ).values()
                    if c["columns"] == list(columns)
                ),
            )

    def assertIndexNotExists(self, table, columns):
        return self.assertIndexExists(table, columns, False)

    def assertFKExists(self, table, columns, to, value=True):
        with connection.cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["foreign_key"] == to
                    for c in connection.introspection.get_constraints(
                        cursor, table
                    ).values()
                    if c["columns"] == list(columns)
                ),
            )

    def assertFKNotExists(self, table, columns, to, value=True):
        return self.assertFKExists(table, columns, to, False)

    def test_create_shared_model(self):
        migration = Migration("name", "tests")
        migration.operations = [
            migrations.CreateModel(
                "Address",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("street", models.TextField()),
                ],
            )
        ]
        with connection.schema_editor() as editor:
            migration.apply(ProjectState(), editor)

        activate_schema("public")
        self.assertTableExists("tests_address")
        activate_schema("__template__", exclude_public=True)
        self.assertTableNotExists("tests_address")

    def test_create_tenant_model(self):
        migration = Migration("name", "tests")
        migration.operations = [
            migrations.CreateModel(
                "Address",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("street", models.TextField()),
                ],
            )
        ]
        with self.settings(POSTGRES_SCHEMA_APPS=["tests"]):
            with connection.schema_editor() as editor:
                migration.apply(ProjectState(), editor)

        activate_schema("public")
        self.assertTableNotExists("tests_address")
        activate_schema("__template__", exclude_public=True)
        self.assertTableExists("tests_address")


@isolate_apps("schema_test_app", attr_name="apps")
class SchemaQuerySetTest(TestCase):
    def setUp(self):
        from django.db import models

        class TestModel(AbstractSchema):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_test_app"

        # Create the table using migrations
        migration = Migration("name", "schema_test_app")
        migration.operations = [
            migrations.CreateModel(
                "TestModel",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("schema", models.CharField(max_length=100)),
                    ("is_active", models.BooleanField(default=True)),
                ],
            )
        ]

        with connection.schema_editor() as editor:
            migration.apply(ProjectState(), editor)

    def test_create_requires_schema(self):
        TestModel = self.apps.get_model("schema_test_app", "TestModel")

        # Activate the public schema first
        activate_schema("public")

        # Should work with schema provided
        instance = TestModel.objects.create(name="test", schema="test_schema")
        self.assertEqual(instance.schema, "test_schema")

        # Should raise ValueError when schema is missing
        with self.assertRaises(ValidationError) as context:
            TestModel.objects.create(name="test")

        self.assertEqual(
            context.exception.message,
            "The 'schema' argument is required when creating a new instance",
        )
