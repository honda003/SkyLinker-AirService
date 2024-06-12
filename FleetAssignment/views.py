from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ExcelUploadForm, create_column_index_form, create_solver_selection_form, FleetCountForm, create_fleet_detail_form, create_optional_flights_form, DemandAdjustmentForm, RecaptureRatioForm
from .utils import SyncReadExcel, FlightColumnIndex, ItinColumnIndex, ClockToMinutes, NodesGenerator, VariableY, flights_oeprating_costs, FlightsCategorization, VariableZ, spilled_and_captured_variables, DemandCorrection
import pandas as pd
import json
import numpy as np
from io import StringIO
from pyomo.util.infeasible import log_infeasible_constraints
import pyomo.environ as pyo 
from pyomo.environ import *
from pyomo.opt import SolverFactory
import os
from django.conf import settings
import traceback
from django.http import FileResponse, HttpResponseNotFound, HttpResponse, HttpResponseServerError
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@login_required
def upload_flights_excel(request):
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
                return render(request, 'pages/fleetassignment.html', {'flight_excel_form': form, 'error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            flights_df_json = read_excel.get_dataframe().to_json(orient='split')
            flights_list = read_excel.get_data_list()

            # Store in session
            request.session['flights_df'] = flights_df_json
            request.session['flights_list'] = flights_list

            return redirect('process_flight_columns')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/fleetassignment.html', {'flight_excel_form': form})

def process_flight_columns(request):
    if 'flights_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_flights_excel')

    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    flight_column_index = FlightColumnIndex(flights_df)

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

                is_valid, message = flight_column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/fleetassignment.html', {'flight_column_form': form, 'error_messages': error_messages})
            
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**flight_column_index.columns, **provided_indexes}
            # Save complete column indexes in session
            request.session['flight_column_indexes'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            
            if 'number_of_fleets' in request.session:
                request.session.pop('number_of_fleets', None)
                
            # Proceed to upload itineraries excel file
            return redirect('fleet_data')
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/fleetassignment.html', {'flight_column_form': form})
    else:
        # Either we have all columns from the start or we need to ask for them
        if flight_column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = flight_column_index.missing_columns
            form = create_column_index_form(flight_column_index.missing_columns)()
            return render(request, 'pages/fleetassignment.html', {'flight_column_form': form})
        else:
            # No missing columns, use found columns
            request.session['flight_column_indexes'] = json.dumps(flight_column_index.columns)
            
            if 'number_of_fleets' in request.session:
                request.session.pop('number_of_fleets', None)

            # Proceed to upload itineraries excel file
            return redirect('fleet_data')


def fleet_data(request):
    count_form = FleetCountForm(request.POST or None)
    detail_forms = []

    if request.method == 'POST':
        if 'submit_count' in request.POST:
            if count_form.is_valid():
                number_of_fleets = count_form.cleaned_data['number_of_fleets']
                request.session['number_of_fleets'] = number_of_fleets
                # Create each form but do not bind POST data yet
                detail_forms = [create_fleet_detail_form(None, number_of_fleets, i + 1) for i in range(number_of_fleets)]
                return render(request, 'pages/fleetassignment.html', {'count_form': count_form, 'detail_forms': detail_forms})

        elif 'submit_details' in request.POST:
            number_of_fleets = request.session.get('number_of_fleets', 0)
            # This time, bind the POST data because we are submitting these forms
            detail_forms = [create_fleet_detail_form(request.POST, number_of_fleets, i + 1) for i in range(number_of_fleets)]
            if all(form.is_valid() for form in detail_forms):
                fleet_details = []
                for form in detail_forms:
                    # Correctly accessing cleaned_data using the base field names
                    fleet_data = {
                        'Fleet Type': form.cleaned_data['fleet_type'],
                        'Number of Aircrafts': form.cleaned_data['number_of_aircrafts'],
                        'Number of Seats': form.cleaned_data['number_of_seats'],
                        'Operating Cost Per Mile': form.cleaned_data['operating_cost_per_mile']
                    }
                    fleet_details.append(fleet_data)

                fleets_df = pd.DataFrame(fleet_details)
                fleet_list = fleets_df['Fleet Type'].tolist()
                
                request.session['fleets_df'] = fleets_df.to_json(orient='split')
                request.session['fleet_list'] = fleet_list
                # Process valid forms
                # Do something with the data
                return redirect('solver_selection')

    else:
        if 'number_of_fleets' in request.session:
            number_of_fleets = request.session['number_of_fleets']
            # Create forms without binding POST data initially
            detail_forms = [create_fleet_detail_form(None, number_of_fleets, i + 1) for i in range(number_of_fleets)]

    return render(request, 'pages/fleetassignment.html', {'count_form': count_form, 'detail_forms': detail_forms})



def solver_selection(request):
    if request.method == 'POST':
        solver_selection_form = create_solver_selection_form()(request.POST)
        if solver_selection_form.is_valid():
            
            # Extract selected solver from the form
            selected_solver = solver_selection_form.cleaned_data['solver']
            
            # Save the extracted values into the session
            request.session['selected_solver'] = selected_solver
            
            if selected_solver == 'ISD-IFAM':
                return redirect('demand_adjustment')  # Adjust 'next_step' as needed
            elif selected_solver == 'IFAM':
                return redirect('recapture_ratio') 
            else:
                return redirect('optional_flights_selection')  # Adjust 'next_step' as needed
    else:
        solver_selection_form = create_solver_selection_form()

    return render(request, 'pages/fleetassignment.html', {
        'solver_selection_form': solver_selection_form
    })

def recapture_ratio(request):
    if request.method == 'POST':
        form = RecaptureRatioForm(request.POST)
        if form.is_valid():
            # Process the data in form.cleaned_data     
            request.session['recapture_ratio'] = form.cleaned_data['recapture_ratio']
            
            # Then redirect to the next step in your workflow
            return redirect('upload_itineraries_excel')
    else:
        recapture_ratio_form = RecaptureRatioForm()

    return render(request, 'pages/fleetassignment.html', {
        'recapture_ratio_form': recapture_ratio_form
    })
    
def demand_adjustment(request):
    if request.method == 'POST':
        form = DemandAdjustmentForm(request.POST)
        if form.is_valid():
            # Process the data in form.cleaned_data     
            request.session['recapture_ratio'] = form.cleaned_data['recapture_ratio']
            request.session['decrease_demand_percentage'] = form.cleaned_data['decrease_demand_percentage']
            request.session['increase_demand_percentage'] = form.cleaned_data['increase_demand_percentage']
            
            # Then redirect to the next step in your workflow
            return redirect('upload_itineraries_excel')
    else:
        demand_factors_form = DemandAdjustmentForm()

    return render(request, 'pages/fleetassignment.html', {
        'demand_factors_form': demand_factors_form
    })

def upload_itineraries_excel(request):
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
                return render(request, 'pages/fleetassignment.html', {'itinerary_excel_form': form, 'error_message': str(e)})

            # Convert DataFrame to JSON for session storage
            itineraries_df_json = read_excel.get_dataframe().to_json(orient='split')
            itineraries_list = read_excel.get_data_list()

            # Store in session
            request.session['itineraries_df'] = itineraries_df_json
            request.session['itineraries_list'] = itineraries_list

            return redirect('process_itinerary_columns')
    else:
        form = ExcelUploadForm()

    return render(request, 'pages/fleetassignment.html', {'itinerary_excel_form': form})

def process_itinerary_columns(request):
    if 'itineraries_df' not in request.session:
        # Redirect to upload page if session does not contain flight data
        return redirect('upload_itineraries_excel')

    # Load DataFrame from session
    itineraries_df_json = request.session.get('itineraries_df')
    itineraries_df = pd.read_json(StringIO(itineraries_df_json), orient='split')
    
    # Initialize ColumnIndex with DataFrame
    itinerary_column_index = ItinColumnIndex(itineraries_df)

    if request.method == 'POST' and 'missing_columns' in request.session:
        # User is submitting indexes for missing columns
        form = create_column_index_form(request.session['missing_columns'])(request.POST)
        if form.is_valid():
            provided_indexes = {col: form.cleaned_data[f"{col}_index"] - 1 for col in request.session['missing_columns']}
            
            error_messages = []
            for col, idx in provided_indexes.items():
                if idx >= len(itineraries_df.columns) or idx < 0:
                    error_messages.append(f"Index for {col} is out of the valid range (1 - {len(itineraries_df.columns)}).")
                    continue

                is_valid, message = itinerary_column_index.validate_column_data(idx, col)
                if not is_valid:
                    error_messages.append(message)
            
            if error_messages:
                # If there are any errors, re-render the form with the errors displayed
                return render(request, 'pages/fleetassignment.html', {'itinerary_column_form': form, 'error_messages': error_messages})
            
            # Merge provided indexes with those found by ColumnIndex
            complete_indexes = {**itinerary_column_index.columns, **provided_indexes}
            # Save complete column indexes in session
            request.session['itinerary_column_indexes'] = json.dumps(complete_indexes)
            # Remove 'missing_columns' from session as it's no longer needed
            del request.session['missing_columns']
            
            if 'selected_solver' in request.session:
                if request.session.get('selected_solver') == 'IFAM':
                    return redirect('IFAM')
                else:
                    return redirect('optional_flights_selection')
            else:
                return redirect('optional_flights_selection')                 
            
            # Proceed to upload itineraries excel file
            
        else:
            # Form is invalid, render it again with errors
            return render(request, 'pages/fleetassignment.html', {'itinerary_column_form': form})
    else:
        # Either we have all columns from the start or we need to ask for them
        if itinerary_column_index.missing_columns:
            # There are missing columns, need user input
            request.session['missing_columns'] = itinerary_column_index.missing_columns
            form = create_column_index_form(itinerary_column_index.missing_columns)()
            return render(request, 'pages/fleetassignment.html', {'itinerary_column_form': form})
        else:
            # No missing columns, use found columns
            request.session['itinerary_column_indexes'] = json.dumps(itinerary_column_index.columns)
            
            if 'selected_solver' in request.session:
                if request.session.get('selected_solver') == 'IFAM':
                    return redirect('IFAM')
                else:
                    return redirect('optional_flights_selection')
            else:
                return redirect('optional_flights_selection') 
 
def optional_flights_selection(request):
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    flight_column_indexes = json.loads(request.session['flight_column_indexes'])
    flight_no_col = flight_column_indexes.get('flight number')

    if request.method == 'POST':
        form = create_optional_flights_form(flights_df, flight_no_col)(request.POST)
        if form.is_valid():
            has_optional = form.cleaned_data['has_optional_flights']
            all_flights_optional = form.cleaned_data.get('all_flights_optional', False)
            selected_flights = form.cleaned_data.get('select_optional_flights', [])
            
            selected_flights = [int(flight) for flight in selected_flights]
            
            print(f'selected_flights type\n: {type(selected_flights)}\n \n')
            print(f'selected_flights\n: {selected_flights}\n \n')
            print(f'Flight Number Column\n: {flight_no_col}\n \n')
            print(f'Flight Number\n: {flights_df.iloc[:, flight_no_col]}\n \n')
            print(f'Condition\n: {flights_df.loc[flights_df.iloc[:, flight_no_col].isin(selected_flights) ]}\n \n')

            if has_optional == 'no':
                flights_df['Optional'] = 0
                
            elif selected_flights:
                flights_df['Optional'] = 0
                flights_df.loc[flights_df.iloc[:, flight_no_col].isin(selected_flights), 'Optional'] = 1
            else:
                flights_df['Optional'] = 1
            
                
            print(f'flights_df\n: {flights_df['Optional']}\n \n')

            # Convert DataFrame back to JSON and store in session
            flights_df_json = flights_df.to_json(orient='split')
            request.session['flights_df'] = flights_df_json
            
            selected_solver = request.session.get('selected_solver')
            
            if selected_solver == 'ISD-IFAM':
                return redirect('ISD_IFAM')
            elif selected_solver == 'FAM':
                return redirect('FAM')
            else:
                return redirect('IFAM')
                
    else:
        form = create_optional_flights_form(flights_df, flight_no_col)()

    return render(request, 'pages/fleetassignment.html', {
        'optional_flights_form': form
    })        

def FAM(request):
    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
     
    fleets_df_json = request.session.get('fleets_df')
    fleets_df = pd.read_json(StringIO(fleets_df_json), orient='split') 
    
    flight_column_indexes = json.loads(request.session['flight_column_indexes'])
    flight_no_col = flight_column_indexes.get('flight number')
    origin_col = flight_column_indexes.get('origin')
    departure_col = flight_column_indexes.get('departure')
    destination_col = flight_column_indexes.get('destination')
    arrival_col = flight_column_indexes.get('arrival')
    distance_col = flight_column_indexes.get('distance')
    duration_col = flight_column_indexes.get('duration')
       
    station_list = np.unique(flights_df.iloc[:, origin_col].to_list())       # list of stations
    flights_list = flights_df.iloc[:, flight_no_col].astype(str).tolist()    #List of flights
    fleet_list = fleets_df['Fleet Type'].tolist()
    oc_list = fleets_df['Operating Cost Per Mile'].tolist()
    
    # ****************** Convert time to minutes **************** #
    dep_arriv = ClockToMinutes(flights_df, departure_col, arrival_col)
    dep = dep_arriv.get_departure_minutes()
    arriv = dep_arriv.get_arrival_minutes()
     
    # ****************** Generate Balance Nodes **************** #
    Nodes_df_instance = NodesGenerator(flights_df, station_list, flight_no_col, origin_col, destination_col, departure_col, arrival_col, dep, arriv)
    Nodes_df = Nodes_df_instance.get_nodes()
       
    # ****************** Ground Arc Variable (Y) **************** #
    var_y_instance = VariableY(Nodes_df, station_list, fleet_list)
    vars_y = var_y_instance.get_y()
    
    # ----------------------- FAM MODEL --------------------------#
    # Creating Model
    model = ConcreteModel()
    # ----------------------- Generating Problem's sets Starts Here --------------------------#
   
    model.setF = pyo.Set(initialize = flights_list) # set of all flights optional and non optional
    model.setE = pyo.Set(initialize = fleet_list)  # set of fleet --> from 1 to 2
    model.setS = pyo.Set(initialize=station_list)  # set of stations --> [ORD,LAX,BOS]
    
    # ****************** Find Optional Flights **************** #
    cat = FlightsCategorization(flights_df, flight_no_col)
    optional_flights = cat.optional_flights
    non_optional_flights = cat.non_optional_flights
    
    print(f'optional flights\n {optional_flights} \n\n')
    print(f'flights_df\n {flights_df} \n\n')        
                
    
    # ****************** Define non/Optional Flight Sets**************** #
    model.setF_optional = pyo.Set(initialize = optional_flights)             # set of optional flights
    model.setF_non_optional = pyo.Set(initialize = non_optional_flights )    # set of non optional flights
    
    # ----------------------- Generating Problem's sets Ends Here --------------------------#

    # ----------------------- Generating Problem's Parameters Starts Here --------------------------#
    # first paramater in the problem is C(f,e) which is the cost of assigning aircraft e to flight leg f
    # Making the list of costs

    # ****************** Calculate Operating Cost (C) **************** #
    flights_costs= flights_oeprating_costs(flights_df , fleets_df)
    cost_list= flights_costs.given_operating_cost(distance_col, oc_list)

    # Creating the dictionary which has the flight,fleet as key equals to value from cost_list
    C_fe = {}
    cost_list_counter = 0
    for i in model.setF:
        for j in model.setE:
            C_fe[f'{i},{j}'] = cost_list[cost_list_counter]
            cost_list_counter += 1

    # Let's move to the second paramater in our problem (Ne) which is the number of available aircraft of each fleet type
    Ne = {}
    for number_of_airplane in range(len(fleets_df)):
        Ne[fleets_df.iloc[number_of_airplane]['Fleet Type']] = fleets_df.iloc[number_of_airplane]['Number of Aircrafts']
    # ----------------------- Generating Problem's Parameters Ends Here --------------------------#
        
    # ----------------------- Generating Problem's Decision Variables Starts Here --------------------------#
    # Defining the first decision variable (Xf,e) which is binary that indicates is that flight coverd by the first or second fleet
    # this is two dimensional variable the first dimension indicates the flight number and the second one indicates the fleet number
    model.x = pyo.Var(model.setF, model.setE, within = Binary, bounds=(0,1))
    x = model.x

    # Defining the second desicion variable(RONs,e) which is Integer
    # that represents represents the number of aircraft of fleet type e that remain overnight at station S
    model.RON = pyo.Var(model.setS, model.setE, within=Integers, bounds = (0,None))
    RON = model.RON

    # Defining the third decision variable(Yi_j,e) which is Integer
    # that represents the number of aircrafts between nodes i and j for fleet e
    model.y = pyo.Var(vars_y, within=Integers, bounds = (0,None))
    y = model.y
    # ----------------------- Generating Problem's Decision Variables Ends Here --------------------------#

    # ----------------------- Generating Problem's Objective Function Starts Here --------------------------#
    #Objective Function is minimizing the operating cost of flight f operated by fleet e
    model.obj = pyo.Objective(expr=sum([C_fe[f"{f},{e}"]*x[f,e]
                                        for f in model.setF
                                        for e in model.setE]),
                            sense=minimize)
    # ----------------------- Generating Problem's Objective Function Ends Here  --------------------------#
    
    # ----------------------- Writing Constraints by Pyomo Syntax Starts Here --------------------------# 

    # ****************** Coverage Constraint **************** #
    model.coverage = ConstraintList()
    for f in model.setF:
        if f in model.setF_optional:
            model.coverage.add(expr = sum([x[f,e] for e in model.setE ]) <= 1)
        elif f in model.setF_non_optional:
            model.coverage.add(expr = sum([x[f,e] for e in model.setE ]) == 1)

    # Writing the Resources Constraints
    model.resource = ConstraintList()
    for e in model.setE:
        model.resource.add(expr=sum([RON[station,e]
                        for station in model.setS]) <= Ne[e])

    # Writing the Balance Constraints
    model.balance = ConstraintList()
    for fleet in model.setE:
        for node in Nodes_df.index:
            
            city = Nodes_df.iloc[node-1]['city']
            city_nodes_df = Nodes_df[Nodes_df['city'] == city]

            first_node = city_nodes_df.index.values.min()
            last_node = city_nodes_df.index.values.max()

            y_sum = 0

    # Assuming 'first_node', 'last_node' are defined
            if first_node != last_node:
                # Writing The Ground Arcs
                y_sum = (sum([model.y[var_name] if (var_name.replace(",", "_").split('_')[1] == str(node)) & ((str(fleet)) in var_name) else 0 for var_name in vars_y])) +\
                    (sum([-1*model.y[var_name] if (var_name.replace(",", "_").split('_')[0] == str(node)) &
                    ((str(fleet)) in var_name) else 0 for var_name in vars_y]))

            #Writing The Whole Balance Constraint
            model.balance.add(expr=y_sum +
                            sum(flight[1] * model.x[str(flight[0]), fleet]
                                for flight in Nodes_df.iloc[node-1]['flights'])
                            + (RON[city, fleet] if node == first_node and node != last_node else -1 *
                                model.RON[city, fleet] if node == last_node and node != first_node else 0)
                            == 0)
            
    # ----------------------- Writing Constraints by Pyomo Syntax Ends Here --------------------------# 
    # ----------------------- FAM Model Ends Here --------------------------# 
    
    # ----------------------- Solving The Problem --------------------------# 
    opt = SolverFactory('gurobi') #Solving using gurobi solver
    problem_results = opt.solve(model)
    # Function to convert minutes to hh:mm:ss format
    def minutes_to_time(minutes):
        hours = int(minutes // 60)
        minutes = int(minutes % 60)
        return '{:02d}:{:02d}:00'.format(hours, minutes)

    # Convert DepartureTime and ArrivalTime columns
    flights_df.iloc[:, departure_col] = flights_df.iloc[:, departure_col].apply(minutes_to_time)
    flights_df.iloc[:, arrival_col] = flights_df.iloc[:, arrival_col].apply(minutes_to_time)
    
    print(f'Operating cost \n\n {cost_list}\n\n')


    if problem_results.solver.termination_condition == TerminationCondition.optimal:
    # The solver was successful, and the optimal solution is available
    
        # Create a dictionary to store fleet type assignments for each flight based on Pyomo variable x
        flight_assignments = {}
        operate_flight = {}
        for i in model.component_objects(pyo.Var, active=True):  # Iterate over all Pyomo variables
            print(i)
            if i.name == "x":  # Ensure to process only the relevant variable
                for idx in i:
                    print(f'{i[idx]} = {i[idx].value}')  # Debug print
                    flight_number, fleet_type = idx
                    if pyo.value(i[idx]) == 1:  # Check if this assignment is selected
                        # Ensure that flight_number is an integer if it's stored as such in flights_df
                        flight_assignments[int(flight_number)] = fleet_type
        
        # Now, ensure all flights are accounted for in 'operate_flight'
        for flight_number in flights_df.iloc[:, flight_no_col]:
            if flight_number not in operate_flight:
                operate_flight[flight_number] = 'Yes'  # Default to 'Yes' if not found

        # Debug print to check the content of the flight_assignments dictionary
        print("Flight Assignments:", flight_assignments)

        # Map fleet types to flight numbers ensuring the index is integer if required
        flights_df['Fleet Type'] = flights_df.iloc[:, flight_no_col].map(flight_assignments)  # Adjust FlightNumber if it's not the correct column name
        fleet_type_col = flights_df.columns.get_loc('Fleet Type')
        
        
        # Select relevant columns and rename them to match the required structure
        result_df = flights_df.iloc[:, [flight_no_col, origin_col, departure_col, destination_col, arrival_col, distance_col, duration_col, fleet_type_col]]
        result_df.columns = ['Flight Number', 'Origin', 'Departure', 'Destination', 'Arrival', 'Distance', 'Duration', 'Fleet Type']
        result_df['Fleet Type'].fillna(value='None',inplace=True)
        
        print(result_df)
        
        # After defining operate_flight and before creating result_df
        ron_aggregate = {}  # Dictionary to hold RON data

        # Extract RON data from the model
        for ron_var in model.component_objects(pyo.Var, active=True):
            if ron_var.name == "RON":
                for (station, fleet_type), value in ron_var.items():
                    if pyo.value(value) >= 0:  # Only consider positive RON values
                        if (station, fleet_type) not in ron_aggregate:
                            ron_aggregate[(station, fleet_type)] = 0
                        ron_aggregate[(station, fleet_type)] += int(pyo.value(value))

        # Convert RON data to a DataFrame for easier display
        ron_df = pd.DataFrame(list(ron_aggregate.items()), columns=['Station_Fleet', 'Number of Aircraft Staying Overnight'])
        ron_df[['Station', 'Fleet Type']] = pd.DataFrame(ron_df['Station_Fleet'].tolist(), index=ron_df.index)
        ron_df.drop(columns='Station_Fleet', inplace=True)

        # Reorder columns if necessary
        ron_df = ron_df[['Station', 'Fleet Type', 'Number of Aircraft Staying Overnight']]

        # Sort the DataFrame for better presentation
        ron_df.sort_values(by=['Station', 'Fleet Type'], inplace=True)

        # Debug print to check RON DataFrame
        print(ron_df)

        # Add the RON DataFrame to the session or directly to the template context
        request.session['ron_schedule_html'] = ron_df.to_html(classes=["table", "table-striped"], index=False)
        
        # Create individual dataframes for each fleet type
        for fleet_type in result_df['Fleet Type'].unique():
            if not pd.isna(fleet_type):  # Only process valid fleet type assignments
                fleet_df_name = f'fleet_type_{str(fleet_type)}_df'
                globals()[fleet_df_name] = result_df[result_df['Fleet Type'] == fleet_type]
                print(f'DataFrame {fleet_df_name} created with {len(globals()[fleet_df_name])} entries\n {globals()[fleet_df_name]} ')
                
        objective_value = pyo.value(model.obj)
        
        request.session['objective_value_FAM'] = objective_value
        request.session['optimized_schedule_html'] = result_df.to_html(classes=["table", "table-striped"], index=False)
        
        fleet_dfs = {}
        for fleet_type in result_df['Fleet Type'].unique():
            if not fleet_type == 'None':
                if not pd.isna(fleet_type):  # Only process valid fleet type assignments
                    fleet_df_name = f'fleet {str(fleet_type)}'
                    fleet_dfs[fleet_df_name] = result_df[result_df['Fleet Type'] == fleet_type]
                    print(f'DataFrame {fleet_df_name} created with {len(fleet_dfs[fleet_df_name])} entries')
                    print(fleet_dfs[fleet_df_name], '\n')

        # If you want to print each DataFrame separately after creation
        fleet_files = []
        for df_name, df in fleet_dfs.items():
            print(f"Contents of {df_name}:")
            print(df, '\n')
            excel_filename_2 = save_for_routing_to_excel(df, df_name)
            fleet_files.append({
                'fleet_type': df_name,
                'file_name': excel_filename_2
            })
        
        # After preparing all dataframes
        excel_filename = save_FAM_dataframes_to_excel(result_df, ron_df)


        return render(request, 'pages/fleetassignment.html', {
            'objective_value_FAM': objective_value,
            'optimized_schedule_html': result_df.to_html(classes=["table", "table-striped"], index=False),
            'ron_schedule_html': ron_df.to_html(classes=["table", "table-striped"], index=False),  # Add this line
            'excel_file_url': excel_filename,  # This is the link to the file for downloading
            'fleet_files': fleet_files   # This is the link to the file for downloading
            })

    else:
        # The solver did not find an optimal solution
        request.session['infeasibility_result'] = "Solver did not converge to an optimal solution."
        infeasibility_result = request.session.get('infeasibility_result', [])
        context = {
            'infeasibility_result': infeasibility_result,
            # You may want to include forms or other context data needed to render 'routing.html'
        }
        return render(request, 'pages/fleetassignment.html', context)
    
def save_FAM_dataframes_to_excel(result_df, ron_df):
    filename = 'Fleet_Assignment_Report.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        result_df.to_excel(writer, sheet_name='Optimized Schedule', index=False)
        ron_df.to_excel(writer, sheet_name='RON Details', index=False)
    
    return filename

def IFAM(request):
    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    fleets_df_json = request.session.get('fleets_df')
    fleets_df = pd.read_json(StringIO(fleets_df_json), orient='split')
    
    itineraries_df_json = request.session.get('itineraries_df')
    itineraries_df = pd.read_json(StringIO(itineraries_df_json), orient='split')
    
    flight_column_indexes = json.loads(request.session['flight_column_indexes'])
    flight_no_col = flight_column_indexes.get('flight number')
    origin_col = flight_column_indexes.get('origin')
    departure_col = flight_column_indexes.get('departure')
    destination_col = flight_column_indexes.get('destination')
    arrival_col = flight_column_indexes.get('arrival')
    distance_col = flight_column_indexes.get('distance')
    duration_col = flight_column_indexes.get('duration')
    
    itinerary_column_indexes = json.loads(request.session['itinerary_column_indexes'])
    itinerary_no_col = itinerary_column_indexes.get('itinerary')
    demand_col = itinerary_column_indexes.get('demand')
    fare_col = itinerary_column_indexes.get('fare')
    flights_col = itinerary_column_indexes.get('flights')
    type_col = itinerary_column_indexes.get('type')
    
    # Debugging log
    logger.debug(f"itinerary_no_col: {itinerary_no_col}")
    
    station_list = np.unique(flights_df.iloc[:, origin_col].to_list())       # list of stations
    flights_list = flights_df.iloc[:, flight_no_col].astype(str).tolist()    #List of flights
    fleet_list = fleets_df['Fleet Type'].tolist()
    oc_list = fleets_df['Operating Cost Per Mile'].tolist()
    
    # ****** Convert time to minutes ****** #
    dep_arriv = ClockToMinutes(flights_df, departure_col, arrival_col)
    dep = dep_arriv.get_departure_minutes()
    arriv = dep_arriv.get_arrival_minutes()
        
    # ****** Generate Balance Nodes ****** #
    Nodes_df_instance = NodesGenerator(flights_df, station_list, flight_no_col, origin_col, destination_col, departure_col, arrival_col, dep, arriv)
    Nodes_df = Nodes_df_instance.get_nodes()
    
    # ****** Recapture ratio bpr ****** #
    recapture_ratio = request.session.get('recapture_ratio')

    # ****** Ground Arc Variable (Y) ****** #
    var_y_instance = VariableY(Nodes_df, station_list, fleet_list)
    var_y = var_y_instance.get_y()
    
    # ****** Number of Available ACs ****** #
    Ne = {}
    for number_of_airplane in range(len(fleets_df)):
        Ne[fleets_df.iloc[number_of_airplane]['Fleet Type']] = fleets_df.iloc[number_of_airplane]['Number of Aircrafts']
        
    # ****** Define FAM Model Sets ****** #
    model = ConcreteModel()
    model.setF = pyo.Set(initialize = flights_list)     # set of flights
    model.setE = pyo.Set(initialize = fleet_list)       # set of fleet
    model.setS = pyo.Set(initialize=station_list)       # set of stations


    # ****** Define FAM Model Decision Variables ****** #
    model.x = pyo.Var(model.setF, model.setE, within=Binary, bounds=(0, None))  # This is two dimensional variable the first dimension indicates the flight number and the second one indicates the fleet number
    x = model.x

    model.RON = pyo.Var(model.setS, model.setE, within=Integers, bounds=(0, None)) # Second desicion variable (RONs,e) which is binary that represents represents the number of aircraft of fleet type e that remain overnight at station s
    RON = model.RON

    model.y = pyo.Var(var_y, within=Integers, bounds=(0, None)) # Defining the third decision variable(Y1_2,e) which is Integer that represents the number of aircrafts between nodes
    y = model.y


    # ****** Calculate Operating Cost (C) ****** #
    flights_costs= flights_oeprating_costs(flights_df , fleets_df)
    cost_list= flights_costs.given_operating_cost(distance_col, oc_list)
    # cost_list = [30000,16600,15100,13500,15500,45000,57000,13500,42000,16600,15500,45000] 
    # Creating the dictionary which has the flight,fleet as key equals to value from cost_list
    C_fe = {}
    cost_list_counter = 0
    for i in model.setF:
        for j in model.setE:
            C_fe[f'{i},{j}'] = cost_list[cost_list_counter]
            cost_list_counter += 1
              
                
    # ****** Define Itinerary Sets****** #
    model.setp = pyo.RangeSet(len(itineraries_df))                            # set of itenraries

    # ****** Define spilled passenger from itinerary p (tp) ****** #
    itineraries_demand_list =itineraries_df.iloc[:, demand_col].tolist() # Get column of demand from itenraries dataframe and convert to list
    model.t_spilled = pyo.Var(model.setp, within=pyo.Integers, bounds=lambda model, i: (0, itineraries_demand_list[i-1]))
    t_spilled=model.t_spilled
    
    # ****** Define spilled passenger from itinerary p and recaptured by itinerary r (tpr) ****** #
    data1=spilled_and_captured_variables(flights_df)
    itineraries_df=spilled_and_captured_variables.Itinraries_df_simplify(data1,itineraries_df,itinerary_no_col, flights_col, flight_no_col, origin_col, destination_col,type_col)

    itineraries_df.iloc[:, itinerary_no_col] = itineraries_df.iloc[:, itinerary_no_col].astype('int64')
    spilled_recaptured_vars=spilled_and_captured_variables.spill_recaptured_variables_list(data1, itineraries_df, itinerary_no_col)
    #print(f"Variable t_p_r:\n{spilled_recaptured_vars}")

    model.spilled_recaptured_vars = pyo.Var(spilled_recaptured_vars, within=Integers, bounds=(0, None))
    spilled_recaptured_vars = model.spilled_recaptured_vars


    # ****** Add Market Column in Itinerary dataframe ****** #
    itineraries_df['market'] = itineraries_df.apply(lambda row: [row['From'], row['To']], axis=1)

    # Create a list of lists 'airline_markets'
    airline_markets_for_each_itenrary = itineraries_df['market'].tolist() 
    # getting the unique markets
    ailine_market=[]

    for market in airline_markets_for_each_itenrary:
        if market not in ailine_market:
            ailine_market.append(market)
    #print(f'Itinerary Data Frame:\n{itineraries_df}\n')

    #_C_Operating costs
    C_Operating_cost=sum(C_fe[f"{f},{e}"] * model.x[f, e] for f in model.setF for e in model.setE)
    #print(f'Operating Cost (C):\n{C_Operating_cost}\n') 

    # ****** Calculate Spill Cost (S) ****** #
    S_Spill_Cost=sum(model.spilled_recaptured_vars[t_p_r] * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[1])).values , fare_col].values[0] for t_p_r in spilled_recaptured_vars)

    #print(f'Spill Cost (S):\n{S_Spill_Cost}\n')

    # ****** Calculate Recaptured Revenue (M) ****** #
    M_Recaptured_Revenue=sum(model.spilled_recaptured_vars[t_p_r] * recapture_ratio * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[2])).values , fare_col].values[0] 
                if t_p_r.split('_')[1] == str(r) and int(t_p_r.split('_')[2]) != len(itineraries_df)+1  
                else 0 
                for t_p_r in spilled_recaptured_vars   
                for r in model.setp.data())
    #print(f'Recaptured Revenue (M):\n{M_Recaptured_Revenue}\n')

    # ****** Objective Function ****** #
    model.obj = pyo.Objective(
        expr=(C_Operating_cost + S_Spill_Cost - M_Recaptured_Revenue),
        sense=pyo.minimize
    )

    # ****** Coverage Constraint ****** #
    model.coverage = ConstraintList()
    for f in model.setF:
        model.coverage.add(expr = sum([x[f,e] for e in model.setE ]) == 1)         

    # ****** Resources Constraint ****** #
    model.resources = ConstraintList()
    for e in model.setE:
        model.resources.add(expr=sum([RON[station, e]for station in model.setS]) <= Ne[e])   
        
    # ****** Balance Constraint ****** #
    model.balance = ConstraintList()
    for fleet in model.setE:
        for node in Nodes_df.index:

            city = Nodes_df.iloc[node-1]['city']
            city_nodes_df = Nodes_df[Nodes_df['city'] == city]

            first_node = city_nodes_df.index.values.min()
            last_node = city_nodes_df.index.values.max()

            y_sum = 0

    # Assuming 'first_node', 'last_node' are defined
            if first_node != last_node:
                # Define the constraint using Pyomo syntax
                y_sum = (sum([model.y[var_name] if (var_name.replace(",", "").split('_')[1] == str(node)) & ((str(fleet)) in var_name) else 0 for var_name in var_y])) +\
                    (sum([-1*model.y[var_name] if (var_name.replace(",", "").split('_')[0] == str(node)) &
                    ((str(fleet)) in var_name) else 0 for var_name in var_y]))

            model.balance.add(expr=y_sum +
                            sum(flight[1] * model.x[str(flight[0]), fleet]
                                for flight in Nodes_df.iloc[node-1]['flights'])
                            + (RON[city, fleet] if node == first_node and node != last_node else -1 *
                                model.RON[city, fleet] if node == last_node and node != first_node else 0)
                            == 0)
            

    # ****** Flight Interaction Constraint ****** # 
    model.flight_interaction = ConstraintList()

    for idx1, flight in flights_df.iterrows():

        # Spilled passengers
        spilled_passengers = sum(
            sum(
                model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[1] == str(itineraries_df.iloc[idx, itinerary_no_col]) else 0
                for t_p_r in spilled_recaptured_vars
            )
            if str(flight.iloc[flight_no_col]) in (str(itineraries_df.iloc[idx, flights_col]).split(", "))
            else 0
            for idx, itn in itineraries_df.iterrows()   
        )
        
        # Recaptured passengers
        recaptured_passengers = sum(
            sum(
                recapture_ratio * model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[2] == str(itineraries_df.iloc[idx, itinerary_no_col]) else 0
                for t_p_r in spilled_recaptured_vars
            )
            if str(flight.iloc[flight_no_col]) in (str(itineraries_df.iloc[idx, flights_col]).split(", "))
            else 0
            for idx, itn in itineraries_df.iterrows()   
        )
        
        # Flight unconstrained demand
        flight_unconstrained_demand = 0
        for idx, itn in itineraries_df.iterrows():
            if str(flight.iloc[flight_no_col]) in (str(itn.iloc[flights_col]).split(", ")):
                flight_unconstrained_demand += itn.iloc[demand_col]

        # Flight available seats
        flight_seats_available = sum(
            (model.x[str(flight.iloc[flight_no_col]), fleet.iloc[0]]) * fleet.iloc[2] for idx, fleet in fleets_df.iterrows()  ########### TAKE CARE FLEETS Index##############
        )
        
        
        #print(f'Interaction constraind Demand correction part equation{idx1 + 1}:\n{flight_demand_correction}\n')

        model.flight_interaction.add(expr= spilled_passengers - recaptured_passengers >= flight_unconstrained_demand - flight_seats_available)
            
    # ****** Spill-Recapture & Demand Constraints ****** #
    model.demand = ConstraintList()
    model.spill_recapture=ConstraintList()
    for itn in range(len(itineraries_df)):  
        
        itenrary=itineraries_df.iloc[itn, itinerary_no_col]
        t_p_r_sum = sum(model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[1] == str(itenrary) else 0 for t_p_r in spilled_recaptured_vars) # from I_FAM
        
        model.demand.add(expr= t_p_r_sum - itineraries_df.iloc[itn, demand_col] <= 0) # Demand Constraints
        
        model.spill_recapture.add(expr=t_p_r_sum== model.t_spilled[itenrary])  # Spill_recapture Constraints
        
            
    # ****** Solving ****** # 
    opt = SolverFactory('gurobi')
    #print('\n\nSolving please wait\n\n')
    problem_results = opt.solve(model)
            
    # Function to convert minutes to hh:mm:ss format
    def minutes_to_time(minutes):
        hours = int(minutes // 60)
        minutes = int(minutes % 60)
        return '{:02d}:{:02d}:00'.format(hours, minutes)

    # Convert DepartureTime and ArrivalTime columns
    flights_df.iloc[:, departure_col] = flights_df.iloc[:, departure_col].apply(minutes_to_time)
    flights_df.iloc[:, arrival_col] = flights_df.iloc[:, arrival_col].apply(minutes_to_time)


    if problem_results.solver.termination_condition == TerminationCondition.optimal:
    # The solver was successful, and the optimal solution is available
    
        # Create a dictionary to store fleet type assignments for each flight based on Pyomo variable x
        model.pprint()
        
        flight_assignments = {}
        operate_flight = {}
        for i in model.component_objects(pyo.Var, active=True):  # Iterate over all Pyomo variables
            print(i)
            if i.name == "x":  # Ensure to process only the relevant variable
                for idx in i:
                    print(f'{i[idx]} = {i[idx].value}')  # Debug print
                    flight_number, fleet_type = idx
                    if pyo.value(i[idx]) == 1:  # Check if this assignment is selected
                        # Ensure that flight_number is an integer if it's stored as such in flights_df
                        flight_assignments[int(flight_number)] = fleet_type
           
        # Now, ensure all flights are accounted for in 'operate_flight'
        for flight_number in flights_df.iloc[:, flight_no_col]:
            if flight_number not in operate_flight:
                operate_flight[flight_number] = 'Yes'  # Default to 'Yes' if not found

        # Debug print to check the content of the flight_assignments dictionary
        print("Flight Assignments:", flight_assignments)

        # Map fleet types to flight numbers ensuring the index is integer if required
        flights_df['Fleet Type'] = flights_df.iloc[:, flight_no_col].map(flight_assignments)  # Adjust FlightNumber if it's not the correct column name
        fleet_type_col = flights_df.columns.get_loc('Fleet Type')
       
        
        # Select relevant columns and rename them to match the required structure
        result_df = flights_df.iloc[:, [flight_no_col, origin_col, departure_col, destination_col, arrival_col, distance_col, duration_col, fleet_type_col]]
        result_df.columns = ['Flight Number', 'Origin', 'Departure', 'Destination', 'Arrival', 'Distance', 'Duration', 'Fleet Type']
        result_df['Fleet Type'].fillna(value='None',inplace=True)
        
        print(result_df)
        
        # After defining operate_flight and before creating result_df
        ron_aggregate = {}  # Dictionary to hold RON data

        # Extract RON data from the model
        for ron_var in model.component_objects(pyo.Var, active=True):
            if ron_var.name == "RON":
                for (station, fleet_type), value in ron_var.items():
                    if pyo.value(value) >= 0:  # Only consider positive RON values
                        if (station, fleet_type) not in ron_aggregate:
                            ron_aggregate[(station, fleet_type)] = 0
                        ron_aggregate[(station, fleet_type)] += int(pyo.value(value))

        # Convert RON data to a DataFrame for easier display
        ron_df = pd.DataFrame(list(ron_aggregate.items()), columns=['Station_Fleet', 'Number of Aircraft Staying Overnight'])
        ron_df[['Station', 'Fleet Type']] = pd.DataFrame(ron_df['Station_Fleet'].tolist(), index=ron_df.index)
        ron_df.drop(columns='Station_Fleet', inplace=True)

        # Reorder columns if necessary
        ron_df = ron_df[['Station', 'Fleet Type', 'Number of Aircraft Staying Overnight']]

        # Sort the DataFrame for better presentation
        ron_df.sort_values(by=['Fleet Type', 'Station'], inplace=True)

        # Debug print to check RON DataFrame
        print(ron_df)

        # Add the RON DataFrame to the session or directly to the template context
        request.session['ron_schedule_html'] = ron_df.to_html(classes=["table", "table-striped"], index=False)
        
        
        # Extracting data from t_spilled
        spilled_data = {}
        for var in model.component_objects(pyo.Var, active=True):
            if var.name == "t_spilled":
                for (i_j), value in var.items():
                    if pyo.value(value) > 0:  # Only consider cases where passengers are actually spilled and recaptured
                        i = i_j  # Split to get itinerary i and j
                        spilled_data[(int(i))] = int(pyo.value(value))                        

        # Convert the data to a DataFrame
        spilled_df = pd.DataFrame(list(spilled_data.items()), columns=['Itinerary', 'Number of Passengers'])
        spilled_df[['Spilling Itinerary']] = pd.DataFrame(spilled_df['Itinerary'].tolist(), index=spilled_df.index)
        spilled_df.drop(columns='Itinerary', inplace=True)
        spilled_df = spilled_df[['Spilling Itinerary', 'Number of Passengers']]

        # Sort by Itinerary From for better presentation
        spilled_df.sort_values(by=['Spilling Itinerary'], inplace=True)

        # Debug print to check DataFrame
        print(spilled_df)

        # Adding DataFrame to the session or directly to the template context
        request.session['spilled_html'] = spilled_df.to_html(classes=["table", "table-striped"], index=False)
        
        # Extracting data from spilled_recaptured_vars
        spilled_recaptured_data = {}
        for var in model.component_objects(pyo.Var, active=True):
            if var.name == "spilled_recaptured_vars":
                for (i_j), value in var.items():
                    if pyo.value(value) > 0:  # Only consider cases where passengers are actually spilled and recaptured
                        i, j = i_j.split('_')[1:]  # Split to get itinerary i and j
                        spilled_recaptured_data[(int(i), int(j))] = round(recapture_ratio * int(pyo.value(value)), 1)

        # Convert the data to a DataFrame
        spilled_recaptured_df = pd.DataFrame(list(spilled_recaptured_data.items()), columns=['Itinerary_Pair', 'Number of Passengers'])
        spilled_recaptured_df[['Spilling Itinerary', 'Recapturing Itinerary']] = pd.DataFrame(spilled_recaptured_df['Itinerary_Pair'].tolist(), index=spilled_recaptured_df.index)
        spilled_recaptured_df.drop(columns='Itinerary_Pair', inplace=True)
        spilled_recaptured_df = spilled_recaptured_df[['Spilling Itinerary', 'Recapturing Itinerary', 'Number of Passengers']]

        # Sort by Itinerary From for better presentation
        spilled_recaptured_df.sort_values(by=['Spilling Itinerary', 'Recapturing Itinerary'], inplace=True)

        # Debug print to check DataFrame
        print(spilled_recaptured_df)

        # Adding DataFrame to the session or directly to the template context
        request.session['spilled_recaptured_html'] = spilled_recaptured_df.to_html(classes=["table", "table-striped"], index=False)
        
        # Create individual dataframes for each fleet type
        for fleet_type in result_df['Fleet Type'].unique():
            if not pd.isna(fleet_type):  # Only process valid fleet type assignments
                fleet_df_name = f'fleet_type_{str(fleet_type)}_df'
                globals()[fleet_df_name] = result_df[result_df['Fleet Type'] == fleet_type]
                print(f'DataFrame {fleet_df_name} created with {len(globals()[fleet_df_name])} entries\n {globals()[fleet_df_name]} ')
                
        objective_value = pyo.value(model.obj)
        
        request.session['objective_value_IFAM'] = objective_value
        request.session['optimized_schedule_html'] = result_df.to_html(classes=["table", "table-striped"], index=False)
        
        fleet_dfs = {}
        for fleet_type in result_df['Fleet Type'].unique():
            if not fleet_type == 'None':
                if not pd.isna(fleet_type):  # Only process valid fleet type assignments
                    fleet_df_name = f'fleet {str(fleet_type)}'
                    fleet_dfs[fleet_df_name] = result_df[result_df['Fleet Type'] == fleet_type]
                    print(f'DataFrame {fleet_df_name} created with {len(fleet_dfs[fleet_df_name])} entries')
                    print(fleet_dfs[fleet_df_name], '\n')

        # If you want to print each DataFrame separately after creation
        fleet_files = []
        for df_name, df in fleet_dfs.items():
            print(f"Contents of {df_name}:")
            print(df, '\n')
            excel_filename_2 = save_for_routing_to_excel(df, df_name)
            fleet_files.append({
                'fleet_type': df_name,
                'file_name': excel_filename_2
            })
        
        # After preparing all dataframes
        excel_filename = save_ISD_dataframes_to_excel(result_df, ron_df, spilled_df, spilled_recaptured_df)


        return render(request, 'pages/fleetassignment.html', {
            'objective_value_IFAM': objective_value,
            'optimized_schedule_html': result_df.to_html(classes=["table", "table-striped"], index=False),
            'ron_schedule_html': ron_df.to_html(classes=["table", "table-striped"], index=False),  # Add this line
            'spilled_recaptured_html': spilled_recaptured_df.to_html(classes=["table", "table-striped"], index=False),
            'spilled_html': spilled_df.to_html(classes=["table", "table-striped"], index=False),
            'excel_file_url': excel_filename,  # This is the link to the file for downloading
            'fleet_files': fleet_files   # This is the link to the file for downloading
            })

    else:
        # The solver did not find an optimal solution
        request.session['infeasibility_result'] = "Solver did not converge to an optimal solution."
        infeasibility_result = request.session.get('infeasibility_result', [])
        context = {
            'infeasibility_result': infeasibility_result,
            # You may want to include forms or other context data needed to render 'routing.html'
        }
        return render(request, 'pages/fleetassignment.html', context)
    
def ISD_IFAM(request):
    # Load DataFrame from session
    flights_df_json = request.session.get('flights_df')
    flights_df = pd.read_json(StringIO(flights_df_json), orient='split')
    
    fleets_df_json = request.session.get('fleets_df')
    fleets_df = pd.read_json(StringIO(fleets_df_json), orient='split')
    
    itineraries_df_json = request.session.get('itineraries_df')
    itineraries_df = pd.read_json(StringIO(itineraries_df_json), orient='split')
    
    flight_column_indexes = json.loads(request.session['flight_column_indexes'])
    flight_no_col = flight_column_indexes.get('flight number')
    origin_col = flight_column_indexes.get('origin')
    departure_col = flight_column_indexes.get('departure')
    destination_col = flight_column_indexes.get('destination')
    arrival_col = flight_column_indexes.get('arrival')
    distance_col = flight_column_indexes.get('distance')
    duration_col = flight_column_indexes.get('duration')
    
    itinerary_column_indexes = json.loads(request.session['itinerary_column_indexes'])
    itinerary_no_col = itinerary_column_indexes.get('itinerary')
    demand_col = itinerary_column_indexes.get('demand')
    fare_col = itinerary_column_indexes.get('fare')
    flights_col = itinerary_column_indexes.get('flights')
    type_col = itinerary_column_indexes.get('type')
    
    # Debugging log
    logger.debug(f"itinerary_no_col: {itinerary_no_col}")
    
    station_list = np.unique(flights_df.iloc[:, origin_col].to_list())       # list of stations
    flights_list = flights_df.iloc[:, flight_no_col].astype(str).tolist()    #List of flights
    fleet_list = fleets_df['Fleet Type'].tolist()
    oc_list = fleets_df['Operating Cost Per Mile'].tolist()
    
    # ****************** Convert time to minutes **************** #
    dep_arriv = ClockToMinutes(flights_df, departure_col, arrival_col)
    dep = dep_arriv.get_departure_minutes()
    arriv = dep_arriv.get_arrival_minutes()

        
    # ****************** Generate Balance Nodes **************** #
    Nodes_df_instance = NodesGenerator(flights_df, station_list, flight_no_col, origin_col, destination_col, departure_col, arrival_col, dep, arriv)
    Nodes_df = Nodes_df_instance.get_nodes()
    
    # ****************** Recapture ratio bpr **************** #
    recapture_ratio = request.session.get('recapture_ratio')
    decrease_demand_percentage = request.session.get('decrease_demand_percentage')
    increase_demand_percentage = request.session.get('increase_demand_percentage')
    
    # ****************** Ground Arc Variable (Y) **************** #
    var_y_instance = VariableY(Nodes_df, station_list, fleet_list)
    var_y = var_y_instance.get_y()
    
    # ****************** Number of Available ACs **************** #
    Ne = {}
    for number_of_airplane in range(len(fleets_df)):
        Ne[fleets_df.iloc[number_of_airplane]['Fleet Type']] = fleets_df.iloc[number_of_airplane]['Number of Aircrafts']
        
    # ****************** Define FAM Model Sets **************** #
    model = ConcreteModel()
    model.setF = pyo.Set(initialize = flights_list)     # set of flights
    model.setE = pyo.Set(initialize = fleet_list)       # set of fleet
    model.setS = pyo.Set(initialize=station_list)       # set of stations


    # ****************** Define FAM Model Decision Variables **************** #
    model.x = pyo.Var(model.setF, model.setE, within=Binary, bounds=(0, None))  # This is two dimensional variable the first dimension indicates the flight number and the second one indicates the fleet number
    x = model.x

    model.RON = pyo.Var(model.setS, model.setE, within=Integers, bounds=(0, None)) # Second desicion variable (RONs,e) which is binary that represents represents the number of aircraft of fleet type e that remain overnight at station s
    RON = model.RON

    model.y = pyo.Var(var_y, within=Integers, bounds=(0, None)) # Defining the third decision variable(Y1_2,e) which is Integer that represents the number of aircrafts between nodes
    y = model.y


    # ****************** Calculate Operating Cost (C) **************** #
    flights_costs= flights_oeprating_costs(flights_df , fleets_df)
    cost_list= flights_costs.given_operating_cost(distance_col,oc_list)
    # cost_list = [30000,16600,15100,13500,15500,45000,57000,13500,42000,16600,15500,45000]  #######################TAKECARE##################

    # Creating the dictionary which has the flight,fleet as key equals to value from cost_list
    C_fe = {}
    cost_list_counter = 0
    for i in model.setF:
        for j in model.setE:
            C_fe[f'{i},{j}'] = cost_list[cost_list_counter]
            cost_list_counter += 1
            
    # ****************** Find Optional Flights **************** #
    cat = FlightsCategorization(flights_df, flight_no_col)
    optional_flights = cat.optional_flights
    non_optional_flights = cat.non_optional_flights
    
    print(f'optional flights\n {optional_flights} \n\n')
    print(f'flights_df\n {flights_df} \n\n')        
                
    
    # ****************** Define non/Optional Flight Sets**************** #
    model.setF_optional = pyo.Set(initialize = optional_flights)             # set of optional flights
    model.setF_non_optional = pyo.Set(initialize = non_optional_flights )    # set of non optional flights
    
    # ****************** Find Optional Itineraries **************** #
    optional_itineraries=[]
    for idx, itn in itineraries_df.iterrows():
        for opt_flight in optional_flights:
            if str(opt_flight) in (str(itn[flights_col]).split(", ")) and itn[itinerary_no_col] not in optional_itineraries :
                optional_itineraries.append(itn[itinerary_no_col])
                
    print(f'optional itineraries\n {optional_itineraries} \n\n')     
                
    # ****************** Define non/Optional Itinerary Sets**************** #
    model.setp = pyo.RangeSet(len(itineraries_df))                            # set of itenraries
    model.setp_optional=pyo.Set(initialize=optional_itineraries)                # set of optional itenraries
    

    # ****************** Generate Zq Decision Variable**************** #
    def optional_df(itineraries_df, optional_itineraries, itinerary_no_col):
        # Iterate over each row of the DataFrame
        print(itinerary_no_col)
        for idx in range(len(itineraries_df)):
            # Check if the itinerary is in the list of optional itineraries
            if itineraries_df.iloc[idx, itinerary_no_col] in optional_itineraries:
                # Set the 'Optional' column to 1 for this row
                itineraries_df.at[idx, 'Optional'] = 1
                
        itineraries_df.fillna(0,inplace = True)

        return itineraries_df
            
    optional_dfs = optional_df(itineraries_df, optional_itineraries, itinerary_no_col)     
    var_z = VariableZ(itineraries_df, itinerary_no_col)
    var_z = var_z.get_z()
    if var_z is not None:
        model.z = pyo.Var(var_z, within = Binary, bounds = (0,1))

    # ****************** Define spilled passenger from itinerary p (tp) **************** #
    itineraries_demand_list =itineraries_df.iloc[:, demand_col].tolist() # Get column of demand from itenraries dataframe and convert to list
    model.t_spilled = pyo.Var(model.setp, within=pyo.Integers, bounds=lambda model, i: (0, itineraries_demand_list[i-1]))
    t_spilled=model.t_spilled
    
    # ****************** Define spilled passenger from itinerary p and recaptured by itinerary r (tpr) **************** #
    data1=spilled_and_captured_variables(flights_df)
    itineraries_df=spilled_and_captured_variables.Itinraries_df_simplify(data1,itineraries_df,itinerary_no_col, flights_col, flight_no_col, origin_col, destination_col,type_col)

    itineraries_df.iloc[:, itinerary_no_col] = itineraries_df.iloc[:, itinerary_no_col].astype('int64')
    spilled_recaptured_vars=spilled_and_captured_variables.spill_recaptured_variables_list(data1, itineraries_df, itinerary_no_col)
    #print(f"Variable t_p_r:\n{spilled_recaptured_vars}")

    model.spilled_recaptured_vars = pyo.Var(spilled_recaptured_vars, within=Integers, bounds=(0, None))
    spilled_recaptured_vars = model.spilled_recaptured_vars


    # ****************** Add Market Column in Itinerary dataframe **************** #
    itineraries_df['market'] = itineraries_df.apply(lambda row: [row['From'], row['To']], axis=1)

    # Create a list of lists 'airline_markets'
    airline_markets_for_each_itenrary = itineraries_df['market'].tolist() 
    # getting the unique markets
    ailine_market=[]

    for market in airline_markets_for_each_itenrary:
        if market not in ailine_market:
            ailine_market.append(market)
    #print(f'Itinerary Data Frame:\n{itineraries_df}\n')


    # ****************** Define Demand correction variable Delta Dqp **************** #
    demand_correction = DemandCorrection(itineraries_df, increase_demand_percentage, decrease_demand_percentage, optional_itineraries, optional_flights, itinerary_no_col, flights_col, demand_col)
    demand_correction_factor_df = demand_correction.get_demand_correction_df()
    #print(f'Demand Correction Factor:\n{demand_correction_factor_df}\n')

    #__C__Operating costs
    C_Operating_cost=sum(C_fe[f"{f},{e}"] * model.x[f, e] for f in model.setF for e in model.setE)
    #print(f'Operating Cost (C):\n{C_Operating_cost}\n')
    
            
    # ****************** Calculate Unconstrained Revenue (R) **************** #
    R_Unconstrained_Revenue=sum(itineraries_df.iloc[idx, demand_col] * itineraries_df.iloc[idx, fare_col] for idx in range(len(itineraries_df)))
    #print(f'Unconstrained Revenue (R):\n{R_Unconstrained_Revenue}\n')


    # ****************** Calculate Spill Cost (S) **************** #
    S_Spill_Cost=sum(model.spilled_recaptured_vars[t_p_r] * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[1])).values , fare_col].values[0] for t_p_r in spilled_recaptured_vars)

    #print(f'Spill Cost (S):\n{S_Spill_Cost}\n')


    # ****************** Calculate Recaptured Revenue (M) **************** #
    M_Recaptured_Revenue=sum(model.spilled_recaptured_vars[t_p_r] * recapture_ratio * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[2])).values , fare_col].values[0] 
                if t_p_r.split('_')[1] == str(r) and int(t_p_r.split('_')[2]) != len(itineraries_df)+1  
                else 0 
                for t_p_r in spilled_recaptured_vars   
                for r in model.setp.data())
    #print(f'Recaptured Revenue (M):\n{M_Recaptured_Revenue}\n')


    # ****************** Calculate Unconstrained Revenue Loss (Delta R) **************** #
    optional_itineraries = np.array(optional_itineraries, dtype='int64')
    DeltaR_Uncontrained_Revenue_Loss = sum(
        (
            (itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , demand_col].iloc[0] *
            itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , fare_col].iloc[0])
            - sum(
                (demand_correction_factor_df.loc[demand_correction_factor_df['name'] == f'D_{opt_iten}_{iten.iloc[itinerary_no_col]}', 'value'].iloc[0] *
                itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == iten.iloc[itinerary_no_col]).values , fare_col].iloc[0])
                if f'D_{opt_iten}_{iten.iloc[itinerary_no_col]}' in demand_correction_factor_df['name'].tolist()
                else 0
                for idx, iten in itineraries_df.iterrows()
            )
        ) *
        (1 - model.z[f'{opt_iten}'])
        for opt_iten in optional_itineraries
    )

    #print(f'Unconstrained Revenue Loss (Delta R):\n{DeltaR_Uncontrained_Revenue_Loss}\n')


    # ****************** Objective Function **************** #
    model.obj = pyo.Objective(
        expr=(-C_Operating_cost - S_Spill_Cost + R_Unconstrained_Revenue + M_Recaptured_Revenue - DeltaR_Uncontrained_Revenue_Loss),
        sense=pyo.maximize
    )


    # ****************** Coverage Constraint **************** #
    model.coverage = ConstraintList()
    for f in model.setF:
        if f in model.setF_optional:
            model.coverage.add(expr = sum([x[f,e] for e in model.setE ]) <= 1)
        elif f in model.setF_non_optional:
            model.coverage.add(expr = sum([x[f,e] for e in model.setE ]) == 1)
            

    # ****************** Resources Constraint **************** #
    model.resources = ConstraintList()
    for e in model.setE:
        model.resources.add(expr=sum([RON[station, e]for station in model.setS]) <= Ne[e])
        
        
    # ****************** Balance Constraint **************** #
    model.balance = ConstraintList()
    for fleet in model.setE:
        for node in Nodes_df.index:

            city = Nodes_df.iloc[node-1]['city']
            city_nodes_df = Nodes_df[Nodes_df['city'] == city]

            first_node = city_nodes_df.index.values.min()
            last_node = city_nodes_df.index.values.max()

            y_sum = 0

    # Assuming 'first_node', 'last_node' are defined
            if first_node != last_node:
                # Define the constraint using Pyomo syntax
                y_sum = (sum([model.y[var_name] if (var_name.replace(",", "_").split('_')[1] == str(node)) & ((str(fleet)) in var_name) else 0 for var_name in var_y])) +\
                    (sum([-1*model.y[var_name] if (var_name.replace(",", "_").split('_')[0] == str(node)) &
                    ((str(fleet)) in var_name) else 0 for var_name in var_y]))

            model.balance.add(expr=y_sum +
                            sum(flight[1] * model.x[str(flight[0]), fleet]
                                for flight in Nodes_df.iloc[node-1]['flights'])
                            + (RON[city, fleet] if node == first_node and node != last_node else -1 *
                                model.RON[city, fleet] if node == last_node and node != first_node else 0)
                            == 0)
            

    # ****************** Flight Interaction Constraint **************** # 
    model.flight_interaction = ConstraintList()


    for idx1, flight in flights_df.iterrows():

        # Spilled passengers
        spilled_passengers = sum(
            sum(
                model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[1] == str(itineraries_df.iloc[idx, itinerary_no_col]) else 0
                for t_p_r in spilled_recaptured_vars
            )
            if str(flight.iloc[flight_no_col]) in (str(itineraries_df.iloc[idx, flights_col]).split(", "))
            else 0
            for idx, itn in itineraries_df.iterrows()   
        )
        
        # Recaptured passengers
        recaptured_passengers = sum(
            sum(
                recapture_ratio * model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[2] == str(itineraries_df.iloc[idx, itinerary_no_col]) else 0
                for t_p_r in spilled_recaptured_vars
            )
            if str(flight.iloc[flight_no_col]) in (str(itineraries_df.iloc[idx, flights_col]).split(", "))
            else 0
            for idx, itn in itineraries_df.iterrows()   
        )
        
        # Flight unconstrained demand
        flight_unconstrained_demand = 0
        for idx, itn in itineraries_df.iterrows():
            if str(flight.iloc[flight_no_col]) in (str(itn.iloc[flights_col]).split(", ")):
                flight_unconstrained_demand += itn.iloc[demand_col]

        # Flight available seats
        flight_seats_available = sum(
            (model.x[str(flight.iloc[flight_no_col]), fleet.iloc[0]]) * fleet.iloc[2] for idx, fleet in fleets_df.iterrows()  ########### TAKE CARE FLEETS Index##############
        )
        
        flight_demand_correction = sum(
            sum(
                (
                    (demand_correction_factor_df[demand_correction_factor_df['name'] == str(f'D_{opt_iten}_{itn.iloc[itinerary_no_col]}')]['value'].iloc[0]) *
                    (1 - model.z[f'{opt_iten}'])
                )
                if str(f'D_{opt_iten}_{itn.iloc[itinerary_no_col]}') in demand_correction_factor_df['name'].values
                else 0
                for opt_iten in optional_itineraries
            )
            if str(flight.iloc[flight_no_col]) in (str(itn.iloc[flights_col]).split(", "))
            else 0
            for idx, itn in itineraries_df.iterrows()
        )
        
        #print(f'Interaction constraind Demand correction part equation{idx1 + 1}:\n{flight_demand_correction}\n')

        model.flight_interaction.add(expr= spilled_passengers - recaptured_passengers >= flight_unconstrained_demand + flight_demand_correction - flight_seats_available)
            
    # ****************** Spill-Recapture & Demand Constraints **************** #
    model.demand = ConstraintList()
    model.spill_recapture=ConstraintList()
    for itn in range(len(itineraries_df)):  
        
        itenrary=itineraries_df.iloc[itn, itinerary_no_col]
        t_p_r__sum = sum(model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[1] == str(itenrary) else 0 for t_p_r in spilled_recaptured_vars) # from I_FAM
        
        
        demand_correction_factor_sum = sum( 
                                        (demand_correction_factor_df[demand_correction_factor_df['name'] == str(f'D_{opt_iten}_{itenrary}')]['value'].iloc[0])
                                        * (1-model.z[f'{opt_iten}'])
                                        if str(f'D_{opt_iten}_{itenrary}') in demand_correction_factor_df['name'].values else 0
                                        for opt_iten in optional_itineraries)
        
        model.demand.add(expr= t_p_r__sum - itineraries_df.iloc[itn, demand_col] -  demand_correction_factor_sum <= 0) # Demand Constraints
        
        model.spill_recapture.add(expr=t_p_r__sum == model.t_spilled[itenrary])  # Spill_recapture Constraints
        
    # ****************** Ensure Zq = 0 Constraint **************** #    
    model.Ensure_Z_is_zero = ConstraintList()
    

    for opt_iten in optional_itineraries:
        
        opt_iten_flights=str((itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , flights_col].iloc[0])).split(", ")

        for flight in opt_iten_flights:
            
            model.Ensure_Z_is_zero.add(expr=   model.z[f'{opt_iten}'] <= sum([x[flight,e] for e in model.setE ]  ))
            
            
    # ****************** Ensure Zq = 1 Constraint **************** # 
    model.Ensure_Z_is_ONE = ConstraintList()
    for opt_iten in optional_itineraries:
        
        opt_iten_flights=str((itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , flights_col].iloc[0])).split(", ")
        N_q=len(opt_iten_flights)  # Number of flights in optional itenrary
        
        model.Ensure_Z_is_ONE.add(expr = model.z[f'{opt_iten}'] - sum([x[flight,e] for e in model.setE for flight in opt_iten_flights]  ) >= 1-N_q)
            

    # ****************** Solving **************** # 
    opt = SolverFactory('gurobi')
    #print('\n\nSolving please wait\n\n')
    problem_results = opt.solve(model)

    # Function to convert minutes to hh:mm:ss format
    def minutes_to_time(minutes):
        hours = int(minutes // 60)
        minutes = int(minutes % 60)
        return '{:02d}:{:02d}:00'.format(hours, minutes)

    # Convert DepartureTime and ArrivalTime columns
    flights_df.iloc[:, departure_col] = flights_df.iloc[:, departure_col].apply(minutes_to_time)
    flights_df.iloc[:, arrival_col] = flights_df.iloc[:, arrival_col].apply(minutes_to_time)

    if problem_results.solver.termination_condition == TerminationCondition.optimal:
        # The solver was successful, and the optimal solution is available
        model.pprint()
    
        # Create a dictionary to store fleet type assignments for each flight based on Pyomo variable x
        flight_assignments = {}
        operate_flight = {}
        for i in model.component_objects(pyo.Var, active=True):  # Iterate over all Pyomo variables
            print(i)
            if i.name == "x":  # Ensure to process only the relevant variable
                for idx in i:
                    print(f'{i[idx]} = {i[idx].value}')  # Debug print
                    flight_number, fleet_type = idx
                    if pyo.value(i[idx]) == 1:  # Check if this assignment is selected
                        # Ensure that flight_number is an integer if it's stored as such in flights_df
                        flight_assignments[int(flight_number)] = fleet_type
            if i.name == "z":  # Ensure to process only the relevant variable
                for idx in i:
                    print(f'{i[idx]} = {i[idx].value}')  # Debug print
                    flight_number= idx
                    print(f'z flight number\n: {flight_number}')
                    if pyo.value(i[idx]) == 1:  # Check if this assignment is selected
                        # Ensure that flight_number is an integer if it's stored as such in flights_df
                        operate_flight[int(flight_number)] = 'Yes'
                    else:
                        operate_flight[int(flight_number)] = 'No'
        
        # Now, ensure all flights are accounted for in 'operate_flight'
        for flight_number in flights_df.iloc[:, flight_no_col]:
            if flight_number not in operate_flight:
                operate_flight[flight_number] = 'Yes'  # Default to 'Yes' if not found

        # Debug print to check the content of the flight_assignments dictionary
        print("Flight Assignments:", flight_assignments)

        # Map fleet types to flight numbers ensuring the index is integer if required
        flights_df['Fleet Type'] = flights_df.iloc[:, flight_no_col].map(flight_assignments)  # Adjust FlightNumber if it's not the correct column name
        fleet_type_col = flights_df.columns.get_loc('Fleet Type')
        
        flights_df['Operate Flight'] = flights_df.iloc[:, flight_no_col].map(operate_flight)  # Adjust FlightNumber if it's not the correct column name
        operate_flight_col = flights_df.columns.get_loc('Operate Flight')
        
        print(f'operate_flight:\n {operate_flight}')
        print(f'flights_df Operate Flight:\n {flights_df['Operate Flight']}')
        
        
        # Select relevant columns and rename them to match the required structure
        result_df = flights_df.iloc[:, [flight_no_col, origin_col, departure_col, destination_col, arrival_col, distance_col, duration_col, fleet_type_col, operate_flight_col]]
        result_df.columns = ['Flight Number', 'Origin', 'Departure', 'Destination', 'Arrival', 'Distance', 'Duration', 'Fleet Type', 'Operate Flight']
        result_df['Fleet Type'].fillna(value='None',inplace=True)
        print(result_df)
        
        # After defining operate_flight and before creating result_df
        ron_aggregate = {}  # Dictionary to hold RON data

        # Extract RON data from the model
        for ron_var in model.component_objects(pyo.Var, active=True):
            if ron_var.name == "RON":
                for (station, fleet_type), value in ron_var.items():
                    if pyo.value(value) >= 0:  # Only consider positive RON values
                        if (station, fleet_type) not in ron_aggregate:
                            ron_aggregate[(station, fleet_type)] = 0
                        ron_aggregate[(station, fleet_type)] += int(pyo.value(value))

        # Convert RON data to a DataFrame for easier display
        ron_df = pd.DataFrame(list(ron_aggregate.items()), columns=['Station_Fleet', 'Number of Aircraft Staying Overnight'])
        ron_df[['Station', 'Fleet Type']] = pd.DataFrame(ron_df['Station_Fleet'].tolist(), index=ron_df.index)
        ron_df.drop(columns='Station_Fleet', inplace=True)

        # Reorder columns if necessary
        ron_df = ron_df[['Station', 'Fleet Type', 'Number of Aircraft Staying Overnight']]

        # Sort the DataFrame for better presentation
        ron_df.sort_values(by=['Station', 'Fleet Type'], inplace=True)

        # Debug print to check RON DataFrame
        print(ron_df)

        # Add the RON DataFrame to the session or directly to the template context
        request.session['ron_schedule_html'] = ron_df.to_html(classes=["table", "table-striped"], index=False)
        
        
        # Extracting data from t_spilled
        spilled_data = {}
        for var in model.component_objects(pyo.Var, active=True):
            if var.name == "t_spilled":
                for (i_j), value in var.items():
                    if pyo.value(value) > 0:  # Only consider cases where passengers are actually spilled and recaptured
                        i = i_j  # Split to get itinerary i and j
                        spilled_data[(int(i))] = int(pyo.value(value))

        # Convert the data to a DataFrame
        spilled_df = pd.DataFrame(list(spilled_data.items()), columns=['Itinerary', 'Number of Passengers'])
        spilled_df[['Spilling Itinerary']] = pd.DataFrame(spilled_df['Itinerary'].tolist(), index=spilled_df.index)
        spilled_df.drop(columns='Itinerary', inplace=True)
        spilled_df = spilled_df[['Spilling Itinerary', 'Number of Passengers']]

        # Sort by Itinerary From for better presentation
        spilled_df.sort_values(by=['Spilling Itinerary'], inplace=True)

        # Debug print to check DataFrame
        print(spilled_df)

        # Adding DataFrame to the session or directly to the template context
        request.session['spilled_html'] = spilled_df.to_html(classes=["table", "table-striped"], index=False)
        
        # Extracting data from spilled_recaptured_vars
        spilled_recaptured_data = {}
        for var in model.component_objects(pyo.Var, active=True):
            if var.name == "spilled_recaptured_vars":
                for (i_j), value in var.items():
                    if pyo.value(value) > 0:  # Only consider cases where passengers are actually spilled and recaptured
                        i, j = i_j.split('_')[1:]  # Split to get itinerary i and j
                        spilled_recaptured_data[(int(i), int(j))] = round(recapture_ratio * int(pyo.value(value)), 1)

        # Convert the data to a DataFrame
        spilled_recaptured_df = pd.DataFrame(list(spilled_recaptured_data.items()), columns=['Itinerary_Pair', 'Number of Passengers'])
        spilled_recaptured_df[['Spilling Itinerary', 'Recapturing Itinerary']] = pd.DataFrame(spilled_recaptured_df['Itinerary_Pair'].tolist(), index=spilled_recaptured_df.index)
        spilled_recaptured_df.drop(columns='Itinerary_Pair', inplace=True)
        spilled_recaptured_df = spilled_recaptured_df[['Spilling Itinerary', 'Recapturing Itinerary', 'Number of Passengers']]

        # Sort by Itinerary From for better presentation
        spilled_recaptured_df.sort_values(by=['Spilling Itinerary', 'Recapturing Itinerary'], inplace=True)

        # Debug print to check DataFrame
        print(spilled_recaptured_df)

        # Adding DataFrame to the session or directly to the template context
        request.session['spilled_recaptured_html'] = spilled_recaptured_df.to_html(classes=["table", "table-striped"], index=False)
        
        # Create individual dataframes for each fleet type
        fleet_dfs = {}
        for fleet_type in result_df['Fleet Type'].unique():
            if not fleet_type == 'None':
                if not pd.isna(fleet_type):  # Only process valid fleet type assignments
                    fleet_df_name = f'fleet {str(fleet_type)}'
                    fleet_dfs[fleet_df_name] = result_df[result_df['Fleet Type'] == fleet_type]
                    print(f'DataFrame {fleet_df_name} created with {len(fleet_dfs[fleet_df_name])} entries')
                    print(fleet_dfs[fleet_df_name], '\n')
                    
        # If you want to print each DataFrame separately after creation
        fleet_files = []
        for df_name, df in fleet_dfs.items():
            print(f"Contents of {df_name}:")
            print(df, '\n')
            excel_filename_2 = save_for_routing_to_excel(df, df_name)
            fleet_files.append({
                'fleet_type': df_name,
                'file_name': excel_filename_2
            })
                             
        objective_value = pyo.value(model.obj)
        request.session['objective_value_ISD_IFAM'] = objective_value
        request.session['optimized_schedule_html'] = result_df.to_html(classes=["table", "table-striped"], index=False)
        
        
        # After preparing all dataframes
        excel_filename = save_ISD_dataframes_to_excel(result_df, ron_df, spilled_df, spilled_recaptured_df)

        return render(request, 'pages/fleetassignment.html', {
            'objective_value_ISD_IFAM': objective_value,
            'optimized_schedule_html': result_df.to_html(classes=["table", "table-striped"], index=False),
            'ron_schedule_html': ron_df.to_html(classes=["table", "table-striped"], index=False),  # Add this line
            'spilled_recaptured_html': spilled_recaptured_df.to_html(classes=["table", "table-striped"], index=False),
            'spilled_html': spilled_df.to_html(classes=["table", "table-striped"], index=False),
            'excel_file_url': excel_filename,  # This is the link to the file for downloading
            'fleet_files': fleet_files   # This is the link to the file for downloading
            })

    else:
        # The solver did not find an optimal solution
        request.session['infeasibility_result'] = "Solver did not converge to an optimal solution."
        infeasibility_result = request.session.get('infeasibility_result', [])
        context = {
            'infeasibility_result': infeasibility_result,
            # You may want to include forms or other context data needed to render 'routing.html'
        }
        return render(request, 'pages/fleetassignment.html', context)
       
def save_ISD_dataframes_to_excel(result_df, ron_df, spilled_df, spilled_recaptured_df):
    filename = 'Fleet_Assignment_Report.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        result_df.to_excel(writer, sheet_name='Optimized Schedule', index=False)
        ron_df.to_excel(writer, sheet_name='RON Details', index=False)
        spilled_df.to_excel(writer, sheet_name='Spillage Details', index=False)
        spilled_recaptured_df.to_excel(writer, sheet_name='Spill and Recapture Details', index=False)
    
    return filename

def download_excel(request):
    filename = 'Fleet_Assignment_Report.xlsx'
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
    
def save_for_routing_to_excel(result_df, fleet_type):
    filename_2 = f'{fleet_type} Routing Model.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename_2)
    
    logger.debug(f"Saving Excel file at: {filepath}")

    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT)

    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        result_df.to_excel(writer, sheet_name= f'{fleet_type} Schedule', index=False)
    
    return filename_2

def download_for_routing_excel(request, fleet_type):
    filename_2 = f'{fleet_type} Routing Model.xlsx'
    filepath = os.path.join(settings.MEDIA_ROOT, filename_2)

    try:
        if os.path.exists(filepath):
            # Open the file without a context manager to manually control when it is closed
            excel_file = open(filepath, 'rb')
            response = FileResponse(excel_file, as_attachment=True, filename=filename_2)

            # Add cleanup for the file on the response close
            response.file_to_close = excel_file

            return response
        else:
            return HttpResponseNotFound('The requested Excel file was not found on the server.')
    except Exception as e:
        # Log the error for debugging
        print(e)
        return HttpResponseServerError('A server error occurred. Please contact the administrator.')

flights_sample_df = pd.DataFrame({
    'Flight Number': [123, 124],
    'Origin': ['ABC', 'EFG'],
    'Departure': ['10:00', '14:00'],
    'Destination': ['EFG', 'XYZ'],
    'Arrival': ['12:00', '16:00'],
    'Distance': [500, 1000],
    'Duration': [2.5, 3]
})

def download_flights_sample_excel(request):
    """View to handle downloading the flights sample as an Excel file."""
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Flight_Data_Excel_Sample.xlsx"'
    
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        flights_sample_df.to_excel(writer, index=False)
    
    return response

def preview_flights_sample(request):
    """View to handle AJAX request for previewing the flights sample on a webpage."""
    html_table = flights_sample_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})

def download_itineraries_sample_excel(request):
    # Define a DataFrame with the necessary columns
    itineraries_sample_df = pd.DataFrame(columns=[
        'Itinerary Number', 'Demand', 'Fare', 'Flights', 'Type'
    ])
    
    itineraries_sample_df.loc[0] = [1, 100, 250, '123', 'non stop']
    itineraries_sample_df.loc[1] = [2, 200, 400, '124', 'non stop']
    itineraries_sample_df.loc[2] = [3, 350, 600, '123, 124', 'single stop']


    # Define the Excel response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Download_Itinerary_Data_Excel_Sample.xlsx"'

    # Write the empty DataFrame to the Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        itineraries_sample_df.to_excel(writer, index=False)

    return response

def preview_itineraries_sample(request):
    # Sample data for itineraries
    itineraries_sample_df = pd.DataFrame({
        'Itinerary Number': [1, 2, 3],
        'Demand': [100, 200, 350],
        'Fare': [250, 400, 600],
        'Flights': ['123', '124', '123, 124'],
        'Type': ['non stop', 'non stop', 'single stop']
    })

    # Convert DataFrame to HTML table
    html_table = itineraries_sample_df.to_html(classes=["table", "table-striped"], index=False)
    return JsonResponse({'html_table': html_table})