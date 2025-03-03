from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Admin-Berechtigung', {'fields': ('is_app_admin',)}),
    )
    list_display = list(UserAdmin.list_display) + ['is_app_admin']
    list_filter = list(UserAdmin.list_filter) + ['is_app_admin']

admin.site.register(CustomUser, CustomUserAdmin)
