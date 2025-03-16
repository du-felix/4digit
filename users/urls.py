from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path("signup/", views.signup, name="signup"),
<<<<<<< HEAD
    path('login/', views.login, name='login'),
=======
    path('login/', LoginView.as_view(template_name='users/login.html', success_url='/success'), name='login'),
    path('success/', views.login_success, name='login_success'),
>>>>>>> 57f056b2bb65fd36a4ee1abd606ce384accbf866
]