from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from . import views


urlpatterns = [
    path("adminview/", views.adminview, name="adminview-home"),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('csv/', views.csv, name='csv'),
    path('users/<int:user_id>/', views.adminview, name='user_edit'),
]
