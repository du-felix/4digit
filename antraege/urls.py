from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", views.home, name="home"),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('neuer_antrag/', views.neuer_antrag, name='neuer_antrag'),
    path('user_antraege/', views.user_antraege, name='user_antraege'),
    path("antrag_bestaetigen/<str:token>/", views.antrag_bestaetigen, name="antrag_bestaetigen"),
    path('meine-antraege/', views.meine_antraege, name='meine_antraege'),
]