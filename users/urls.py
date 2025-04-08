from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path('login/', views.login, name='login'),
    path("activate/<uid>/<token>/", views.activate, name="activate"),
]