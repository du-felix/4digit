<<<<<<< HEAD
from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path("adminview/", views.adminview, name="adminview-home")
]
=======
from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminview, name='adminview'),
]
>>>>>>> 57f056b (adminview_first)
