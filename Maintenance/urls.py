from django.urls import path
from . import views, maintenance_dashboard_view
from django.contrib.auth import views as auth_views
# Create your tests here.

urlpatterns = [
    path('', views.login_view, name='maintenance-login'),
    path('dashboard/', maintenance_dashboard_view.maintenance_dashboard_view, name='maintenance_dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='maintenance-login'), name='logout'),
]