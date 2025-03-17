from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
 # Importiere dein benutzerdefiniertes User-Modell

admin.site.register(CustomUser) 