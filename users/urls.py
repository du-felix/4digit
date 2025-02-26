from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'),
]