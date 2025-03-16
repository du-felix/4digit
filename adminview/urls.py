from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path("adminview/", views.adminview, name="adminview-home")
]
