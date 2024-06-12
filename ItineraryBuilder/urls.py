from django.urls import path
from .views import upload_excel_Itin, process_columns_Itin, turn_around_and_connection_Itin, results_Itin, upload_airport_coordinates, process_columns_airport, download_IB_flights_sample_excel, preview_IB_flights_sample, download_airports_sample_excel, preview_airports_sample, download_IB_results_excel, download_req_format_excel

urlpatterns = [
    path('', upload_excel_Itin, name='upload_excel_Itin'),
    path('download_IB_flights_sample_excel/', download_IB_flights_sample_excel, name='download_IB_flights_sample_excel'),
    path('preview_IB_flights_sample/', preview_IB_flights_sample, name='preview_IB_flights_sample'),
    path('process_columns/', process_columns_Itin, name='process_columns_Itin'),
    path('upload_airport_coordinates/', upload_airport_coordinates, name='upload_airport_coordinates'),
    path('download_airports_sample_excel/', download_airports_sample_excel, name='download_airports_sample_excel'),
    path('preview_airports_sample/', preview_airports_sample, name='preview_airports_sample'),
    path('process_columns_airport/', process_columns_airport, name='process_columns_airport'),
    path('turn_around_and_connection/', turn_around_and_connection_Itin, name='turn_around_and_connection_Itin'),
    path('results/', results_Itin, name='results_Itin'),
    path('download_IB_results_excel/', download_IB_results_excel, name='download_IB_results_excel'),
    path('download_req_format_excel/', download_req_format_excel, name='download_req_format_excel'),  
]