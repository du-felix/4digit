from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminview, name='adminview'),
]