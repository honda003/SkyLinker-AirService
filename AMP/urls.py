from django.urls import path
from . import views

# Create your tests here.

urlpatterns = [
    path('', views.excel_data_view, name='excel_data_view')
]