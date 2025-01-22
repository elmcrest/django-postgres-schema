import ast
from pathlib import Path

from django.conf import settings
from django.core.management.commands.makemigrations import Command as BaseCommand


class MigrationTransformer(ast.NodeTransformer):
    def __init__(self, operation_class):
        self.operation_class = operation_class

    def visit_Assign(self, node):
        if not self._is_operations_list(node):
            return node

        operations = node.value.elts
        wrapped_ops = []
        for op in operations:
            if self._needs_wrapping(op):
                wrapped_ops.append(
                    ast.Call(
                        func=ast.Name(id=self.operation_class, ctx=ast.Load()),
                        args=[op],
                        keywords=[],
                    )
                )
            else:
                wrapped_ops.append(op)

        node.value.elts = wrapped_ops
        return node

    def _is_operations_list(self, node):
        return (
            isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "operations"
            and isinstance(node.value, ast.List)
        )

    def _needs_wrapping(self, op):
        # Extend logic based on operation type
        return isinstance(op, ast.Call) and getattr(op.func, "attr", "") in {
            "CreateModel",
            "AddField",
            "AlterField",
            "RemoveField",
        }


class Command(BaseCommand):
    """
    Hook to wrap generated migrations with postgres_schema RunInSchema operations.
    """

    success_msg = "Successfully wrapped migrations."

    def write_migration_files(self, changes):
        super().write_migration_files(changes)

        for file_name in self.written_files:
            self._transform_migration(file_name)

    def _get_app_label(self, file_name):
        return Path(file_name).parent.parent.name

    def _transform_migration(self, file_name):
        with open(file_name, "r") as f:
            tree = ast.parse(f.read())

        app_label = self._get_app_label(file_name)
        if app_label in settings.POSTGRES_SCHEMA_APPS:
            operation_class = "RunInTemplate"
        elif app_label in settings.POSTGRES_SCHEMA_MODEL:
            operation_class = "RunInPublic"
        else:
            return
        # Add imports
        tree.body.insert(
            0,
            ast.parse(f"from postgres_schema.operations import {operation_class}"),
        )

        # Transform operations
        transformer = MigrationTransformer(operation_class=operation_class)
        transformed = transformer.visit(tree)
        ast.fix_missing_locations(transformed)

        with open(file_name, "w") as f:
            f.write(ast.unparse(transformed))
