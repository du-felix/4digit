from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    # path("signup/", views.signup, name="signup"),
    path('login/', views.login, name='login'),
    path("activate/<uid>/<token>/", views.activate, name="activate"),
    path("activate_account/", views.activate_account, name="activate_account"),
    path("edit_password/<uid>/<token>/", views.edit_password, name="edit_password"),
    path("get_link/", views.get_link, name="get_link"),
]