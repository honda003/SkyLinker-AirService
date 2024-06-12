from django.urls import path
from .views import upload_excel, process_columns, turn_around_and_hub_selection, fpd_decision, cycle_and_aircraft_input, optimization_step, download_R_flights_sample_excel, preview_R_flights_sample, download_R_results_excel

urlpatterns = [
    path('', upload_excel, name='upload_excel'),
    path('download_R_flights_sample_excel/', download_R_flights_sample_excel, name='download_R_flights_sample_excel'),
    path('preview_R_flights_sample/', preview_R_flights_sample, name='preview_R_flights_sample'),
    path('process_columns/', process_columns, name='process_columns'),
    path('turn_around_and_hub_selection/', turn_around_and_hub_selection, name='turn_around_and_hub_selection'),
    path('fpd_decision/', fpd_decision, name='fpd_decision'),
    path('cycle_and_aircraft_input/', cycle_and_aircraft_input, name='cycle_and_aircraft_input'),
    path('optimization_step/', optimization_step, name='optimization_step'),
    path('download_R_results_excel/', download_R_results_excel, name='download_R_results_excel'),  
    # Add more paths as needed for further steps
]