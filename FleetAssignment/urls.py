from django.urls import path
from .views import upload_flights_excel, download_for_routing_excel, process_flight_columns, upload_itineraries_excel, process_itinerary_columns, fleet_data, solver_selection, optional_flights_selection, ISD_IFAM, FAM, download_excel, download_flights_sample_excel, download_itineraries_sample_excel, demand_adjustment, recapture_ratio, IFAM, preview_flights_sample, preview_itineraries_sample

urlpatterns = [
    path('', upload_flights_excel, name='upload_flights_excel'),
    path('download-flights-sample-excel/', download_flights_sample_excel, name='download_flights_sample_excel'),
    path('preview_flights_sample/', preview_flights_sample, name='preview_flights_sample'),
    path('process_flight_columns/', process_flight_columns, name='process_flight_columns'),
    path('fleet_data/', fleet_data, name='fleet_data'),
    path('solver_selection/', solver_selection, name='solver_selection'),
    path('recapture_ratio/', recapture_ratio, name='recapture_ratio'),
    path('demand-adjustment/', demand_adjustment, name='demand_adjustment'),
    path('upload_itineraries_excel/', upload_itineraries_excel, name='upload_itineraries_excel'),
    path('download-itineraries-sample-excel/', download_itineraries_sample_excel, name='download_itineraries_sample_excel'),
    path('preview_itineraries_sample/', preview_itineraries_sample, name='preview_itineraries_sample'),
    path('process_itinerary_columns/', process_itinerary_columns, name='process_itinerary_columns'),
    path('optional_flights_selection/', optional_flights_selection, name='optional_flights_selection'),
    path('IFAM/', IFAM, name='IFAM'),
    path('ISD_IFAM/', ISD_IFAM, name='ISD_IFAM'),
    path('FAM/', FAM, name='FAM'),
    path('download-excel/', download_excel, name='download_excel'),
    path('download/<str:fleet_type>/', download_for_routing_excel, name='download-fleet-excel'),
    # other URL patterns
    # Add more paths as needed for further steps
]