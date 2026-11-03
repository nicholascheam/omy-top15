from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login", views.login_redirect, name="login"),
    path("oauth/callback", views.oauth_callback, name="oauth_callback"),
    path("logout", views.logout_view, name="logout"),
    path("vote", views.vote, name="vote"),
    path("my-ballot", views.my_ballot, name="my_ballot"),
    path("my-ballot/edit", views.edit_ballot, name="edit_ballot"),
    path("api/players/search", views.search_players, name="search_players"),
]