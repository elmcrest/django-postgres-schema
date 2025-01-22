import string
from typing import Optional, Set

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.apps import apps
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect


class SchemaMiddleware:
    """Schema-based tenant routing middleware with subdomain support."""

    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.tenant_model = self._get_tenant_model()
        self.allowed_chars = self._get_allowed_chars()
        self.domain = self._get_domain()

        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    @staticmethod
    def _get_tenant_model():
        model_path = getattr(settings, "POSTGRES_SCHEMA_MODEL", None)
        if not model_path:
            raise ValueError("POSTGRES_SCHEMA_MODEL setting is required")
        app_name, model_name = model_path.split(".")
        return apps.get_model(app_name, model_name)

    @staticmethod
    def _get_allowed_chars() -> Set[str]:
        return set(
            getattr(
                settings,
                "POSTGRES_SCHEMA_ALLOWED_CHARS",
                string.ascii_lowercase + string.digits + "-",
            )
        )

    @staticmethod
    def _get_domain() -> str:
        domain = getattr(settings, "SERVER_NAME", None)
        if not domain:
            raise ValueError("SERVER_NAME setting is required")
        return domain

    def get_subdomain(self, request: HttpRequest) -> str:
        """Extract and validate subdomain from request."""
        host = request.META.get("HTTP_HOST", "").split(":")[0]
        if not host.endswith(self.domain):
            return ""
        subdomain = host[: -len(self.domain)]
        return subdomain.rstrip(".") if subdomain else ""

    def is_valid_schema(self, schema: str) -> bool:
        """Validate schema name against allowed characters."""
        return set(schema) <= self.allowed_chars

    async def __acall__(self, request: HttpRequest) -> HttpResponse:
        redirect = await self._process_request(request)
        if redirect:
            return redirect

        response = await self.get_response(request)

        if hasattr(response, "render"):
            response = await self._process_template_response(request, response)

        return response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        redirect = self._process_request(request)
        if redirect:
            return redirect

        response = self.get_response(request)

        if hasattr(response, "render"):
            response = self._process_template_response(request, response)

        return response

    def _process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        request.tenant = None

        subdomain = self.get_subdomain(request)
        if not subdomain or not self.is_valid_schema(subdomain):
            return self._handle_missing_tenant(request)

        try:
            tenant = self.tenant_model.objects.get(schema=subdomain)
            if tenant.is_active:
                tenant.activate()
                request.tenant = tenant
                return None
        except self.tenant_model.DoesNotExist:
            pass

        return self._handle_missing_tenant(request)

    def _handle_missing_tenant(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle requests without valid tenant context."""
        if not request.user.is_authenticated:
            return None

        active_tenants = request.user.companies.active()
        if len(active_tenants) == 1:
            return HttpResponseRedirect(
                f"{active_tenants[0].url(request)}{request.path}"
            )

        return None

    def _process_template_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Inject tenant context into template response."""
        if not hasattr(response, "context_data") or response.context_data is None:
            return response

        current_schema = request.tenant.schema if request.tenant else ""
        response.context_data.update(
            {
                "selected_tenant": request.tenant,
                "available_tenants": self._get_available_tenants(
                    request, current_schema
                )
                if request.user.is_authenticated
                else [],
            }
        )

        return response

    def _get_available_tenants(self, request: HttpRequest, current: str) -> list:
        """Get list of available tenants for authenticated user."""
        return [
            {
                "name": t.name,
                "schema": t.schema,
                "url": t.url(request),
                "current": t.schema == current,
            }
            for t in request.user.companies.active()
        ]
