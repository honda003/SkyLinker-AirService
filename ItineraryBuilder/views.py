from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ExcelUploadForm, create_column_index_form, TurnAroundTimeForm, ConnectionTimeForm, DistanceConstraintForm
from .utils import ColumnIndex, SyncReadExcel, ClockToMinutes, UniqueStations, ItinSSBuilder, ItinDSBuilder, ColumnIndex_Airport, create_distance_dataframe, Flights_Distance_Duration
import pandas as pd
import json
from io import StringIO
import logging
from datetime import datetime,timedelta
from django.conf import settings
import traceback
import os
from django.http import FileResponse, HttpResponseNotFound, HttpResponse, HttpResponseServerError
from django.http import JsonResponse

logger = logging.getLogger(__name__)

@login_required
def upload_excel_Itin(request):
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
                return render(request, 'pages/itinerarybuilder.html', {'excel_form': form, 'error_message': str(e)})

            
            # Convert DataFrame to JSON for session storage
            flights_df_json = read_excel.get_dataframe().to_json(orient='split')
            flights_list = read_excel.get_data_list()

             # Store in session
            request.session['flights_df'] = flights_df_json
            request.session['flights_list'] = flights_list
            

            return redirect('process_columns_Itin')
    else:
        form = ExcelUploadForm()
    return render(request, 'pages/itinerarybuilder.html', {'excel_form': form}) ############################# CARE

def process_columns_Itin(request):
    if 'flights_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_excel_Itin')

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
                return render(request, 'pages/itinerarybuilder.html', {'column_form': form, 'error_messages': error_messages})
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**column_index.columns, **provided_indexes}
            
            # Save complete column indexes in session
            request.session['column_indexes'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            # Call process_time_and_stations now that we have all column indexes
            process_time_and_stations_Itin(request)
            # Proceed to turn-around and hub selection
            return redirect('upload_airport_coordinates')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/itinerarybuilder.html', {'column_form': form}) ################################ CARE
    else:
        # Either we have all columns from the start or we need to ask for them
        if column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = column_index.missing_columns
            form = create_column_index_form(column_index.missing_columns)()
            return render(request, 'pages/itinerarybuilder.html', {'column_form': form})  ################################ CARE
        else:
            # No missing columns, use found columns
            request.session['column_indexes'] = json.dumps(column_index.columns)
            # Call process_time_and_stations with the columns found by ColumnIndex
            process_time_and_stations_Itin(request)
            # Proceed to turn-around and hub selection
            return redirect('upload_airport_coordinates')
        
def upload_airport_coordinates(request):
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
                return render(request, 'pages/itinerarybuilder.html', {'airport_excel_form': form, 'error_message': str(e)})

            
            # Convert DataFrame to JSON for session storage
            airport_df_json = read_excel.get_dataframe().to_json(orient='split')
            airport_list = read_excel.get_data_list()

             # Store in session
            request.session['airport_df'] = airport_df_json
            request.session['airport_list'] = airport_list
            

            return redirect('process_columns_airport')
    else:
        form = ExcelUploadForm()
    return render(request, 'pages/itinerarybuilder.html', {'airport_excel_form': form}) ############################# CARE

def process_columns_airport(request):
    if 'airport_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_airport_coordinates')

    # Load DataFrame from session
    airport_df_json = request.session.get('airport_df')
    airport_df = pd.read_json(StringIO(airport_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    column_index = ColumnIndex_Airport(airport_df)

    if request.method == 'POST' and 'missing_columns' in request.session:
        # User is submitting indexes for missing columns
        form = create_column_index_form(request.session['missing_columns'])(request.POST)
        if form.is_valid():
            provided_indexes = {col: form.cleaned_data[f"{col}_index"] - 1 for col in request.session['missing_columns']}
            
            error_messages = []
            for col, idx in provided_indexes.items():
                if idx >= len(airport_df.columns) or idx < 0:
                    error_messages.append(f"Index for {col} is out of the valid range (1 - {len(airport_df.columns)}).")
                    continue

                is_valid, message = column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/itinerarybuilder.html', {'airport_column_form': form, 'error_messages': error_messages})
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**column_index.columns, **provided_indexes}
            
            # Save complete column indexes in session
            request.session['column_indexes_airport'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            # Call process_time_and_stations now that we have all column indexes
            process_time_and_stations_Itin(request)
            # Proceed to turn-around and hub selection
            return redirect('turn_around_and_connection_Itin')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/itinerarybuilder.html', {'airport_column_form': form}) ################################ CARE
    else:
        # Either we have all columns from the start or we need to ask for them
        if column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = column_index.missing_columns
            form = create_column_index_form(column_index.missing_columns)()
            return render(request, 'pages/itinerarybuilder.html', {'airport_column_form': form})  ################################ CARE
        else:
            # No missing columns, use found columns
            request.session['column_indexes_airport'] = json.dumps(column_index.columns)
            # Call process_time_and_stations with the columns found by ColumnIndex
            process_time_and_stations_Itin(request)
            # Proceed to turn-around and hub selection
            return redirect('turn_around_and_connection_Itin')

def process_time_and_stations_Itin(request):
    flights_df_json = request.session.get('flights_df', '{}')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    column_indexes = json.loads(request.session.get('column_indexes', '{}'))
    
    #print("\n\n column_indexes: %s", column_indexes)
    
    # Assuming column_indexes are integers and refer to DataFrame column positions
    departure_index = column_indexes.get('departure')
    arrival_index = column_indexes.get('arrival')
    origin_index = column_indexes.get('origin')
    
    
    clock_to_minutes = ClockToMinutes(flights_df, departure_index, arrival_index)
    departure_minutes = clock_to_minutes.get_departure_minutes()
    arrival_minutes = clock_to_minutes.get_arrival_minutes()
    unique_stations = UniqueStations(flights_df, origin_index).get_stations()
    
    request.session['departure_minutes'] = json.dumps(departure_minutes)
    request.session['arrival_minutes'] = json.dumps(arrival_minutes)
    request.session['unique_stations'] = json.dumps(unique_stations)        

def turn_around_and_connection_Itin(request):
    if request.method == 'POST':
        turn_around_form = TurnAroundTimeForm(request.POST)
        connection_time_form = ConnectionTimeForm(request.POST)
        distance_ratio_form = DistanceConstraintForm(request.POST)
        if turn_around_form.is_valid() and connection_time_form.is_valid() and distance_ratio_form.is_valid():
            turn_around_time = turn_around_form.cleaned_data['turn_around_time']
            connection_time = connection_time_form.cleaned_data['connection_time']
            distance_ratio = distance_ratio_form.cleaned_data['distance_ratio']

            request.session['turn_around_time'] = turn_around_time
            request.session['connection_time'] = connection_time
            request.session['distance_ratio'] = distance_ratio

            flights_df_json = request.session.get('flights_df')
            flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
            
            column_indexes = json.loads(request.session.get('column_indexes', '{}'))
            flight_no_index = column_indexes.get('flight number')
            departure_index = column_indexes.get('departure')
            arrival_index = column_indexes.get('arrival')
            origin_index = column_indexes.get('origin')
            destination_index = column_indexes.get('destination')
            
            column_indexes_airport = json.loads(request.session.get('column_indexes_airport', '{}'))
            airport_index = column_indexes_airport.get('airport')
            longitude_index = column_indexes_airport.get('longitude')
            latitude_index = column_indexes_airport.get('latitude')
            
            airport_df_json = request.session.get('airport_df', '{}')
            airport_df = pd.read_json(StringIO(airport_df_json), orient='split')
            
            airports_distances_df = create_distance_dataframe(airport_df, airport_index, latitude_index, longitude_index)

            dep_arriv = ClockToMinutes(flights_df, departure_index, arrival_index)
            singlestop = ItinSSBuilder(flights_df, dep_arriv.get_departure_minutes(), dep_arriv.get_arrival_minutes(), flight_no_index, origin_index, departure_index, destination_index, arrival_index, turn_around_time, connection_time, airports_distances_df, distance_ratio)
            
            singlestop.generate_itineraries()
            ss_itin_df = singlestop.get_ss_itin()
            
            doublestop = ItinDSBuilder(flights_df, ss_itin_df, dep_arriv.get_departure_minutes(), dep_arriv.get_arrival_minutes(), flight_no_index, origin_index, departure_index, destination_index, arrival_index, turn_around_time, connection_time, airports_distances_df, distance_ratio)
            
            doublestop.generate_itineraries()
            ds_itin_df = doublestop.get_ds_itin()
            
            new_flights_df_instance = Flights_Distance_Duration(flights_df, dep_arriv.get_departure_minutes(), dep_arriv.get_arrival_minutes(), flight_no_index, origin_index, departure_index, destination_index, arrival_index, turn_around_time, connection_time, airports_distances_df, distance_ratio)
            
            new_flights_df = new_flights_df_instance.get_flights_distance_duration()
            # print(f'\n\n ds_itin_df: {ds_itin_df}\n\n')
            
            req_format_columns = [
                'Airline', 'Itinerary_Number', 'Flights', 'Itinerary_Origin', 'Itinerary_Departure_Time', 'Itinerary_Destination', 'Itinerary_Arrival_Time', 'Itinerary_Duration',
                'Itinerary_Distance', 'Itinerary_Type', 'Flight1_Origin', 'Flight1_Departure_Time', 'Flight1_Destination', 'Flight1_Arrival_Time',  'Flight1_Duration', 
                'Flight2_Origin', 'Flight2_Departure_Time', 'Flight2_Destination', 'Flight2_Arrival_Time',  'Flight2_Duration',
                'Flight3_Origin', 'Flight3_Departure_Time', 'Flight3_Destination', 'Flight3_Arrival_Time',  'Flight3_Duration','Itinerary_Price'
            ]
            req_format = pd.DataFrame(columns=req_format_columns)
            
            counter = 1
            df_index = 0
            
            # print(flights_df)

            # Use iterrows to iterate over flights_df
            
            for idx, flight in flights_df.iterrows():
                # Set values for the new row using loc to correctly reference and create the row if it does not exist
        
                # departure_time_1 = datetime.strptime(flight.iloc[departure_index], '%H:%M:%S')
                # arrival_time_1 = datetime.strptime(flight.iloc[arrival_index], '%H:%M:%S')

                # # Calculate the transit time difference
                # if departure_time_1 < arrival_time_1:
                #     delta_1 = departure_time_1 - arrival_time_1
                #     hours_1 = delta_1.seconds // 3600
                #     minutes_1 = (delta_1.seconds % 3600) // 60
                #     if minutes_1 > 0:
                #         duration_1 = f"{hours_1}h {minutes_1}"
                #     else:
                #         duration_1 = f"{hours_1}h"
                # else:
                #     duration_1 = "0h"  # If departure is not after arrival, set transit time to "0h"   
                
                departure_time = datetime.strptime(flight.iloc[departure_index], '%H:%M:%S')
                arrival_time = datetime.strptime(flight.iloc[arrival_index], '%H:%M:%S')

                if arrival_time < departure_time:
                    arrival_time += timedelta(days=1)

                duration = arrival_time - departure_time
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                duration_str = f"{hours}h {minutes}" if minutes > 0 else f"{hours}h"

                
                
                req_format.loc[df_index, 'Airline'] = None
                req_format.loc[df_index, 'Itinerary_Number'] = counter
                req_format.loc[df_index, 'Flights'] = f'{flight.iloc[flight_no_index]}'
                req_format.loc[df_index, 'Itinerary_Origin'] = flight.iloc[origin_index]
                req_format.loc[df_index, 'Itinerary_Departure_Time'] = flight.iloc[departure_index]
                req_format.loc[df_index, 'Itinerary_Destination'] = flight.iloc[destination_index]
                req_format.loc[df_index, 'Itinerary_Arrival_Time'] = flight.iloc[arrival_index]
                req_format.loc[df_index, 'Itinerary_Duration'] = duration_str  # Assuming duration is calculated or added later
                req_format.loc[df_index, 'Itinerary_Type'] = 'Non Stop'
                req_format.loc[df_index, 'Itinerary_Price'] = None
                req_format.loc[df_index, 'Itinerary_Distance'] = flight['Distance']
                
                req_format.loc[df_index, 'Flight1_Origin'] = flight.iloc[origin_index]
                req_format.loc[df_index, 'Flight1_Departure_Time'] = flight.iloc[departure_index]
                req_format.loc[df_index, 'Flight1_Destination'] = flight.iloc[destination_index]
                req_format.loc[df_index, 'Flight1_Arrival_Time'] = flight.iloc[arrival_index]
                req_format.loc[df_index, 'Flight1_Duration'] = duration_str
                
                req_format.loc[df_index, 'Flight2_Origin'] = None
                req_format.loc[df_index, 'Flight2_Departure_Time'] = None
                req_format.loc[df_index, 'Flight2_Destination'] = None
                req_format.loc[df_index, 'Flight2_Arrival_Time'] = None
                req_format.loc[df_index, 'Flight2_Duration'] = None
                
                req_format.loc[df_index, 'Flight3_Origin'] = None
                req_format.loc[df_index, 'Flight3_Departure_Time'] = None
                req_format.loc[df_index, 'Flight3_Destination'] = None
                req_format.loc[df_index, 'Flight3_Arrival_Time'] = None
                req_format.loc[df_index, 'Flight3_Duration'] = None

                # Increment counter after each row is added
                counter += 1
                df_index += 1
                
            for idx, flight in ss_itin_df.iterrows():
                # # Set values for the new row using loc to correctly reference and create the row if it does not exist
                
    
                
                departure_time_1 = datetime.strptime(flight['Departure_1'], '%H:%M:%S')
                
                arrival_time_1 = datetime.strptime(flight['Arrival_1'], '%H:%M:%S')
                if arrival_time_1 < departure_time_1:
                    arrival_time_1 += timedelta(days=1)

                departure_time_2 = datetime.strptime(flight['Departure_2'], '%H:%M:%S')
                arrival_time_2 = datetime.strptime(flight['Arrival_2'], '%H:%M:%S')
                if arrival_time_2 < departure_time_2:
                    arrival_time_2 += timedelta(days=1)

                duration_1 = arrival_time_1 - departure_time_1
                hours_1 = duration_1.seconds // 3600
                minutes_1 = (duration_1.seconds % 3600) // 60
                duration_1_str = f"{hours_1}h {minutes_1}" if minutes_1 > 0 else f"{hours_1}h"

                duration_2 = arrival_time_2 - departure_time_2
                hours_2 = duration_2.seconds // 3600
                minutes_2 = (duration_2.seconds % 3600) // 60
                duration_2_str = f"{hours_2}h {minutes_2}" if minutes_2 > 0 else f"{hours_2}h"
                
                Transit_1 = departure_time_2 - arrival_time_1
                
                total_duration = duration_1 + duration_2 + Transit_1
                hours_t = total_duration.seconds // 3600
                minutes_t = (total_duration.seconds % 3600) // 60
                total_duration_str = f"{hours_t}h {minutes_t}" if minutes_t > 0 else f"{hours_t}h"

                
            
                req_format.loc[df_index, 'Airline'] = None
                req_format.loc[df_index, 'Itinerary_Number'] = counter
                req_format.loc[df_index, 'Flights'] = f'{flight['Flight_Number_1']}, {flight['Flight_Number_2']}'
                req_format.loc[df_index, 'Itinerary_Origin'] = flight['Origin_1']
                req_format.loc[df_index, 'Itinerary_Departure_Time'] = flight['Departure_1']
                req_format.loc[df_index, 'Itinerary_Destination'] = flight['Destination_2']
                req_format.loc[df_index, 'Itinerary_Arrival_Time'] = flight['Arrival_2']
                req_format.loc[df_index, 'Itinerary_Duration'] = total_duration_str
                req_format.loc[df_index, 'Itinerary_Type'] = 'Single Stop'
                req_format.loc[df_index, 'Itinerary_Price'] = None
                req_format.loc[df_index, 'Itinerary_Distance'] = flight['Distance']
                
                req_format.loc[df_index, 'Flight1_Origin'] = flight['Origin_1']
                req_format.loc[df_index, 'Flight1_Departure_Time'] = flight['Departure_1']
                req_format.loc[df_index, 'Flight1_Destination'] = flight['Destination_1']
                req_format.loc[df_index, 'Flight1_Arrival_Time'] = flight['Arrival_1']
                req_format.loc[df_index, 'Flight1_Duration'] = duration_1_str
                
                req_format.loc[df_index, 'Flight2_Origin'] = flight['Origin_2']
                req_format.loc[df_index, 'Flight2_Departure_Time'] = flight['Departure_2']
                req_format.loc[df_index, 'Flight2_Destination'] = flight['Destination_2']
                req_format.loc[df_index, 'Flight2_Arrival_Time'] = flight['Arrival_2']
                req_format.loc[df_index, 'Flight2_Duration'] = duration_2_str
                
                req_format.loc[df_index, 'Flight3_Origin'] = None
                req_format.loc[df_index, 'Flight3_Departure_Time'] = None
                req_format.loc[df_index, 'Flight3_Destination'] = None
                req_format.loc[df_index, 'Flight3_Arrival_Time'] = None
                req_format.loc[df_index, 'Flight3_Duration'] = None

                # Increment counter after each row is added
                counter += 1
                df_index += 1
                             
            for idx, flight in ds_itin_df.iterrows():
                # # Set values for the new row using loc to correctly reference and create the row if it does not exist
                
                
                departure_time_1 = datetime.strptime(flight['Departure_1'], '%H:%M:%S')
                arrival_time_1 = datetime.strptime(flight['Arrival_1'], '%H:%M:%S')
                
                if arrival_time_1 < departure_time_1:
                    arrival_time_1 += timedelta(days=1)

                departure_time_2 = datetime.strptime(flight['Departure_2'], '%H:%M:%S')
                arrival_time_2 = datetime.strptime(flight['Arrival_2'], '%H:%M:%S')
                
                if arrival_time_2 < departure_time_2:
                    arrival_time_2 += timedelta(days=1)

                departure_time_3 = datetime.strptime(flight['Departure_3'], '%H:%M:%S')
                arrival_time_3 = datetime.strptime(flight['Arrival_3'], '%H:%M:%S')
                
                if arrival_time_3 < departure_time_3:
                    arrival_time_3 += timedelta(days=1)

                duration_1 = arrival_time_1 - departure_time_1
                hours_1 = duration_1.seconds // 3600
                minutes_1 = (duration_1.seconds % 3600) // 60
                duration_1_str = f"{hours_1}h {minutes_1}" if minutes_1 > 0 else f"{hours_1}h"

                duration_2 = arrival_time_2 - departure_time_2
                hours_2 = duration_2.seconds // 3600
                minutes_2 = (duration_2.seconds % 3600) // 60
                duration_2_str = f"{hours_2}h {minutes_2}" if minutes_2 > 0 else f"{hours_2}h"

                duration_3 = arrival_time_3 - departure_time_3
                hours_3 = duration_3.seconds // 3600
                minutes_3 = (duration_3.seconds % 3600) // 60
                duration_3_str = f"{hours_3}h {minutes_3}" if minutes_3 > 0 else f"{hours_3}h"

                Transit_1 = departure_time_2 - arrival_time_1
                
                Transit_2 = departure_time_3 - arrival_time_2
                
                total_duration = duration_1 + duration_2 + duration_3 + Transit_1 + Transit_2
                hours_t = total_duration.seconds // 3600
                minutes_t = (total_duration.seconds % 3600) // 60
                total_duration_str = f"{hours_t}h {minutes_t}" if minutes_t > 0 else f"{hours_t}h"
                
                

                req_format.loc[df_index, 'Itinerary_Duration'] = total_duration_str
            
                req_format.loc[df_index, 'Airline'] = None
                req_format.loc[df_index, 'Itinerary_Number'] = counter
                req_format.loc[df_index, 'Flights'] = f'{flight['Flight_Number_1']}, {flight['Flight_Number_2']}, {flight['Flight_Number_3']}'
                req_format.loc[df_index, 'Itinerary_Origin'] = flight['Origin_1']
                req_format.loc[df_index, 'Itinerary_Departure_Time'] = flight['Departure_1']
                req_format.loc[df_index, 'Itinerary_Destination'] = flight['Destination_3']
                req_format.loc[df_index, 'Itinerary_Arrival_Time'] = flight['Arrival_3']
                req_format.loc[df_index, 'Itinerary_Duration'] = total_duration_str
                req_format.loc[df_index, 'Itinerary_Type'] = 'Double Stop'
                req_format.loc[df_index, 'Itinerary_Price'] = None
                req_format.loc[df_index, 'Itinerary_Distance'] = flight['Distance']
                
                req_format.loc[df_index, 'Flight1_Origin'] = flight['Origin_1']
                req_format.loc[df_index, 'Flight1_Departure_Time'] = flight['Departure_1']
                req_format.loc[df_index, 'Flight1_Destination'] = flight['Destination_1']
                req_format.loc[df_index, 'Flight1_Arrival_Time'] = flight['Arrival_1']
                req_format.loc[df_index, 'Flight1_Duration'] = duration_1_str
                
                req_format.loc[df_index, 'Flight2_Origin'] = flight['Origin_2']
                req_format.loc[df_index, 'Flight2_Departure_Time'] = flight['Departure_2']
                req_format.loc[df_index, 'Flight2_Destination'] = flight['Destination_2']
                req_format.loc[df_index, 'Flight2_Arrival_Time'] = flight['Arrival_2']
                req_format.loc[df_index, 'Flight2_Duration'] = duration_2_str
                
                req_format.loc[df_index, 'Flight3_Origin'] = flight['Origin_3']
                req_format.loc[df_index, 'Flight3_Departure_Time'] = flight['Departure_3']
                req_format.loc[df_index, 'Flight3_Destination'] = flight['Destination_3']
                req_format.loc[df_index, 'Flight3_Arrival_Time'] = flight['Arrival_3']
                req_format.loc[df_index, 'Flight3_Duration'] = duration_3_str
                
                logger.debug(f"req_format.loc[df_index, 'Itinerary_Departure_Time'] Type: {type(req_format.loc[df_index, 'Itinerary_Departure_Time'])}")
                
                # Increment counter after each row is added
                counter += 1
                df_index += 1
            
            # Iterate through the DataFrame for non-stop flights
            
            # for idx, flight in flights_df.iterrows():
            #     departure_time = datetime.strptime(flight.iloc[departure_index], '%H:%M:%S')
            #     arrival_time = datetime.strptime(flight.iloc[arrival_index], '%H:%M:%S')

            #     if arrival_time < departure_time:
            #         arrival_time += timedelta(days=1)

            #     duration = arrival_time - departure_time
            #     hours = duration.seconds // 3600
            #     minutes = (duration.seconds % 3600) // 60
            #     duration_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

            #     req_format.loc[df_index, 'Itinerary_Duration'] = duration_str
            #     # Increment counter and df_index for each row added
            #     counter += 1
            #     df_index += 1

            # # Iterate through the DataFrame for single-stop flights
            # for idx, flight in ss_itin_df.iterrows():
            #     departure_time_1 = datetime.strptime(flight['Departure_1'], '%H:%M:%S')
            #     arrival_time_1 = datetime.strptime(flight['Arrival_1'], '%H:%M:%S')
            #     if arrival_time_1 < departure_time_1:
            #         arrival_time_1 += timedelta(days=1)

            #     departure_time_2 = datetime.strptime(flight['Departure_2'], '%H:%M:%S')
            #     arrival_time_2 = datetime.strptime(flight['Arrival_2'], '%H:%M:%S')
            #     if arrival_time_2 < departure_time_2:
            #         arrival_time_2 += timedelta(days=1)

            #     duration_1 = arrival_time_1 - departure_time_1
            #     hours_1 = duration_1.seconds // 3600
            #     minutes_1 = (duration_1.seconds % 3600) // 60
            #     duration_1_str = f"{hours_1}h {minutes_1}m" if minutes_1 > 0 else f"{hours_1}h"

            #     duration_2 = arrival_time_2 - departure_time_2
            #     hours_2 = duration_2.seconds // 3600
            #     minutes_2 = (duration_2.seconds % 3600) // 60
            #     duration_2_str = f"{hours_2}h {minutes_2}m" if minutes_2 > 0 else f"{hours_2}h"

            #     total_duration = duration_1 + duration_2
            #     hours_t = total_duration.seconds // 3600
            #     minutes_t = (total_duration.seconds % 3600) // 60
            #     total_duration_str = f"{hours_t}h {minutes_t}m" if minutes_t > 0 else f"{hours_t}h"

            #     req_format.loc[df_index, 'Itinerary_Duration'] = total_duration_str
            #     # Increment counter and df_index for each row added
            #     counter += 1
            #     df_index += 1

            # # Iterate through the DataFrame for double-stop flights
            # for idx, flight in ds_itin_df.iterrows():
            #     departure_time_1 = datetime.strptime(flight['Departure_1'], '%H:%M:%S')
            #     arrival_time_1 = datetime.strptime(flight['Arrival_1'], '%H:%M:%S')
            #     if arrival_time_1 < departure_time_1:
            #         arrival_time_1 += timedelta(days=1)

            #     departure_time_2 = datetime.strptime(flight['Departure_2'], '%H:%M:%S')
            #     arrival_time_2 = datetime.strptime(flight['Arrival_2'], '%H:%M:%S')
            #     if arrival_time_2 < departure_time_2:
            #         arrival_time_2 += timedelta(days=1)

            #     departure_time_3 = datetime.strptime(flight['Departure_3'], '%H:%M:%S')
            #     arrival_time_3 = datetime.strptime(flight['Arrival_3'], '%H:%M:%S')
            #     if arrival_time_3 < departure_time_3:
            #         arrival_time_3 += timedelta(days=1)

            #     duration_1 = arrival_time_1 - departure_time_1
            #     hours_1 = duration_1.seconds // 3600
            #     minutes_1 = (duration_1.seconds % 3600) // 60
            #     duration_1_str = f"{hours_1}h {minutes_1}m" if minutes_1 > 0 else f"{hours_1}h"

            #     duration_2 = arrival_time_2 - departure_time_2
            #     hours_2 = duration_2.seconds // 3600
            #     minutes_2 = (duration_2.seconds % 3600) // 60
            #     duration_2_str = f"{hours_2}h {minutes_2}m" if minutes_2 > 0 else f"{hours_2}h"

            #     duration_3 = arrival_time_3 - departure_time_3
            #     hours_3 = duration_3.seconds // 3600
            #     minutes_3 = (duration_3.seconds % 3600) // 60
            #     duration_3_str = f"{hours_3}h {minutes_3}m" if minutes_3 > 0 else f"{hours_3}h"

            #     total_duration = duration_1 + duration_2 + duration_3
            #     hours_t = total_duration.seconds // 3600
            #     minutes_t = (total_duration.seconds % 3600) // 60
            #     total_duration_str = f"{hours_t}h {minutes_t}m" if minutes_t > 0 else f"{hours_t}h"

            #     req_format.loc[df_index, 'Itinerary_Duration'] = total_duration_str
            #     # Increment counter and df_index for each row added
            #     counter += 1
            #     df_index += 1
           
                
                
            # logger.debug(f"req_format['Itinerary_Departure_Time']: {req_format['Itinerary_Departure_Time']}")
            # logger.debug(f"req_format['Itinerary_Departure_Time'] Type: {type(req_format['Itinerary_Departure_Time'])}")
                
            # req_format['Itinerary_Departure_Time'] = req_format['Itinerary_Departure_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            # req_format['Itinerary_Arrival_Time'] = req_format['Itinerary_Arrival_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            
            # req_format['Flight1_Departure_Time'] = req_format['Flight1_Departure_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            # req_format['Flight2_Departure_Time'] = req_format['Flight2_Departure_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            # req_format['Flight3_Departure_Time'] = req_format['Flight3_Departure_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            
            # req_format['Flight1_Arrival_Time'] = req_format['Flight1_Arrival_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            # req_format['Flight2_Arrival_Time'] = req_format['Flight2_Arrival_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
            # req_format['Flight3_Arrival_Time'] = req_format['Flight3_Arrival_Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None)
                    
            # Print the DataFrame
            request.session['new_flights_df'] = new_flights_df.to_json(orient='split')
            request.session['ss_itin_df'] = ss_itin_df.to_json(orient='split')
            request.session['ds_itin_df'] = ds_itin_df.to_json(orient='split')
            request.session['req_format'] = req_format.to_json(orient='split')

            return redirect('results_Itin')

    else:
        turn_around_form = TurnAroundTimeForm()
        connection_time_form = ConnectionTimeForm()
        distance_ratio_form = DistanceConstraintForm()

    return render(request, 'pages/itinerarybuilder.html', {
        'turn_around_form': turn_around_form,
        'connection_time_form': connection_time_form,
        'distance_ratio_form' : distance_ratio_form,
    })


def results_Itin(request):
    new_flights_df = pd.read_json(request.session.get('new_flights_df', pd.DataFrame().to_json(orient='split')), orient='split') if 'new_flights_df' in request.session else None
    
    ss_itin_df = pd.read_json(request.session.get('ss_itin_df', pd.DataFrame().to_json(orient='split')), orient='split') if 'ss_itin_df' in request.session else None
    ds_itin_df = pd.read_json(request.session.get('ds_itin_df', pd.DataFrame().to_json(orient='split')), orient='split') if 'ds_itin_df' in request.session else None
    req_format = pd.read_json(request.session.get('req_format', pd.DataFrame().to_json(orient='split')), orient='split') if 'req_format' in request.session else None
    
    show_flights = new_flights_df is not None and not new_flights_df.empty
    show_ss_results = ss_itin_df is not None and not ss_itin_df.empty
    show_ds_results = ds_itin_df is not None and not ds_itin_df.empty
    show_req_format = req_format is not None and not req_format.empty

    
    # After preparing all dataframes
    excel_filename_1 = save_IB_dataframes_to_excel(new_flights_df, ss_itin_df, ds_itin_df)
    excel_filename_2 = save_req_format_dataframe_to_excel(req_format)

    return render(request, 'pages/itinerarybuilder.html', {
        'flights_df': new_flights_df.to_html(classes=["table", "table-striped"], index=False),
        'ss_itin_df': ss_itin_df.to_html(classes=["table", "table-striped"], index=False),
        'ds_itin_df': ds_itin_df.to_html(classes=["table", "table-striped"], index=False),
        'show_flights': show_flights,
        'show_ss_results': show_ss_results,
        'show_ds_results': show_ds_results,
        'excel_file_url_1': excel_filename_1,
        'excel_file_url_2': excel_filename_2
    })
    
flights_sample_df = pd.DataFrame({
    'Flight Number': [123, 124],
    'Origin': ['CAI', 'SSH'],
    'Departure': ['10:00', '14:00'],
    'Destination': ['SSH', 'ASW'],
    'Arrival': ['12:00', '16:00'],
})

def preview_IB_flights_sample(request):
    """View to handle AJAX request for previewing the flights sample on a webpage."""
    html_table = flights_sample_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})

def download_IB_flights_sample_excel(request):
    """View to handle downloading the flights sample as an Excel file."""
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Flight_Data_Excel_Sample.xlsx"'
    
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        flights_sample_df.to_excel(writer, index=False)
    
    return response


def preview_airports_sample(request):
    # Sample data for itineraries
    airports_sample_df = pd.DataFrame({
        'Airport': ['CAI','SSH', 'ASW'],
        'Latitude': [22.47611, 27.9794911, 23.9636164],
        'Longitude': [103.97345, 34.3946305, 32.8292664],
    })

    # Convert DataFrame to HTML table
    html_table = airports_sample_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})

def download_airports_sample_excel(request):
    # Define a DataFrame with the necessary columns
    airports_sample_df = pd.DataFrame(columns=[
        'Airport', 'Latitude', 'Longitude'
    ])
    
    airports_sample_df.loc[0] = ['CAI', 22.47611, 103.97345]
    airports_sample_df.loc[1] = ['SSH', 27.9794911, 34.3946305]
    airports_sample_df.loc[2] = ['ASW', 23.9636164, 32.8292664]


    # Define the Excel response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Itinerary_Data_Excel_Sample.xlsx"'

    # Write the empty DataFrame to the Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        airports_sample_df.to_excel(writer, index=False)

    return response


def save_IB_dataframes_to_excel(flights_df, ss_itin_df, ds_itin_df):
    filename = 'ItineraryBuilder All Results.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        flights_df.to_excel(writer, sheet_name='Non Stop Itineraries', index=False)
        ss_itin_df.to_excel(writer, sheet_name='Single Stop Itineraries', index=False)
        ds_itin_df.to_excel(writer, sheet_name='Double Stop Itineraries', index=False)
    return filename

def download_IB_results_excel(request):
    filename = 'ItineraryBuilder All Results.xlsx'
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
    
def save_req_format_dataframe_to_excel(req_format):
    filename = 'ItineraryBuilder Formatted Results.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
       
        # change time columns 
        # Convert relevant columns to datetime and extract time part
        time_columns = ['Itinerary_Departure_Time', 'Itinerary_Arrival_Time','Flight1_Departure_Time','Flight1_Arrival_Time','Flight2_Departure_Time','Flight2_Arrival_Time','Flight3_Departure_Time','Flight3_Arrival_Time']  # Add all relevant column names here
        print('ki0',req_format['Itinerary_Departure_Time'])
        
        for column in time_columns:
            req_format[column] = pd.to_datetime(req_format[column]).dt.time
        
        
        print('ki1',req_format['Itinerary_Departure_Time'])
        req_format.to_excel(writer, sheet_name='Required Format', index=False)
        
        # Get the xlsxwriter workbook from the writer
        workbook = writer.book
        worksheet = writer.sheets['Required Format']

        # Create a text format for Excel to treat data as text
        text_format = workbook.add_format({'num_format': '@', 'align': 'left'})

        # Apply the text format to the time columns
        time_columns = ['E:E', 'G:G', 'L:L', 'N:N', 'Q:Q', 'S:S', 'V:V', 'X:X']
        for col in time_columns:
            worksheet.set_column(col, None, text_format)  # Apply text format to each specified column

    
    return filename

def download_req_format_excel(request):
    filename = 'ItineraryBuilder Formatted Results.xlsx'
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




