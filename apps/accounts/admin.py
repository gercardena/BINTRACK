from django.contrib import admin

from .models import SubscriptionGrant


@admin.register(SubscriptionGrant)
class SubscriptionGrantAdmin(admin.ModelAdmin):
    """The audit log is visible to staff but cannot be changed from admin."""

    list_display = (
        "owner",
        "granted_by",
        "granted_from",
        "granted_until",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("owner__username", "granted_by__username", "reason")
    readonly_fields = (
        "owner",
        "granted_by",
        "reason",
        "previous_end",
        "granted_from",
        "granted_until",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ("GET", "HEAD")

    def has_delete_permission(self, request, obj=None):
        return False
