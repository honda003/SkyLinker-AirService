from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ExcelUploadForm, create_column_index_form, has_historical_data_form
from .utils import SyncReadExcel, Itin_ColumnIndex, DataEditing, ItineraryAnalyzer, propabilities_and_demand, regression_coefficients
import pandas as pd
import json
import pandas as pd
from io import StringIO
import pandas as pd
from pyomo.util.infeasible import log_infeasible_constraints
import pyomo.environ as pyo 
from pyomo.environ import *
from pyomo.opt import SolverFactory
from django.conf import settings
import matplotlib.pyplot as plt
import base64
from django.shortcuts import render
from django.utils.safestring import mark_safe
from io import BytesIO
import base64
import traceback
import os
from django.http import FileResponse, HttpResponseNotFound, HttpResponse, HttpResponseServerError
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import logging
import numpy as np

logger = logging.getLogger(__name__)

@login_required
def use_historical_data(request):
    HistoricalDataForm = has_historical_data_form()  # Get the form class from the function
    if request.method == 'POST':
        form = HistoricalDataForm(request.POST)
        if form.is_valid():
            has_data = form.cleaned_data['has_historical_data']
            if has_data == 'yes':
                return HttpResponseRedirect(reverse('upload_historical_data_excel'))
            elif has_data == 'no':
                My_Egyptian_market_betas = {
                    'Double Stop in Double Stop':-0.291661,
                    'Double Stop in Non Stop':-0.0432075,
                    'Non Stop in Non Stop':0.639733,
                    'Single Stop in Non Stop':0.038563,
                    'Single Stop in Single Stop':0.34343,
                    'Low Fare':0.19705,
                    'High Fare':-0.19705,
                    'Point of Sale Weighted City Presence':-0.043654,
                    'second best connection':-0.44516,
                    'midnight–6 a.m.':-0.0613285,
                    '6–9 a.m.':0.220715,
                    '9–noon':0.178997,
                    '12–3 p.m.':-0.0123549,
                    '3–6 p.m.':-0.097794,
                    '6–9 p.m.':-0.0980845,
                    '9–midnight':-0.065310,
                    'Short Distance':0.137611,
                    'Long Distance':-0.137618 }
                My_Egyptian_market_betas_df = pd.DataFrame(My_Egyptian_market_betas, index=[0])
                
                historical_market_betas = My_Egyptian_market_betas_df
                print(f'historical_market_betas: {historical_market_betas}')
                
                historical_market_betas_df_json = historical_market_betas.to_json(orient='split')
                
                request.session['historical_market_betas_df'] = historical_market_betas_df_json
                return HttpResponseRedirect(reverse('upload_Itinerary_excel'))

        else:
            # In case form is not valid, re-render the current form with errors
            return render(request, 'pages/marketshare.html', {'has_historical_data_form': form})
    else:
        form = has_historical_data_form()
    return render(request, 'pages/marketshare.html', {'has_historical_data_form': form})
    
def upload_historical_data_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            file_content = excel_file.read()
            file_name = excel_file.name

            read_excel = SyncReadExcel(file_content=file_content, file_name=file_name)
            
            try:
                read_excel.read_data()  # Synchronously read the Excel file
            except ValueError as e:
                # Handle the error (e.g., display an error message to the user)
                return render(request, 'pages/marketshare.html', {'hs_excel_form': form, 'hs_error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            historical_Itineraries_df_json = read_excel.get_dataframe().to_json(orient='split')
            historical_Itineraries_list = read_excel.get_data_list()

            # Store in session
            request.session['historical_Itineraries_df'] = historical_Itineraries_df_json
            request.session['historical_Itineraries_list'] = historical_Itineraries_list

            return redirect('process_historical_data_columns')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/marketshare.html', {'hs_excel_form': form})

def process_historical_data_columns(request):
    if 'historical_Itineraries_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_historical_data_excel')

    # Load DataFrame from session
    historical_Itineraries_df_json = request.session.get('historical_Itineraries_df')
    historical_Itineraries_df = pd.read_json(StringIO(historical_Itineraries_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    column_index = Itin_ColumnIndex(historical_Itineraries_df)

    if request.method == 'POST' and 'missing_columns' in request.session:
        # User is submitting indexes for missing columns
        form = create_column_index_form(request.session['missing_columns'])(request.POST)
        if form.is_valid():
            provided_indexes = {col: form.cleaned_data[f"{col}_index"] - 1 for col in request.session['missing_columns']}
            
            error_messages = []
            for col, idx in provided_indexes.items():
                if idx >= len(historical_Itineraries_df.columns) or idx < 0:
                    error_messages.append(f"Index for {col} is out of the valid range (1 - {len(historical_Itineraries_df.columns)}).")
                    continue

                is_valid, message = column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/marketshare.html', {'hs_column_form': form, 'hs_error_messages': error_messages})
            
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**column_index.columns, **provided_indexes}
            # Save complete column indexes in session
            request.session['column_indexes'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            calculate_betas(request)

            # Proceed to turn-around and hub selection
            return redirect('upload_Itinerary_excel')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/marketshare.html', {'hs_column_form': form})
    else:
        # Either we have all columns from the start or we need to ask for them
        if column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = column_index.missing_columns
            form = create_column_index_form(column_index.missing_columns)()
            return render(request, 'pages/marketshare.html', {'hs_column_form': form})
        else:
            # No missing columns, use found columns
            request.session['column_indexes'] = json.dumps(column_index.columns)
            calculate_betas(request)

            # Proceed to turn-around and hub selection
            return redirect('upload_Itinerary_excel')
        
def calculate_betas(request):
    
    historical_Itineraries_df_json = request.session.get('historical_Itineraries_df')
    historical_Itineraries_df = pd.read_json(StringIO(historical_Itineraries_df_json), orient='split')
    # ****************** Find Itineraries columns **************** #
    
    column_indexes = json.loads(request.session.get('column_indexes', '{}'))
    airline_name_col = column_indexes.get('Airline')
    origin_col = column_indexes.get('origin')
    departure_col = column_indexes.get('departure')
    destination_col = column_indexes.get('destination')
    arrival_col = column_indexes.get('arrival')
    duration_col = column_indexes.get('duration')
    type_col = column_indexes.get('type')
    First_stop_col = column_indexes.get('First Stop')
    First_transit_col = column_indexes.get('First Transit Time')
    Second_stop_col = column_indexes.get('Second Stop')
    Second_transit_col = column_indexes.get('Second Transit Time')
    itinerary_price_col = column_indexes.get('Itinerary Price')
    distance_col = column_indexes.get('distance')

    
    user_airline_name = 'Egypt Air'
    
    print(f'destination column ------>: {destination_col}')
    print(f'distance_col column ------>: {distance_col}')
    print(f'airline_name_col column ------>: {airline_name_col}')





    data_editor = DataEditing(historical_Itineraries_df = historical_Itineraries_df,airline_name_col = airline_name_col,type_col = type_col,origin_col = origin_col,destination_col= destination_col
                            ,itinerary_price_col = itinerary_price_col,duration_col=duration_col,distance_col=distance_col,user_airline_name=user_airline_name,First_transit_col=First_transit_col)

    data_editor.read_data()

    data_editor.Sort_airlines_column()

    #Level of Service Data

    data_editor.determine_market_level()
    data_editor.calculate_level_of_service()


    # #Aircraft Type & Size Data                           ''' Dont activate '''
    # data_editor.fill_missing_aircraft_details()
    # data_editor.aircraft_type_and_size()


    # #Code Share Data                                     ''' Dont activate '''
    # data_editor.create_code_share_column()

    # Calculate fare ratio
    data_editor.calculate_fare_ratio()

    # Apply fare categorization based on market averages
    data_editor.apply_fare_categorization()

    #Point of Sale Weighted City Presence
    data_editor.calculate_total_itineraries_per_market()
    data_editor.calculate_itineraries_per_airline_per_market()
    data_editor.calculate_proportion_per_airline_per_market()

    #Second Best Connection                               ''' activate later'''
    data_editor.calculate_second_shortest_transit_time()

    #Departure Time Categorizing
    departure_col_str = historical_Itineraries_df.columns[departure_col]
    data_editor.apply_time_slots(departure_col_str)

    # #Aircraft Size Categorization                          ''' activate later'''
    # data_editor.apply_size_category()


    #Distance Ratio 
    data_editor.calculate_min_distance()
    data_editor.calculate_distance_ratio()
    #Distance Ratio Categorization
    test = data_editor.apply_distance_categorization()


    # Define the list of columns to drop
    columns_to_drop = ['Capacity', 'Airplane of second leg', 'Capacity.1', 'Airplane of third leg', 'Capacity.2', 'Priority', 'Best Priority','min_distance', 'Transit Time Minutes']

    # Call the drop_columns method
    data_editor.drop_columns(columns_to_drop)
    data_editor.replace_empty_values()

    Itineraries_df__edited=data_editor.save_summary()

    ''' Use these to cacualte probabilities and my airline demand'''


    analyzer = ItineraryAnalyzer(Itineraries_df__edited)
    analyzer.create_itinerary_id()
    analyzer.count_unique_itineraries()
    Common_itineraries_count_df= analyzer.save_summary()

    # Starting calculation of betas
    betas_calculator = regression_coefficients(Common_itineraries_count_df)

    betas_calculator.data_filter()
    betas_calculator.regression_calculation()
    historical_market_betas = betas_calculator.save_coefficients_to_excel()
    
    
    print(f'historical_market_betas: {historical_market_betas}')
    
    historical_market_betas_df_json = historical_market_betas.to_json(orient='split')
    
    request.session['historical_market_betas_df'] = historical_market_betas_df_json 
        
def upload_Itinerary_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            file_content = excel_file.read()
            file_name = excel_file.name

            read_excel = SyncReadExcel(file_content=file_content, file_name=file_name)
            
            try:
                read_excel.read_data()  # Synchronously read the Excel file
            except ValueError as e:
                # Handle the error (e.g., display an error message to the user)
                return render(request, 'pages/marketshare.html', {'i_excel_form': form, 'i_error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            Itineraries_df_json = read_excel.get_dataframe().to_json(orient='split')
            Itineraries_list = read_excel.get_data_list()

            # Store in session
            request.session['Itineraries_df'] = Itineraries_df_json
            request.session['Itineraries_list'] = Itineraries_list

            return redirect('process_Itinerary_columns')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/marketshare.html', {'i_excel_form': form})

def process_Itinerary_columns(request):
    if 'Itineraries_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_Itinerary_excel')

    # Load DataFrame from session
    Itineraries_df_json = request.session.get('Itineraries_df')
    Itineraries_df = pd.read_json(StringIO(Itineraries_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    i_column_index = Itin_ColumnIndex(Itineraries_df)

    if request.method == 'POST' and 'missing_columns' in request.session:
        # User is submitting indexes for missing columns
        form = create_column_index_form(request.session['missing_columns'])(request.POST)
        if form.is_valid():
            i_provided_indexes = {col: form.cleaned_data[f"{col}_index"] - 1 for col in request.session['missing_columns']}
            
            error_messages = []
            for col, idx in i_provided_indexes.items():
                if idx >= len(Itineraries_df.columns) or idx < 0:
                    error_messages.append(f"Index for {col} is out of the valid range (1 - {len(Itineraries_df.columns)}).")
                    continue

                is_valid, message = i_column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/marketshare.html', {'i_column_form': form, 'i_error_messages': error_messages})
            
            # Merge provided indexes with those found by ColumnIndex
            i_complete_indexes = {**i_column_index.columns, **i_provided_indexes}
            # Save complete column indexes in session
            request.session['i_column_indexes'] = json.dumps(i_complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            #calculate_probability(request)

            # Proceed to turn-around and hub selection
            return redirect('calculate_probability')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/marketshare.html', {'i_column_form': form})
    else:
        # Either we have all columns from the start or we need to ask for them
        if i_column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = i_column_index.missing_columns
            form = create_column_index_form(i_column_index.missing_columns)()
            return render(request, 'pages/marketshare.html', {'i_column_form': form})
        else:
            # No missing columns, use found columns
            request.session['i_column_indexes'] = json.dumps(i_column_index.columns)
            #calculate_probability(request)

            # Proceed to turn-around and hub selection
            return redirect('calculate_probability')
       
def calculate_probability(request):
    
    Itineraries_df_json = request.session.get('Itineraries_df')
    Itineraries_df = pd.read_json(StringIO(Itineraries_df_json), orient='split')
    # ****************** Find Itineraries columns **************** #
    
    i_column_indexes = json.loads(request.session.get('i_column_indexes', '{}'))
    airline_name_col = i_column_indexes.get('Airline')
    origin_col = i_column_indexes.get('origin')
    departure_col = i_column_indexes.get('departure')
    destination_col = i_column_indexes.get('destination')
    arrival_col = i_column_indexes.get('arrival')
    duration_col = i_column_indexes.get('duration')
    type_col = i_column_indexes.get('type')
    First_stop_col = i_column_indexes.get('First Stop')
    First_transit_col = i_column_indexes.get('First Transit Time')
    Second_stop_col = i_column_indexes.get('Second Stop')
    Second_transit_col = i_column_indexes.get('Second Transit Time')
    itinerary_price_col = i_column_indexes.get('Itinerary Price')
    distance_col = i_column_indexes.get('distance')

    
    user_airline_name = 'Egypt Air'
    
    print(f'destination column ------>: {destination_col}')
    print(f'distance_col column ------>: {distance_col}')
    print(f'airline_name_col column ------>: {airline_name_col}')





    data_editor = DataEditing(historical_Itineraries_df = Itineraries_df,airline_name_col = airline_name_col,type_col = type_col,origin_col = origin_col,destination_col= destination_col
                            ,itinerary_price_col = itinerary_price_col,duration_col=duration_col,distance_col=distance_col,user_airline_name=user_airline_name,First_transit_col=First_transit_col)

    data_editor.read_data()

    data_editor.Sort_airlines_column()

    #Level of Service Data

    data_editor.determine_market_level()
    data_editor.calculate_level_of_service()


    # #Aircraft Type & Size Data                           ''' Dont activate '''
    # data_editor.fill_missing_aircraft_details()
    # data_editor.aircraft_type_and_size()


    # #Code Share Data                                     ''' Dont activate '''
    # data_editor.create_code_share_column()

    # Calculate fare ratio
    data_editor.calculate_fare_ratio()

    # Apply fare categorization based on market averages
    data_editor.apply_fare_categorization()

    #Point of Sale Weighted City Presence
    data_editor.calculate_total_itineraries_per_market()
    data_editor.calculate_itineraries_per_airline_per_market()
    data_editor.calculate_proportion_per_airline_per_market()

    #Second Best Connection                               ''' activate later'''
    data_editor.calculate_second_shortest_transit_time()

    #Departure Time Categorizing
    departure_col_str = Itineraries_df.columns[departure_col]
    data_editor.apply_time_slots(departure_col_str)

    # #Aircraft Size Categorization                          ''' activate later'''
    # data_editor.apply_size_category()


    #Distance Ratio 
    data_editor.calculate_min_distance()
    data_editor.calculate_distance_ratio()
    #Distance Ratio Categorization
    test = data_editor.apply_distance_categorization()


    # Define the list of columns to drop
    columns_to_drop = ['Capacity', 'Airplane of second leg', 'Capacity.1', 'Airplane of third leg', 'Capacity.2', 'Priority', 'Best Priority','min_distance', 'Transit Time Minutes']

    # Call the drop_columns method
    data_editor.drop_columns(columns_to_drop)
    data_editor.replace_empty_values()

    Itineraries_df__edited=data_editor.save_summary()

    ''' Use these to cacualte probabilities and my airline demand'''



    analyzer = ItineraryAnalyzer(Itineraries_df__edited)
    analyzer.create_itinerary_id()
    analyzer.count_unique_itineraries()
    Common_itineraries_count_df= analyzer.save_summary()

    

    My_Egyptian_market_betas = {
        'Double Stop in Double Stop':-0.291661,
        'Double Stop in Non Stop':-0.0432075,
        'Non Stop in Non Stop':0.639733,
        'Single Stop in Non Stop':0.038563,
        'Single Stop in Single Stop':0.34343,
        'Low Fare':0.19705,
        'High Fare':-0.19705,
        'Point of Sale Weighted City Presence':-0.043654,
        'second best connection':-0.44516,
        'midnight–6 a.m.':-0.0613285,
        '6–9 a.m.':0.220715,
        '9–noon':0.178997,
        '12–3 p.m.':-0.0123549,
        '3–6 p.m.':-0.097794,
        '6–9 p.m.':-0.0980845,
        '9–midnight':-0.065310,
        'Short Distance':0.137611,
        'Long Distance':-0.137618 }
    My_Egyptian_market_betas_df = pd.DataFrame(My_Egyptian_market_betas, index=[0])
    
    historical_market_betas_df_json = request.session.get('historical_market_betas_df')
    historical_market_betas_df = pd.read_json(StringIO(historical_market_betas_df_json), orient='split')
    historical_market_betas = historical_market_betas_df.to_dict

    itineraries_df_for_demand_calc=propabilities_and_demand(Itineraries_df__edited,historical_market_betas,airline_name_col,origin_col,departure_col,arrival_col,destination_col)
    itineraries_df_for_demand_calc.Itineraries_filter_for_demand()
    itineraries_df_for_demand_calc.Utility_calculation(historical_market_betas_df)
    itineraries_df_for_demand_calc. probability_calculation()
    QSI_df, HHI = itineraries_df_for_demand_calc.calculate_qsi_hhi()
    empty_unconstrained_demand = itineraries_df_for_demand_calc.empty_unconstrained_demand()
    
    empty_unconstrained_demand_df_json = empty_unconstrained_demand.to_json(orient='split')
    request.session['empty_unconstrained_demand_df'] = empty_unconstrained_demand_df_json
    
    Itineraries_df__edited_json = Itineraries_df__edited.to_json(orient='split')
    request.session['Itineraries_df__edited'] = Itineraries_df__edited_json 
    
    
    return redirect('upload_unconstrained_demand_excel')

def upload_unconstrained_demand_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            file_content = excel_file.read()
            file_name = excel_file.name

            read_excel = SyncReadExcel(file_content=file_content, file_name=file_name)
            
            try:
                read_excel.read_data()  # Synchronously read the Excel file
            except ValueError as e:
                # Handle the error (e.g., display an error message to the user)
                return render(request, 'pages/marketshare.html', {'d_excel_form': form, 'd_error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            unconstrained_demand_df_json = read_excel.get_dataframe().to_json(orient='split')
            unconstrained_demand_list = read_excel.get_data_list()

            # Store in session
            request.session['unconstrained_demand_df'] = unconstrained_demand_df_json
            request.session['unconstrained_demand_list'] = unconstrained_demand_list

            return redirect('market_share_results')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/marketshare.html', {'d_excel_form': form})


def market_share_results(request):
    unconstrained_demand_df_json = request.session.get('unconstrained_demand_df')
    unconstrained_demand_df = pd.read_json(StringIO(unconstrained_demand_df_json), orient='split')
    
    i_column_indexes = json.loads(request.session.get('i_column_indexes', '{}'))
    airline_name_col = i_column_indexes.get('Airline')
    origin_col = i_column_indexes.get('origin')
    departure_col = i_column_indexes.get('departure')
    destination_col = i_column_indexes.get('destination')
    arrival_col = i_column_indexes.get('arrival')
    
    Itineraries_df__edited_json = request.session.get('Itineraries_df__edited')
    Itineraries_df__edited = pd.read_json(StringIO(Itineraries_df__edited_json), orient='split')
    
    historical_market_betas_df_json = request.session.get('historical_market_betas_df')
    historical_market_betas_df = pd.read_json(StringIO(historical_market_betas_df_json), orient='split')
    
    
    historical_market_betas = historical_market_betas_df.to_dict
    
    itineraries_df_for_demand_calc=propabilities_and_demand(Itineraries_df__edited,historical_market_betas,airline_name_col,origin_col,departure_col,arrival_col,destination_col)


    itineraries_df_for_demand_calc.Itineraries_filter_for_demand()
    itineraries_df_for_demand_calc.Utility_calculation(historical_market_betas_df)
    itineraries_df_for_demand_calc. probability_calculation()
    QSI_df, HHI = itineraries_df_for_demand_calc.calculate_qsi_hhi()
    itineraries_df_for_demand_calc.demand_calculation(unconstrained_demand_df)
    
    QSI_df_json = QSI_df.to_json(orient='split')
    request.session['QSI_df'] = QSI_df_json
    
    HHI_json = HHI.to_json(orient='split')
    request.session['HHI'] = HHI_json
    
    Itineraries_Demand_DF = itineraries_df_for_demand_calc.get_demand_dataframe()
    
    logger.debug("\n \n  Itineraries_Demand_DF: %s", Itineraries_Demand_DF)
    logger.debug("\n\nItineraries_Demand_DF type: %s", type(Itineraries_Demand_DF))
    
    
    excel_filename = save_MS_dataframes_to_excel(historical_market_betas_df, Itineraries_Demand_DF, QSI_df, HHI)

    print(f'QSI: {QSI_df}')
    print(f'HHI: {HHI}')

    # Transpose the DataFrame and reset the index to make it two columns
    transposed_historical_market_betas_df = historical_market_betas_df.T.reset_index()
    transposed_historical_market_betas_df.columns = ['Regression Coefficient (Beta)', 'Value']
    
    Itineraries_df_json = request.session.get('Itineraries_df')
    Itineraries_df = pd.read_json(StringIO(Itineraries_df_json), orient='split')
    
    i_column_indexes = json.loads(request.session.get('i_column_indexes', '{}'))
    airline_name_col = i_column_indexes.get('Airline')
    origin_col = i_column_indexes.get('origin')
    departure_col = i_column_indexes.get('departure')
    destination_col = i_column_indexes.get('destination')
    arrival_col = i_column_indexes.get('arrival')
    duration_col = i_column_indexes.get('duration')
    type_col = i_column_indexes.get('type')
    itinerary_price_col = i_column_indexes.get('Itinerary Price')
    distance_col = i_column_indexes.get('distance')
    
    Itineraries_df= Itineraries_df.iloc[:, [airline_name_col, origin_col, departure_col,destination_col, arrival_col, duration_col, type_col, itinerary_price_col, distance_col]]
    
    columns_to_keep2 = ['Demand']
    Itineraries_Demand_DF= Itineraries_Demand_DF.filter(columns_to_keep2)
    
    combined_df = pd.concat([Itineraries_df, Itineraries_Demand_DF],axis=1)
    

    return render(request, 'pages/marketshare.html', {
            'historical_market_betas_df': transposed_historical_market_betas_df.to_html(classes=["table", "table-striped"], index=False),
            'Itineraries_Demand': combined_df.to_html(classes=["table", "table-striped"], index=False),
            'HHI': HHI.to_html(classes=["table", "table-striped"], index=False),
            'QSI': QSI_df.to_html(classes=["table", "table-striped"], index=False),
            'excel_file_url': excel_filename
            })
    
# def recommendations(request):
#     # Retrieve data from session
#     QSI_df_json = request.session.get('QSI_df')
#     QSI_df = pd.read_json(StringIO(QSI_df_json), orient='split')
    
#     HHI_json = request.session.get('HHI')
#     HHI_df = pd.read_json(StringIO(HHI_json), orient='split')
    
#     market_info = []
#     for _, row in HHI_df.iterrows():
#         market = f"{row['From']}-{row['To']}"
#         HHI_value = row['HHI']
        
        
#         # Determine competition level based on HHI value
#         if HHI_value < 0.5:
#             competition_level = "Fair - You can enter this market easily (high chance of acquiring high market share)."
#         elif HHI_value < 1:
#             competition_level = "Fierce - The airline has small chance of acquiring market share in this market."
#         else:
#             competition_level = "Monopolistic - It's impossible to compete in this market."
        
#         # Prepare pie chart data
#         # Prepare pie chart data
#         market_QSI = QSI_df[(QSI_df['From'] == row['From']) & (QSI_df['To'] == row['To'])]
#         plt.figure()
#         plt.pie(market_QSI['QSI'], labels=market_QSI['Airline'], autopct='%1.1f%%')
#         plt.title(f"Market Share for {market}")
        
#         # Use BytesIO for binary image data
#         buf = BytesIO()
#         plt.savefig(buf, format='png')
#         plt.close()
#         buf.seek(0)
#         pie_chart = base64.b64encode(buf.read()).decode('utf-8')
        
#         market_info.append({
#             'market': market,
#             'competition_level': competition_level,
#             'pie_chart': pie_chart
#         })
        
#     return render(request, 'pages/marketshare.html', {'markets': market_info})



def recommendations(request):
    
       
    Itineraries_df_json = request.session.get('Itineraries_df')
    Itineraries_df = pd.read_json(StringIO(Itineraries_df_json), orient='split')
    # ****************** Find Itineraries columns **************** #
    i_column_indexes = json.loads(request.session.get('i_column_indexes', '{}'))
    airline_name_col = i_column_indexes.get('Airline')
    origin_col = i_column_indexes.get('origin')
    departure_col = i_column_indexes.get('departure')
    destination_col = i_column_indexes.get('destination')
    arrival_col = i_column_indexes.get('arrival')
    duration_col = i_column_indexes.get('duration')
    type_col = i_column_indexes.get('type')
    First_stop_col = i_column_indexes.get('First Stop')
    First_transit_col = i_column_indexes.get('First Transit Time')
    Second_stop_col = i_column_indexes.get('Second Stop')
    Second_transit_col = i_column_indexes.get('Second Transit Time')
    itinerary_price_col = i_column_indexes.get('Itinerary Price')
    distance_col = i_column_indexes.get('distance')

    
    user_airline_name = 'Egypt Air'
    

    data_editor = DataEditing(historical_Itineraries_df = Itineraries_df,airline_name_col = airline_name_col,type_col = type_col,origin_col = origin_col,destination_col= destination_col
                            ,itinerary_price_col = itinerary_price_col,duration_col=duration_col,distance_col=distance_col,user_airline_name=user_airline_name,First_transit_col=First_transit_col)

    data_editor.read_data()

    data_editor.Sort_airlines_column()

    #Level of Service Data

    data_editor.determine_market_level()
    data_editor.calculate_level_of_service()


    # Calculate fare ratio
    data_editor.calculate_fare_ratio()

    # Apply fare categorization based on market averages
    data_editor.apply_fare_categorization()

    #Point of Sale Weighted City Presence
    data_editor.calculate_total_itineraries_per_market()
    data_editor.calculate_itineraries_per_airline_per_market()
    data_editor.calculate_proportion_per_airline_per_market()

    #Second Best Connection                               ''' activate later'''
    data_editor.calculate_second_shortest_transit_time()

    #Departure Time Categorizing
    departure_col_str = Itineraries_df.columns[departure_col]
    data_editor.apply_time_slots(departure_col_str)


    #Distance Ratio 
    data_editor.calculate_min_distance()
    data_editor.calculate_distance_ratio()
    #Distance Ratio Categorization
    test = data_editor.apply_distance_categorization()


    # Define the list of columns to drop
    columns_to_drop = ['Capacity', 'Airplane of second leg', 'Capacity.1', 'Airplane of third leg', 'Capacity.2', 'Priority', 'Best Priority','min_distance', 'Transit Time Minutes']

    # Call the drop_columns method
    data_editor.drop_columns(columns_to_drop)
    data_editor.replace_empty_values()

    itineraries_df_edited=data_editor.save_summary()
    
    
    
    # Assuming Itineraries_df_edited is your DataFrame and column indices are known for 'From' and 'To'


      # Prepare market data and time slots for visualization
    itineraries_df_edited['Market'] = itineraries_df_edited.iloc[:, origin_col] + " to " + itineraries_df_edited.iloc[:, destination_col]
    time_slots = ['midnight–6 a.m.', '6–9 a.m.', '9–noon', '12–3 p.m.', '3–6 p.m.', '6–9 p.m.', '9–midnight']
    market_time_slot_counts = itineraries_df_edited.groupby('Market')[time_slots].sum()
    itinerary_types_count = itineraries_df_edited.groupby([itineraries_df_edited['Market'], itineraries_df_edited.columns[type_col]]).size().unstack(fill_value=0)

    # Load QSI and HHI data from session
    QSI_df = pd.read_json(StringIO(request.session.get('QSI_df')), orient='split')
    HHI_df = pd.read_json(StringIO(request.session.get('HHI')), orient='split')

    # Prepare data for Google Charts
    google_chart_data = prepare_chart_data(market_time_slot_counts, QSI_df, HHI_df, itinerary_types_count, itineraries_df_edited)
    
    return render(request, 'pages/marketshare.html', {'markets': google_chart_data})


class NumpyEncoder(json.JSONEncoder):
    """ Custom encoder for numpy data types to make them JSON serializable """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)): # This is the trick: to turn an array into a list
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
    
def prepare_chart_data(market_time_slot_counts, QSI_df, HHI_df, itinerary_types_count, itineraries_df_edited):
    google_chart_data = []
    for market, data in market_time_slot_counts.iterrows():
        total_count = data.sum()
        time_slot_data = [['Time Slot', 'Count']] + [(ts, cnt) for ts, cnt in data.items()]
        itinerary_type_data = [['Itinerary Type', 'Count']] + [(item[0], int(item[1])) for item in itinerary_types_count.loc[market].reset_index().values]

        # Calculate counts for Low Fare and High Fare
        fare_counts = itineraries_df_edited[itineraries_df_edited['Market'] == market][['Low Fare', 'High Fare']].sum().astype(int)
        fare_data = [['Fare Type', 'Count'], ['Low Fare', fare_counts['Low Fare']], ['High Fare', fare_counts['High Fare']]]

        market_QSI = QSI_df[(QSI_df['From'] == market.split(' to ')[0]) & (QSI_df['To'] == market.split(' to ')[1])]
        market_share_data = [['Airline', 'QSI']] + [(item['Airline'], float(item['QSI'])) for index, item in market_QSI.iterrows()]

        competition_level, time_slot_comments, type_comments, fare_recommendation = analyze_market(HHI_df, market, time_slot_data, total_count, itinerary_type_data, fare_data)

        google_chart_data.append({
            'market': market,
            'time_slot_data': json.dumps(time_slot_data, cls=NumpyEncoder),
            'itinerary_type_data': json.dumps(itinerary_type_data, cls=NumpyEncoder),
            'market_share_data': json.dumps(market_share_data, cls=NumpyEncoder),
            'fare_data': json.dumps(fare_data, cls=NumpyEncoder),  # Use custom encoder here
            'competition_level': competition_level,
            'time_slot_comments': time_slot_comments,
            'type_comments': type_comments,
            'fare_comments': fare_recommendation
        })
    return google_chart_data

def analyze_market(HHI_df, market, time_slot_data, total_count, itinerary_type_data, fare_data):

    # Attempt to find the relevant HHI data and analyze competition level
    time_slot_comments= 'none'
    row = HHI_df[(HHI_df['From'] == market.split(' to ')[0]) & (HHI_df['To'] == market.split(' to ')[1])].iloc[0]
    HHI_value = row['HHI']
    if HHI_value < 0.5:
        competition_level = f"This is a fair market which has high competetion between airlines, the HHI of this market is {HHI_value} which mean the market concentration is low - You can enter this market easily."
    elif HHI_value < 1:
        competition_level = f"This is a Fierce market, the HHI of this market is {HHI_value} which means the market concentration is intermediate - still there is a chance of acquiring market share"
    else:
        competition_level = f"This is a monopolistic market - Impossible to compete, unless you have an trump card."


    # Analyze time slots for the highest and lowest preference
    time_slot_dict = {ts: cnt for ts, cnt in time_slot_data[1:] if cnt > 0}
    
    if total_count > 0 and time_slot_dict:
        # Handling for markets with one time slot only
        if len(time_slot_dict) == 1:
            only_slot = list(time_slot_dict.keys())[0]
            percentage = (time_slot_dict[only_slot] / total_count) * 100
            time_slot_comments = f"All passengers travel during {only_slot} ({percentage:.1f}%) if your itineraries have other departure times, it will be an advantage and the passenger would has more options ."
        else:
            most_preferred = max(time_slot_dict, key=time_slot_dict.get)
            least_preferred = min(time_slot_dict, key=time_slot_dict.get)
            most_percentage = (time_slot_dict[most_preferred] / total_count) * 100
            least_percentage = (time_slot_dict[least_preferred] / total_count) * 100

            time_slot_comments = (f"Most passengers prefer slot {most_preferred} ({most_percentage:.1f}%) if your itinieraries are near this slot, then you are perfect. "
                                  f"Few passengers go with slot {least_preferred} ({least_percentage:.1f}%) if your itineraries are near this slot, we recommend that you should make more researchs before making final decision.")
            
    # Analyzing the most common itinerary type

    # Convert each item in itinerary_type_data to a tuple (type, count)
    itinerary_type_tuples = [(type_info[0], type_info[1]) for type_info in itinerary_type_data[1:]]
    # Find the most common type using the max function with a key that checks the count
    most_common_type = max(itinerary_type_tuples, key=lambda x: x[1], default=('None', 0))
    type_comments = f"Most airlines make {most_common_type[0]} itineraries in this market, if you increased the level of service, it will me a trump card, but try not to decrase your level of service."
    
    # Fare analysis and recommendations
    low_fare_count = fare_data[1][1]  # Accessing the count of Low Fare directly
    high_fare_count = fare_data[2][1]  # Accessing the count of High Fare directly
    fare_recommendation = ""
    if low_fare_count > high_fare_count:
        fare_recommendation = "This market is distinguished by its low prices so it's recommended not to increase your fare."
    elif high_fare_count > low_fare_count:
        fare_recommendation = "This market has high prices, so if you lower your prices, it will be a strong advantage for you."
    else:
        fare_recommendation = "Entering with high fare or low fare will not be a problem it's a winning situation in both cases, but for sure with low fares, you will gurantee more passengers ."

    return competition_level, time_slot_comments, type_comments, fare_recommendation

    
    

def preview_unconstrained_demand(request):
    """View to handle AJAX request for previewing the flights sample on a webpage."""
    empty_unconstrained_demand_df_json = request.session.get('empty_unconstrained_demand_df')
    empty_unconstrained_demand_df = pd.read_json(StringIO(empty_unconstrained_demand_df_json), orient='split')
    html_table = empty_unconstrained_demand_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})
    
def download_unconstrained_demand_excel(request):
    # Define a DataFrame with the necessary columns
    empty_unconstrained_demand_df_json = request.session.get('empty_unconstrained_demand_df')
    empty_unconstrained_demand_df = pd.read_json(StringIO(empty_unconstrained_demand_df_json), orient='split')
    
    # Define the Excel response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Unconstrained_Demand_Excel.xlsx"'

    # Write the empty DataFrame to the Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        empty_unconstrained_demand_df.to_excel(writer, index=False)

    return response
        
def save_MS_dataframes_to_excel(historical_market_betas_df, Itineraries_Demand, QSI_df, HHI):
    filename = 'Market_Share_Results.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        historical_market_betas_df.to_excel(writer, sheet_name='Regression Coefficients (Betas)', index=False)
        Itineraries_Demand.to_excel(writer, sheet_name='Itineraries Demand', index=False)
        HHI.to_excel(writer, sheet_name='HHI', index=False)
        QSI_df.to_excel(writer, sheet_name='Quality Service Index (QSI)', index=False)
        
    
    return filename

def download_MS_results_excel(request):
    filename = 'Market_Share_Results.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)

    try:
        if os.path.exists(filepath):
            # Open the file without a context manager to manually control when it is closed
            excel_file = open(filepath, 'rb')
            response = FileResponse(excel_file, as_attachment=True, filename=filename)

            # Add cleanup for the file on the response close
            response.file_to_close = excel_file

            return response
        else:
            return HttpResponseNotFound('The requested Excel file was not found on the server.')
    except Exception as e:
        # Log the error for debugging
        print(e)
        return HttpResponseServerError('A server error occurred. Please contact the administrator.')


        
