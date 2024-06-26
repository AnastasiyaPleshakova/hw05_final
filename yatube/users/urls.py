from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.urls import path

from . import views


app_name = 'users'

urlpatterns = [
    path('login/',
         LoginView.as_view(template_name='users/login.html'),
         name='login'),
    path('logout/',
         LogoutView.as_view(template_name='users/logged_out.html'),
         name='logout'
         ),
    path('password_change/',
         PasswordChangeView.as_view(
             template_name='users/password_change_form.html'
         ),
         name='password_change'),
    path('password_reset/',
         PasswordResetView.as_view(
             template_name='users/password_reset_form.html'
         ),
         name='password_reset'),
    path('signup/', views.SignUp.as_view(), name='signup'),
]
