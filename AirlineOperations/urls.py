from django.urls import path
from . import views, operations_dashboard_view
from django.contrib.auth import views as auth_views
# Create your tests here.

urlpatterns = [
    path('', views.login_view, name='operations-login'),
    path('dashboard/', operations_dashboard_view.operations_dashboard_view, name='operations_dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='operations-login'), name='logout'),
]