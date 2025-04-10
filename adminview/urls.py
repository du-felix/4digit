from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from . import views


urlpatterns = [
    path("adminview/", views.adminview, name="adminview-home"),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('csv/', views.csv, name='adminview-csv'),
    path('users/<int:user_id>/', views.edit_user, name='user_edit'),
    path('add_user/', views.adding, name='add_user'),
    path('lehrer/', views.lehrer, name='lehrer'),
    path('add_lehrer/', views.add_lehrer, name='add_lehrer'),
    path('lehrer/<int:lehrer_id>/', views.edit_lehrer, name='lehrer_edit'),
    path('lehrer/csv/', views.lehrer_csv, name='lehrer_csv'),
]
