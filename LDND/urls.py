from django.urls import path
from .views import last_done_list, choose_airline_aircraft, state_due_clearance

# Create your tests here.

urlpatterns = [
    path('', choose_airline_aircraft, name ='choose_airline_aircraft'),
    path('state_due_clearance/', state_due_clearance, name ='state_due_clearance'),
    path('last_done_list/', last_done_list, name ='last_done_list')
]
