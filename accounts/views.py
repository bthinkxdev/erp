from django.contrib.auth import views as auth_views


# Re-export for URL routing convenience.
# All logic is in Django's built-in auth views.
LoginView = auth_views.LoginView
LogoutView = auth_views.LogoutView
