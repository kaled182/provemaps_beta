from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Model

from .models import ServiceAccount, ServiceAccountAuditLog, ServiceAccountToken

MANAGE_PERMISSION = "service_accounts.manage_tokens"
AUDIT_LOG_VIEW_PERMISSION = "service_accounts.view_serviceaccountauditlog"


if TYPE_CHECKING:
    TabularInlineBase = admin.TabularInline[  # type: ignore[type-arg]
        ServiceAccountToken
    ]
    ServiceAccountAdminBase = admin.ModelAdmin[  # type: ignore[type-arg]
        ServiceAccount
    ]
    AuditLogAdminBase = admin.ModelAdmin[  # type: ignore[type-arg]
        ServiceAccountAuditLog
    ]
    TokenAdminBase = admin.ModelAdmin[  # type: ignore[type-arg]
        ServiceAccountToken
    ]
else:  # pragma: no cover - runtime fallback for Django generics
    TabularInlineBase = admin.TabularInline
    ServiceAccountAdminBase = admin.ModelAdmin
    AuditLogAdminBase = admin.ModelAdmin
    TokenAdminBase = admin.ModelAdmin


class ServiceAccountTokenInline(TabularInlineBase):
    model = ServiceAccountToken
    extra = 0
    can_delete = False
    readonly_fields = (
        "last_four",
        "created_by",
        "created_at",
        "expires_at",
        "rotated_at",
        "revoked_at",
        "last_notified_at",
        "status",
    )
    fields = readonly_fields

    def status(self, obj: ServiceAccountToken) -> str:
        if obj.revoked_at:
            return f"Revoked {obj.revoked_at:%Y-%m-%d %H:%M}"
        if obj.is_expired:
            return "Expired"
        if obj.expires_at:
            return f"Active (expires {obj.expires_at:%Y-%m-%d})"
        return "Active"

    status.short_description = "State"  # type: ignore[attr-defined]

    def has_add_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccount | None = None,
    ) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccountToken | None = None,
    ) -> bool:
        return False


@admin.register(ServiceAccount)
class ServiceAccountAdmin(ServiceAccountAdminBase):
    change_form_template = (
        "admin/service_accounts/serviceaccount/change_form.html"
    )
    list_display = ("name", "email", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "email")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ServiceAccountTokenInline,)

    class TokenGenerationForm(forms.Form):
        expires_at = forms.DateTimeField(
            required=False,
            label="Expira em",
            help_text="Opcional; use data e hora no formato ISO.",
        )
        note = forms.CharField(
            required=False,
            label="Observação",
            widget=forms.Textarea(attrs={"rows": 3}),
        )

    def _can_manage(self, request: HttpRequest) -> bool:
        return request.user.is_superuser or request.user.has_perm(
            MANAGE_PERMISSION
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        if super().has_module_permission(request):
            return True
        return self._can_manage(request)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccount | None = None,
    ) -> bool:
        if super().has_view_permission(request, obj):
            return True
        return self._can_manage(request)

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccount | None = None,
    ) -> bool:
        if super().has_change_permission(request, obj):
            return True
        return self._can_manage(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        if super().has_add_permission(request):
            return True
        return self._can_manage(request)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccount | None = None,
    ) -> bool:
        if super().has_delete_permission(request, obj):
            return True
        return self._can_manage(request)

    def save_model(
        self,
        request: HttpRequest,
        obj: ServiceAccount,
        form: ModelForm,
        change: bool,
    ) -> None:
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/generate-token/",
                self.admin_site.admin_view(self.generate_token_view),
                name="service_accounts_serviceaccount_generate_token",
            ),
        ]
        return custom_urls + urls

    def generate_token_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> HttpResponse:
        if not self.has_change_permission(request):
            raise PermissionDenied

        account = self.get_object(request, object_id)
        if not account:
            self.message_user(
                request,
                "Conta de serviço não encontrada.",
                level=messages.ERROR,
            )
            return redirect("admin:service_accounts_serviceaccount_changelist")

        FormClass = self.TokenGenerationForm
        if request.method == "POST":
            form = FormClass(request.POST)
            if form.is_valid():
                expires_at = form.cleaned_data.get("expires_at")
                if expires_at and timezone.is_naive(expires_at):
                    expires_at = timezone.make_aware(
                        expires_at,
                        timezone.get_current_timezone(),
                    )

                user: Model | None = None
                if request.user.is_authenticated:
                    user = cast(Model, request.user)

                plain_token, token_obj = account.create_token(
                    created_by=user,
                    expires_at=expires_at,
                    note=(
                        form.cleaned_data.get("note")
                        or "Token gerado via admin"
                    ),
                    remote_addr=request.META.get("REMOTE_ADDR"),
                )

                token_display = format_html(
                    "<strong>{}</strong>",
                    plain_token,
                )
                messages.success(
                    request,
                    format_html(
                        (
                            "Token criado com sucesso. Copie agora: {} "
                            "(últimos 4: {})"
                        ),
                        token_display,
                        token_obj.last_four,
                    ),
                )
                return redirect(
                    "admin:service_accounts_serviceaccount_change",
                    object_id=account.pk,
                )
        else:
            form = FormClass()

        context: Dict[str, Any] = {}
        context.update(self.admin_site.each_context(request))
        context.update(
            {
                "opts": self.model._meta,
                "original": account,
                "title": "Gerar token de serviço",
                "form": form,
            }
        )
        return TemplateResponse(
            request,
            "admin/service_accounts/serviceaccount/generate_token.html",
            context,
        )


@admin.register(ServiceAccountAuditLog)
class ServiceAccountAuditLogAdmin(AuditLogAdminBase):
    list_display = ("created_at", "account", "action", "actor")
    list_filter = ("action", "created_at")
    search_fields = ("account__name", "message", "actor__username")
    readonly_fields = (
        "account",
        "action",
        "actor",
        "message",
        "remote_addr",
        "extra_data",
        "created_at",
    )

    def _can_view(self, request: HttpRequest) -> bool:
        return request.user.is_superuser or request.user.has_perm(
            AUDIT_LOG_VIEW_PERMISSION
        ) or request.user.has_perm(MANAGE_PERMISSION)

    def has_module_permission(self, request: HttpRequest) -> bool:
        if super().has_module_permission(request):
            return True
        return self._can_view(request)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccountAuditLog | None = None,
    ) -> bool:
        if super().has_view_permission(request, obj):
            return True
        return self._can_view(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccountAuditLog | None = None,
    ) -> bool:
        return False


@admin.register(ServiceAccountToken)
class ServiceAccountTokenAdmin(TokenAdminBase):
    def _can_view(self, request: HttpRequest) -> bool:
        return request.user.is_superuser or request.user.has_perm(
            MANAGE_PERMISSION
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        if super().has_module_permission(request):
            return True
        return self._can_view(request)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccountToken | None = None,
    ) -> bool:
        if super().has_view_permission(request, obj):
            return True
        return self._can_view(request)

    list_display = (
        "account",
        "last_four",
        "created_at",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("created_at", "revoked_at")
    search_fields = ("account__name", "last_four")
    readonly_fields = (
        "account",
        "token_hash",
        "last_four",
        "created_by",
        "created_at",
        "expires_at",
        "rotated_at",
        "revoked_at",
        "last_notified_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ServiceAccountToken | None = None,
    ) -> bool:
        return False
