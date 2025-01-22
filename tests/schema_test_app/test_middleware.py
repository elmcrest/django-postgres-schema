from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.test import RequestFactory, TestCase, override_settings

from postgres_schema.middleware import SchemaMiddleware

User = get_user_model()


@override_settings(
    SERVER_NAME="example.com", POSTGRES_SCHEMA_MODEL="schema_test_app.Company"
)
class SchemaMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response_mock = Mock(return_value=HttpResponse())
        self.middleware = SchemaMiddleware(self.get_response_mock)

        # Mock tenant model
        self.tenant_mock = Mock()
        self.tenant_mock.objects.get.return_value = Mock(
            is_active=True, schema="test-tenant", name="Test Tenant"
        )
        self.middleware.tenant_model = self.tenant_mock

    def test_valid_subdomain(self):
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "test-tenant.example.com"
        request.user = Mock(is_authenticated=False)

        self.middleware(request)

        self.tenant_mock.objects.get.assert_called_with(schema="test-tenant")
        self.assertEqual(request.tenant.schema, "test-tenant")

    def test_invalid_chars_subdomain(self):
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "INVALID!.example.com"
        request.user = Mock(is_authenticated=False)

        self.middleware(request)

        self.tenant_mock.objects.get.assert_not_called()
        self.assertIsNone(request.tenant)

    def test_inactive_tenant(self):
        self.tenant_mock.objects.get.return_value.is_active = False
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "test-tenant.example.com"
        request.user = Mock(is_authenticated=False)

        self.middleware(request)

        self.assertIsNone(request.tenant)

    def test_missing_tenant_with_single_option(self):
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "example.com"
        request.user = Mock(
            is_authenticated=True,
            companies=Mock(
                active=Mock(
                    return_value=[
                        Mock(
                            schema="only-tenant",
                            url=Mock(return_value="http://only-tenant.example.com"),
                        )
                    ]
                )
            ),
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://only-tenant.example.com/")

    def test_template_context_injection(self):
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "test-tenant.example.com"
        request.user = Mock(
            is_authenticated=True,
            companies=Mock(
                active=Mock(
                    return_value=[
                        Mock(
                            schema="test-tenant",
                            name="Test Tenant",
                            url=Mock(return_value="http://test-tenant.example.com"),
                        )
                    ]
                )
            ),
        )

        template_response = TemplateResponse(request, "template.html", {})
        self.get_response_mock.return_value = template_response

        response = self.middleware(request)

        self.assertIn("selected_tenant", response.context_data)
        self.assertIn("available_tenants", response.context_data)
        self.assertEqual(
            response.context_data["available_tenants"][0]["schema"], "test-tenant"
        )

    @override_settings(SERVER_NAME=None)
    def test_missing_server_name_setting(self):
        with self.assertRaises(ValueError) as context:
            SchemaMiddleware(self.get_response_mock)

        self.assertEqual(context.exception.args[0], "SERVER_NAME setting is required")

    def test_async_support(self):
        async def async_get_response(request):
            return HttpResponse()

        middleware = SchemaMiddleware(async_get_response)
        self.assertTrue(middleware.async_capable)
