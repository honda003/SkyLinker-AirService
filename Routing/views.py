from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import FpdForm, ExcelUploadForm, create_column_index_form, TurnAroundTimeForm, create_hub_selection_form, FpdForm, CycleAndAircraftForm
from .utils import MaxFpd, ColumnIndex, SyncReadExcel, ClockToMinutes, UniqueStations, CombinationsGenerator, FlightPerDay, FpdSchedule,  process_combos, optimization
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
import traceback
import os
from django.http import FileResponse, HttpResponseNotFound, HttpResponse, HttpResponseServerError
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@login_required
def upload_excel(request):
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
                return render(request, 'pages/routing.html', {'excel_form': form, 'error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            flights_df_json = read_excel.get_dataframe().to_json(orient='split')
            flights_list = read_excel.get_data_list()

            # Store in session
            request.session['flights_df'] = flights_df_json
            request.session['flights_list'] = flights_list

            return redirect('process_columns')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/routing.html', {'excel_form': form})

def process_columns(request):
    if 'flights_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_excel')

    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    column_index = ColumnIndex(flights_df)

    if request.method == 'POST' and 'missing_columns' in request.session:
        # User is submitting indexes for missing columns
        form = create_column_index_form(request.session['missing_columns'])(request.POST)
        if form.is_valid():
            provided_indexes = {col: form.cleaned_data[f"{col}_index"] - 1 for col in request.session['missing_columns']}
            
            error_messages = []
            for col, idx in provided_indexes.items():
                if idx >= len(flights_df.columns) or idx < 0:
                    error_messages.append(f"Index for {col} is out of the valid range (1 - {len(flights_df.columns)}).")
                    continue

                is_valid, message = column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/routing.html', {'column_form': form, 'error_messages': error_messages})
            
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**column_index.columns, **provided_indexes}
            # Save complete column indexes in session
            request.session['column_indexes'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            # Call process_time_and_stations now that we have all column indexes
            process_time_and_stations(request)
            # Proceed to turn-around and hub selection
            return redirect('turn_around_and_hub_selection')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/routing.html', {'column_form': form})
    else:
        # Either we have all columns from the start or we need to ask for them
        if column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = column_index.missing_columns
            form = create_column_index_form(column_index.missing_columns)()
            return render(request, 'pages/routing.html', {'column_form': form})
        else:
            # No missing columns, use found columns
            request.session['column_indexes'] = json.dumps(column_index.columns)
            # Call process_time_and_stations with the columns found by ColumnIndex
            process_time_and_stations(request)
            # Proceed to turn-around and hub selection
            return redirect('turn_around_and_hub_selection')

def process_time_and_stations(request):
    flights_df_json = request.session.get('flights_df', '{}')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    column_indexes = json.loads(request.session.get('column_indexes', '{}'))
    
    # Debugging log
    # logger.debug("flights_df: %s", flights_df)
    # logger.debug("column_indexes: %s", column_indexes)
    
    
    # Assuming column_indexes are integers and refer to DataFrame column positions
    flight_number_index = column_indexes.get('flight number')
    origin_index = column_indexes.get('origin')
    departure_index = column_indexes.get('departure')
    destination_index = column_indexes.get('destination')
    arrival_index = column_indexes.get('arrival')
    flight_duration_index = column_indexes.get('flight duration')
    
    
    # Debugging log
    # logger.debug("departure_index: %s", departure_index)
    # logger.debug("arrival_index: %s", arrival_index)
    # logger.debug("origin_index: %s", origin_index)
    
    clock_to_minutes = ClockToMinutes(flights_df, departure_index, arrival_index)
    departure_minutes = clock_to_minutes.get_departure_minutes()
    arrival_minutes = clock_to_minutes.get_arrival_minutes()
    unique_stations = UniqueStations(flights_df, origin_index).get_stations()
    
    request.session['departure_minutes'] = json.dumps(departure_minutes)
    request.session['arrival_minutes'] = json.dumps(arrival_minutes)
    request.session['unique_stations'] = json.dumps(unique_stations)
    
    # Debugging log
    # logger.debug("departure_minutes: %s", departure_minutes)
    # logger.debug("arrival_index: %s", arrival_minutes)
    # logger.debug("unique_stations: %s", unique_stations)
    

def turn_around_and_hub_selection(request):
    unique_stations_json = request.session.get('unique_stations', "[]")
    unique_stations = json.loads(unique_stations_json)

    if request.method == 'POST':
        turn_around_form = TurnAroundTimeForm(request.POST)
        hub_selection_form = create_hub_selection_form(unique_stations)(request.POST)
        if turn_around_form.is_valid() and hub_selection_form.is_valid():
            
            # Extract turn around time from the form
            turn_around_time = turn_around_form.cleaned_data['turn_around_time']
            # Extract selected hubs from the form
            selected_hubs = hub_selection_form.cleaned_data['hubs']
            
            # Save the extracted values into the session
            request.session['turn_around_time'] = turn_around_time
            request.session['selected_hubs'] = selected_hubs
            return redirect('fpd_decision')  # Adjust 'next_step' as needed
    else:
        turn_around_form = TurnAroundTimeForm()
        hub_selection_form = create_hub_selection_form(unique_stations)()

    return render(request, 'pages/routing.html', {
        'turn_around_form': turn_around_form,
        'hub_selection_form': hub_selection_form
    })
    
    
def fpd_decision(request):
    if 'unique_stations' not in request.session:
        return redirect('turn_around_and_hub_selection')

    unique_stations = json.loads(request.session.get('unique_stations', "[]"))
    turn_around_form = TurnAroundTimeForm()
    hub_selection_form = create_hub_selection_form(unique_stations)()

    flights_df_json = request.session['flights_df']
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    departure_minutes = json.loads(request.session['departure_minutes'])
    arrival_minutes = json.loads(request.session['arrival_minutes'])
    TAT = request.session.get('tat', 45)  # Assuming TAT is stored in session

    max_fpd_instance = MaxFpd(flights_df, departure_minutes, arrival_minutes, TAT)
    max_fpd = max_fpd_instance.get_max_fpd()

    if request.method == 'POST':
        fpd_form = FpdForm(request.POST, initial={'max_fpd': max_fpd})
        if fpd_form.is_valid():
            use_max_fpd = fpd_form.cleaned_data['use_max_fpd']
            specified_fpd = fpd_form.cleaned_data.get('specified_fpd', max_fpd)  # Default to max_fpd if unspecified

            request.session['fpd'] = max_fpd if use_max_fpd else specified_fpd
            return redirect('cycle_and_aircraft_input')  # Adjust 'next_step' as needed
    else:
        fpd_form = FpdForm(initial={'max_fpd': max_fpd})

    return render(request, 'pages/routing.html', {
        'turn_around_form': turn_around_form,
        'hub_selection_form': hub_selection_form,
        'fpd_form': fpd_form,
        'max_fpd': max_fpd  # Passing max_fpd to template for informational purposes
    })
    
def cycle_and_aircraft_input(request):
    if request.method == 'POST':
        form = CycleAndAircraftForm(request.POST)
        if form.is_valid():
            days_in_cycle = form.cleaned_data['days_in_cycle']
            number_of_aircrafts = form.cleaned_data['number_of_aircrafts']

            request.session['days_in_cycle'] = days_in_cycle
            request.session['number_of_aircrafts'] = number_of_aircrafts

            user_decided_fpd = request.session.get('fpd')
            combinations_generator = CombinationsGenerator(user_decided_fpd, days_in_cycle)
            combos = combinations_generator.get_combos()

            request.session['combos'] = json.dumps(combos)

            find_combos(request)
            optimization_step(request)
            return redirect('optimization_step')  # Redirect as needed
    else:
        form = CycleAndAircraftForm()

    return render(request, 'pages/routing.html', {'cycle_and_aircraft_form': form})

def find_combos(request):
    flights_df_json = request.session['flights_df']
    flights_df_list = pd.read_json(StringIO(flights_df_json), orient='split').values.tolist()
    departure_minutes = json.loads(request.session['departure_minutes'])
    arrival_minutes = json.loads(request.session['arrival_minutes'])
    TAT = request.session.get('turn_around_time', 45)
    column_indexes = json.loads(request.session['column_indexes'])
    unique_stations = json.loads(request.session['unique_stations'])
    hubs = request.session['selected_hubs']
    days_in_cycle = request.session['days_in_cycle']
    fpd = request.session['fpd']
    
    origin_col_index = column_indexes['origin']
    destination_col_index = column_indexes['destination']
    
    combos = json.loads(request.session['combos'])
    
    logger.debug(f"flights_df_json: {flights_df_json}")
    logger.debug(f"flights_df_list: {flights_df_list}")
    logger.debug(f"departure_minutes: {departure_minutes}")
    logger.debug(f"arrival_minutes: {arrival_minutes}")
    logger.debug(f"TAT: {TAT}")
    logger.debug(f"unique_stations: {unique_stations}")
    logger.debug(f"hubs: {hubs}")
    logger.debug(f"days_in_cycle: {days_in_cycle}")
    logger.debug(f"fpd: {fpd}")
    logger.debug(f"origin_col_index: {origin_col_index}")
    logger.debug(f"destination_col_index : {destination_col_index }")
    logger.debug(f"combos: {combos}")
    

    valid_combos, all_options_lists, total, m, data = process_combos(
        combos, flights_df_list, departure_minutes, arrival_minutes, TAT, 
        origin_col_index, destination_col_index, hubs, days_in_cycle, fpd
    )
    
    # Debugging log
    # logger.debug(f"Valid combos: {valid_combos}")
    # logger.debug(f"data: {data}")

    #Store or process the output as needed
    # Example: Store the result in the session or pass it to the template
    request.session['valid_combos'] = valid_combos
    request.session['all_options_lists'] = all_options_lists
    request.session['total'] = total
    request.session['m'] = m
    request.session['data'] = json.dumps(data)
    
    
    
def optimization_step(request):
    # Directly access the session data without assuming it's a JSON string.
    # The session data should be directly usable if it was stored as a Python list or dict.
    all_options_lists = request.session.get('all_options_lists', [])
    m = request.session.get('m', [])
    
    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    TAT_minutes = request.session.get('turn_around_time', [])
    data = json.loads(request.session.get('data', '[]'))
    valid_combos = request.session.get('valid_combos', [])
    number_of_aircrafts = int(request.session.get('number_of_aircrafts'))
    
    column_indexes = json.loads(request.session['column_indexes'])
    
    flight_number_index = column_indexes.get('flight number')
    origin_index = column_indexes.get('origin')
    departure_index = column_indexes.get('departure')
    destination_index = column_indexes.get('destination')
    arrival_index = column_indexes.get('arrival')
    flight_duration_index = column_indexes.get('flight duration')

    # Since data was adjusted to be stored directly in its Python format,
    # there's no need to load it from JSON strings here.

    # Call the optimization function with the prepared data.
    # Ensure the optimization function can handle the data in its current format.
    
    # Debugging log
    #logger.debug(f"data: {data}")
    
    objective_value, Output_df, routing_result, is_optimized, message = optimization(flights_df, TAT_minutes, all_options_lists, m, data, valid_combos, number_of_aircrafts, flight_number_index, origin_index, departure_index, arrival_index, destination_index, flight_duration_index)
    
    if not is_optimized:
        request.session['infeasibility_result'] = routing_result
        infeasibility_result = request.session.get('infeasibility_result', [])
        # Handle the case where no feasible solution is found or the solver failed
        context = {
            'error_message': message,
            'infeasibility_result': infeasibility_result,
            # You may want to include forms or other context data needed to render 'routing.html'
        }
        return render(request, 'pages/routing.html', context)
        
    else:
        # Save optimization results into the session.
        # If Output_df is a pandas DataFrame, convert it to a JSON string before storing.
        request.session['objective_value'] = objective_value
        request.session['optimized_schedule_html'] = Output_df.to_html(classes=["table", "table-striped"], index=False)
        request.session['routing_result'] = routing_result

        # Debugging log
        #logger.debug(f"Optimized Objective Value: {objective_value}")
        #logger.debug(f"Output_df: {Output_df}")
        
        excel_filename = save_R_dataframes_to_excel(Output_df)
        
        return render(request, 'pages/routing.html', {
            'objective_value': objective_value,
            'optimized_schedule_html': Output_df.to_html(classes=["table", "table-striped"], index=False),
            'routing_result': routing_result,
            'excel_file_url': excel_filename
            })
        
flights_sample_df = pd.DataFrame({
    'Flight Number': [123, 124],
    'Origin': ['ABC', 'EFG'],
    'Departure': ['10:00', '14:00'],
    'Destination': ['EFG', 'XYZ'],
    'Arrival': ['12:00', '16:00'],
    'Distance': [500, 1000],
    'Duration': [2.5, 3]
})

def preview_R_flights_sample(request):
    """View to handle AJAX request for previewing the flights sample on a webpage."""
    html_table = flights_sample_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})

def download_R_flights_sample_excel(request):
    """View to handle downloading the flights sample as an Excel file."""
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Flight_Data_Excel_Sample.xlsx"'
    
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        flights_sample_df.to_excel(writer, index=False)
    
    return response


def save_R_dataframes_to_excel(Output_df):
    filename = 'Routing_Results.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        Output_df.to_excel(writer, sheet_name='Routing Results', index=False)
    
    return filename

def download_R_results_excel(request):
    filename = 'Routing_Results.xlsx'
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