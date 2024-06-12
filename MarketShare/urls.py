from django.urls import path
from .views import use_historical_data, upload_historical_data_excel, process_historical_data_columns, upload_Itinerary_excel, process_Itinerary_columns, upload_unconstrained_demand_excel, download_unconstrained_demand_excel, preview_unconstrained_demand, calculate_probability, market_share_results, download_MS_results_excel, recommendations
urlpatterns = [
    path('', use_historical_data, name='use_historical_data'),
    path('upload_historical_data_excel/', upload_historical_data_excel, name='upload_historical_data_excel'),
    path('process_historical_data_columns/', process_historical_data_columns, name='process_historical_data_columns'),
    path('upload_Itinerary_excel/', upload_Itinerary_excel, name='upload_Itinerary_excel'),
    path('process_Itinerary_columns/', process_Itinerary_columns, name='process_Itinerary_columns'),
    path('calculate_probability/', calculate_probability, name='calculate_probability'),
    path('upload_unconstrained_demand_excel/', upload_unconstrained_demand_excel, name='upload_unconstrained_demand_excel'),
    path('download_unconstrained_demand_excel/', download_unconstrained_demand_excel, name='download_unconstrained_demand_excel'),
    path('preview_unconstrained_demand/', preview_unconstrained_demand, name='preview_unconstrained_demand'),
    path('market_share_results/', market_share_results, name='market_share_results'),
    path('download_MS_results_excel/', download_MS_results_excel, name='download_MS_results_excel'), 
    path('recommendations/', recommendations, name='recommendations'),

    # Add more paths as needed for further steps
]