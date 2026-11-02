from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login", views.login_redirect, name="login"),
    path("oauth/callback", views.oauth_callback, name="oauth_callback"),
    path("logout", views.logout_view, name="logout"),
    path("secret", views.protected_test, name="secret"),
]