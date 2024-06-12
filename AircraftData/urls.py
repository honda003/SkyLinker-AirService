from django.urls import path
from .views import aircraft_data_view, view_data

# Create your tests here.

urlpatterns = [
    path('', aircraft_data_view, name='aircraft_data_view'),
    path('view_data/', view_data, name='view_data'),
]