from django.urls import path

from . import auth_views, views

app_name = "practice"
urlpatterns = [
    path("auth", auth_views.session_login, name="login"),
    path("auth/validate", auth_views.session_status, name="session-status"),
    path("auth/logout", auth_views.session_logout, name="logout"),
    path("announcements", views.announcements, name="announcements"),
    path("announcements/", views.announcements),
]
