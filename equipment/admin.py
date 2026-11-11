from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Booking, Resource, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Access", {"fields": ("role",)}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Access", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "total_quantity", "is_active")
    list_filter = ("is_active", "location")
    search_fields = ("name", "location")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("resource", "user", "start_at", "end_at", "quantity", "status")
    list_filter = ("status", "resource")
    search_fields = ("resource__name", "user__username")
    readonly_fields = ("created_at", "updated_at")
