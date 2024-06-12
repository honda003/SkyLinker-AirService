from django.urls import path
from .views import upcoming_tasks, uk_choose_airline_aircraft

urlpatterns = [
    path('', uk_choose_airline_aircraft, name ='uk_choose_airline_aircraft'),
    path('upcoming_tasks/', upcoming_tasks, name='upcoming_tasks'),
]