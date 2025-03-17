from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from . import views


urlpatterns = [
    path("adminview/", views.adminview, name="adminview-home"),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('csv/', views.csv, name='csv'),
    path('users/<int:user_id>/', views.adminview, name='user_edit'),
    path('add_user/', views.adding, name='add_user'),
]
<<<<<<< HEAD
=======
from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminview, name='adminview'),
]
>>>>>>> 57f056b (adminview_first)
=======
>>>>>>> ffdd6c1 (adminview user-list added, editing possible)
