import pandas as pd
import re
from io import BytesIO
import io
from datetime import datetime, timedelta, time
import numpy as np
import math
from pyomo.util.infeasible import log_infeasible_constraints
import itertools
import pyomo.environ as pyo 
from pyomo.environ import *
from pyomo.opt import SolverFactory

class SyncReadExcel:
    def __init__(self, file_content=None, dtype=str, file_name=None):
        """
        Initializes the SyncReadExcel object with file content.

        Parameters:
        - file_content: bytes, required, binary content of the Excel file.
        - dtype: data type to use for the returned DataFrame columns, default is str.
        - file_name: str, optional, name of the file including the extension.
        """
        self.file_content = file_content
        self.dtype = dtype
        self.file_name = file_name
        self.df = None  # Will store the DataFrame after reading

    def file_type(self):
        """
        Checks if the file is an Excel file based on its extension.
        """
        if self.file_name:
            if self.file_name.endswith(('.xls', '.xlsx', '.xlsm', '.xlsb')):
                return None
            return self.file_name.split('.')[-1]
        return None


    def read_data(self):
        """
        Reads the Excel file from the binary content and stores the data in the DataFrame.
        """
        file_type = self.file_type()
        if self.file_content and not file_type:
            try:
                self.df = pd.read_excel(io.BytesIO(self.file_content), dtype=self.dtype)
            except Exception as e:
                raise ValueError(f"Failed to read Excel file: {e}")
        elif file_type:
            raise ValueError(f"You have uploaded a {file_type} file, please upload the data in Excel format.")
        else:
            raise ValueError("File content must be provided.")
        
    def get_dataframe(self):
        """
        Returns the DataFrame containing the data read from the Excel file.
        """
        return self.df

    def get_data_list(self):
        """
        Converts the DataFrame into a list of lists and returns it.
        Each sublist represents a row from the Excel file.
        """
        if self.df is not None and not self.df.empty:
            return self.df.values.tolist()
        else:
            return []

#################################################################################################################

class FlightColumnIndex:
    def __init__(self, flights_pd):
        self.flights_pd = flights_pd
        self.column_name_mappings = {
            "flight number": ['Flight','FLIGHTS','FLIGHTNO','FLIGHT NO','flightno','flight no','Flight No' 'flight', 'Flights', 'flights', 'Flight Number', 'flight number', 'FlightNumber', 'flightnumber'],
            "origin": ['Origin', 'origin', 'FROM', 'from', 'From'],
            "departure": ['Departure','DEPARTURE', 'departure', 'dep', 'departuretime', 'DepartureTime', 'departure time'],
            "destination": ['Destination', 'destination', 'DESTINATION', 'dest', 'TO', 'to', 'To', 'Dest'],
            "arrival": ['Arrival','ARRIVAL', 'arrival', 'arr', 'arrivaltime', 'ArrivalTime', 'arrival time'],
            "distance": ['Distance', 'distance', 'miles', 'mile', 'Distances', 'DISTANCE', 'distances', 'MILE', 'MILES'],
            "duration": ['duration', 'DURATION', 'Duration', 'Durations', 'Time', 'Times', 'TIME', 'time', 'DURATIONs', 'durations', 'flight hours', 'flight hour', 'Flight Hours', 'Flight hours', 'Flight Hour', 'FLIGHT HOUR', 'FLIGHT HOURS', 'Hours', 'HOURS', 'Hour', 'hour'],
        }
        self.columns = {key: None for key in self.column_name_mappings}
        self.missing_columns = []  # List to store names of missing columns
        self.find_and_validate_columns()
        
    def validate_column_data(self, column_index, column_type):
        """
        Validates the data in a column based on its expected type.

        Parameters:
        - column_index: int, the index of the column to validate.
        - column_type: str, the type of column being validated.

        Returns:
        - bool: True if the data is valid, False otherwise.
        - str: A message indicating the status of the validation.
        """
        sample_data = self.flights_pd.iloc[:, column_index].dropna().head(10)
        
        if column_type == 'flight number':
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'flight number' column does not match expected numeric format: {sample_data.tolist()}"
        elif column_type in ['origin', 'destination']:
            if not all(self.is_valid_alphabetic(value) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected alphabetic format: {sample_data.tolist()}"
        elif column_type in ['departure', 'arrival']:
            if not all(self.is_valid_time_format(str(value)) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected time format (HH:MM): {sample_data.tolist()}"
        elif column_type in ['distance']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'distance' column does not match expected numeric format: {sample_data.tolist()}"
        elif column_type in ['duration']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'flight duration' column does not match expected numeric format: {sample_data.tolist()}"

        return True, "Data format is correct."

    def find_and_validate_columns(self):
        for column_type, potential_names in self.column_name_mappings.items():
            column_index = self.find_column_index_by_potential_names(column_type)
            if column_index is not None:
                self.columns[column_type] = column_index
            else:
                # Instead of raising an error, add the missing column type to the list
                self.missing_columns.append(column_type)

    def find_column_index_by_potential_names(self, column_type):
        potential_names = self.column_name_mappings[column_type]
        columns = self.flights_pd.columns
        for col_name in potential_names:
            if col_name in columns:
                return columns.get_loc(col_name)
        return None
    
    def get_column_indexes(self):
        """Return the column indexes found.

        Returns:
        - dict: A dictionary with column types as keys and their indexes as values.
        """
        return self.columns

    def is_valid_numeric(self, data):
        """Check if data is numeric."""
        try:
            float(data)  # Attempt to convert to float to handle numbers with decimals
            return True
        except ValueError:
            return False

    def is_valid_alphabetic(self, data):
        """Check if data is alphabetic."""
        if isinstance(data, str):
            return data.isalpha()

    def is_valid_time_format(self, data):
        """Check if data is in a valid time format (HH:MM)."""
        return bool(re.match(r'\d{2}:\d{2}', data))
    
    def get_flight_number_column(self):
        """Get the column index for flight number."""
        return self.columns["flight number"]

    def get_origin_column(self):
        """Get the column index for origin."""
        return self.columns["origin"]

    def get_departure_column(self):
        """Get the column index for departure."""
        return self.columns["departure"]

    def get_destination_column(self):
        """Get the column index for destination."""
        return self.columns["destination"]

    def get_arrival_column(self):
        """Get the column index for arrival."""
        return self.columns["arrival"]
    
    def get_distance_column(self):
        """Get the column index for distance."""
        return self.columns["distance"]

    def get_duration_column(self):
        """Get the column index for duration."""
        return self.columns["duration"]
    
##########################################################################################################          
    
class ItinColumnIndex:
    def __init__(self, itinerary_df):
        self.itinerary_df = itinerary_df
        self.column_name_mappings = {
            "itinerary": ['Itinerary', 'itinerary', 'ITINERARY', 'route', 'Route', 'ROUTE', 'path', 'Path', 'PATH'],
            "demand": ['Demand', 'demand', 'DEMAND', 'requests', 'Requests', 'REQUESTS', 'bookings', 'Bookings', 'BOOKINGS'],
            "fare": ['Fare', 'fare', 'FARE', 'price', 'Price', 'PRICE', 'cost', 'Cost', 'COST', 'charge', 'Charge', 'CHARGE'],
            "flights": ['Flights', 'flights', 'FLIGHTS', 'Flight Number', 'flight number', 'FlightNumber', 'flightnumber', 'FLIGHTNUMBER', 'Flights Number', 'flights number', 'FlightsNumber', 'flightsnumber'],
            "type": ['Type', 'type', 'TYPE', 'category', 'Category', 'CATEGORY', 'class', 'Class', 'CLASS'],
        }
        self.columns = {key: None for key in self.column_name_mappings}
        self.missing_columns = []  # List to store names of missing columns
        self.find_and_validate_columns()
        
    def validate_column_data(self, column_index, column_type):
        """
        Validates the data in a column based on its expected type.

        Parameters:
        - column_index: int, the index of the column to validate.
        - column_type: str, the type of column being validated.

        Returns:
        - bool: True if the data is valid, False otherwise.
        - str: A message indicating the status of the validation.
        """
        sample_data = self.itinerary_df.iloc[:, column_index].dropna().head(10)
        
        if column_type == ['itinerary']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'itinerary number' column does not match expected numeric format: {sample_data.tolist()}"
        elif column_type in ['demand']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'demand' column does not match expected numeric format: {sample_data.tolist()}"
        elif column_type in ['fare']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for 'fare' column does not match expected numeric format: {sample_data.tolist()}"        
        elif column_type in ['flights', 'type']:
            if not all(self.is_valid_string(value) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected alphabetic format: {sample_data.tolist()}"
        
        return True, "Data format is correct."

    def find_and_validate_columns(self):
        for column_type, potential_names in self.column_name_mappings.items():
            column_index = self.find_column_index_by_potential_names(column_type)
            if column_index is not None:
                self.columns[column_type] = column_index
            else:
                # Instead of raising an error, add the missing column type to the list
                self.missing_columns.append(column_type)

    def find_column_index_by_potential_names(self, column_type):
        potential_names = self.column_name_mappings[column_type]
        columns = self.itinerary_df.columns
        for col_name in potential_names:
            if col_name in columns:
                return columns.get_loc(col_name)
        return None
    
    def get_column_indexes(self):
        """Return the column indexes found.

        Returns:
        - dict: A dictionary with column types as keys and their indexes as values.
        """
        return self.columns

    def is_valid_numeric(self, data):
        """Check if data is numeric."""
        try:
            float(data)  # Attempt to convert to float to handle numbers with decimals
            return True
        except ValueError:
            return False
    
    def is_valid_string(self, data):
        """Check if data is string."""
        try:
            str(data)  # Attempt to convert to float to handle numbers with decimals
            return True
        except ValueError:
            return False

    def is_valid_alphabetic(self, data):
        """Check if data is alphabetic."""
        if isinstance(data, str):
            return data.isalpha()

    def is_valid_time_format(self, data):
        """Check if data is in a valid time format (HH:MM)."""
        return bool(re.match(r'\d{2}:\d{2}', data))
    
    def get_itinerary_number_column(self):
        """Get the column index for itinerary number."""
        return self.columns["itinerary"]

    def get_demand_column(self):
        """Get the column index for demand."""
        return self.columns["demand"]

    def get_fare_column(self):
        """Get the column index for fare."""
        return self.columns["fare"]

    def get_flights_column(self):
        """Get the column index for flights."""
        return self.columns["flights"]

    def get_type_column(self):
        """Get the column index for type."""
        return self.columns["type"]

##########################################################################################################          
 

class ClockToMinutes:
    def __init__(self, flights_pd, departure_col, arrival_col):
        self.flights_pd = flights_pd
        self.dep_col = departure_col
        self.arriv_col = arrival_col
        
        # Convert times to minutes for the entire DataFrame
        self.flights_pd['departure_minutes'] = self.flights_pd.iloc[:, self.dep_col].apply(self.convert_to_minutes)
        self.flights_pd['arrival_minutes'] = self.flights_pd.iloc[:, self.arriv_col].apply(self.convert_to_minutes)

    @staticmethod
    def convert_to_minutes(time_val):
        """
        Convert a time value to minutes.

        Args:
        - time_val (datetime.time or str): Time value.

        Returns:
        - int: Time converted to minutes, or None if input is invalid.
        """
        if isinstance(time_val, time):
            return time_val.hour * 60 + time_val.minute + time_val.second / 60
        elif isinstance(time_val, str):
            try:
                parts = list(map(int, time_val.split(':')))
                return parts[0] * 60 + parts[1] + (parts[2] / 60 if len(parts) == 3 else 0)
            except ValueError:
                return None
        else:
            return None

    def get_departure_minutes(self):
        return self.flights_pd['departure_minutes'].tolist()

    def get_arrival_minutes(self):
        return self.flights_pd['arrival_minutes'].tolist()
    
##########################################################################################################         

class NodesGenerator():
    def __init__(self,flights_df, station_list, flight_no_col, origin_col, destination_col, departure_col, arrival_col, dep, arriv):
        self.flights_df = flights_df
        self.dep = dep
        self.arriv = arriv
        self.flights_df.iloc[:, departure_col] = self.dep
        self.flights_df.iloc[:, arrival_col] = self.arriv
        self.cities = station_list
        
        self.nodes_df = pd.DataFrame(columns=['node_no', 'city', 'time', 'flights'])
        self.nodes_df.set_index('node_no', inplace=True)
        
        arrival_column_name = self.flights_df.columns[arrival_col]

        for city in self.cities:
            city_flights = self.flights_df[(self.flights_df.iloc[:, origin_col] == city) | (self.flights_df.iloc[:, destination_col] == city)].copy()
            
            def func(From, departure, arrival):
                if city == From:
                    return departure
                else:
                    return arrival
                
            city_flights['stagger_time'] = city_flights.apply(lambda x: func(x.iloc[origin_col], x.iloc[departure_col], x.iloc[arrival_col]), axis=1)
            city_flights = city_flights.sort_values(['stagger_time', arrival_column_name])
            
            types = np.select([city_flights.iloc[:, origin_col] == city, city_flights.iloc[:, destination_col] == city], ['deprt', 'arrv'], default='nan')        
            
            prev_type = "arrv"
            flights = []
            prev_time = 0
            for idx, type in enumerate(types):         
                flight = [city_flights.iloc[idx, flight_no_col], -1] if type == "deprt" else [city_flights.iloc[idx, flight_no_col], 1]
                
                if ((prev_type == "deprt") & (type == "arrv")) | (idx == len(types)-1):
                    if not ((prev_type == "arrv") & (type == "arrv") & (idx == len(types)-1)):
                        if type == "deprt":
                            flights.append(flight)
                        self.nodes_df.loc[len(self.nodes_df)] = [city, prev_time, flights]
                        flights = []
                    
                    if (idx == len(types)-1) & (type == "arrv"):
                        flights.append(flight)
                        self.nodes_df.loc[len(self.nodes_df)] = [city, city_flights.iloc[idx]['stagger_time'], flights]
                        flights = []
                    
                
                flights.append(flight)
                prev_time = city_flights.iloc[idx]['stagger_time']
                prev_type = type
                
        self.nodes_df.index +=1
        
    def get_nodes(self):        
        return self.nodes_df
        
##########################################################################################################     

class VariableY():
    def __init__(self, Nodes_df, station_list, fleet_list):
        self.vars_y = []
        for fleet in fleet_list:
            for city in station_list:
                city_nodes = Nodes_df[Nodes_df['city'] == city]
                if len(city_nodes) > 1:
                    for idx in city_nodes.index[1:]:
                        var_name = str(idx-1) + "_" + \
                            str(idx) + ',' + str(fleet)
                        self.vars_y.append(var_name)
    def get_y(self):
        return self.vars_y
    
##########################################################################################################     

class flights_oeprating_costs:
    ''' Get the flights dataframe as input and calculate or import its operating costs based on fleet'''
    
    def __init__(self,flights_df,fleets_df) :
        
        self.flights_df=flights_df
        self.fleets_data=fleets_df
                  
    
    def given_operating_cost(self, distance_col, oc_list):
        
        """ place the operating costs given in a list"""
        
        cost_list = []
        
        for i in range(len(self.flights_df)):
            for j in range(len(self.fleets_data)):
                cost_list.append(self.flights_df.iloc[i, distance_col] * oc_list[j])
        
        
        return(cost_list)
    
##########################################################################################################     

class FlightsCategorization():
    def __init__(self, flights_df, flight_no_col):
        self.optional_flights = []
        self.non_optional_flights = []
        self.flights_df = flights_df
        
        for flight_type in self.flights_df.index:
            self.flight_number = str(self.flights_df.iloc[flight_type, flight_no_col])
            if self.flights_df['Optional'][flight_type] == 0:
                self.non_optional_flights.append(self.flight_number)
            elif self.flights_df['Optional'][flight_type] == 1:
                self.optional_flights.append(self.flight_number)
            else:
                self.optional_flights.append(self.flight_number)
                
                
    def optional_flights(self):
        return self.optional_flights
    
    
    def non_optional_flights(self):
        return self.non_optional_flights
    
##########################################################################################################     

class VariableZ():
    def __init__(self, itineraries_df, itinerary_no_col):
        self.itineraries_df = itineraries_df
        self.vars_z = []
        
        if 'Optional' in self.itineraries_df.columns:
            for idx, itn_deleted in self.itineraries_df[ self.itineraries_df['Optional'] != 0].iterrows():
                var_name = str(itn_deleted.iloc[itinerary_no_col])
                self.vars_z.append(var_name)
                
        else:
            self.vars_z = None
    
    def get_z(self):
        return self.vars_z
        
        
##########################################################################################################     
class spilled_and_captured_variables():
    
    def __init__(self,flights_df):    
        self.__flights_df=flights_df
            
    def Itinraries_df_simplify(self, itineraries_df,itinerary_no_col, flights_col, flight_no_col, origin_col, destination_col,type_col):
        """
        Output the itineraries dataframe after adding 'From', 'To', spillage itineraries, and optional or not.
        
        """
       
        # Making new column and place the origin and destination of itineraries according to the itinerary start and end flight
        print("Flight No. Col:", flight_no_col)
        print("Origin Col:", origin_col)
        print("Destination Col:", destination_col)
        
        print("Flights DataFrame:")
        print(self.__flights_df)
        
        print("Itineraries DataFrame:")
        print(itineraries_df)
            
        for idx, itn in itineraries_df.iterrows():
            
            # Get the first and last flight numbers from the flights column
            flight_numbers = [int(flight) for flight in str(itn.iloc[flights_col]).split(', ')]
            first_flight_num, last_flight_num = flight_numbers[0], flight_numbers[-1]
            
            print(flight_numbers)
            print(flights_col)
            
            
            # Find the 'From' for the first flight and 'To' for the last flight
            itineraries_df.at[idx, 'From'] = self.__flights_df.iloc[(self.__flights_df.iloc[:, flight_no_col] == first_flight_num).values, origin_col].iloc[0]
            itineraries_df.at[idx, 'To'] = self.__flights_df.iloc[(self.__flights_df.iloc[:, flight_no_col] == last_flight_num).values, destination_col].iloc[0]

        # Make a spillage column and contain number of itineraries +1 which is the dummy itinerary    
        itineraries_df['spillage'] = str(len(itineraries_df) + 1)
        
        # Define a mapping for itinerary types to integers reflecting their priority
        type_priority = {'non_stop': 1, 'direct': 2, 'single_stop': 3, 'double_stop': 4}
        # Convert itinerary types to their numeric priorities for comparison
        itineraries_df['type_priority'] = itineraries_df.iloc[:,type_col].map(type_priority)
        
        # In the spillage column for each itinerary, check for other alternative itineraries and add its number in the column
        for idx, itn in itineraries_df.iterrows():
            spillage_itineraries = []
            for idx2, itn2 in itineraries_df.iterrows():
                if itn['From'] == itn2['From'] and itn['To'] == itn2['To'] and itn['type_priority'] < itn2['type_priority']:
                    spillage_itineraries.append(str(itn2.iloc[itinerary_no_col]))

            # Update spillage if there are other eligible itineraries
            if spillage_itineraries:
                itineraries_df.at[idx, 'spillage'] += ', ' + ', '.join(spillage_itineraries)

        # Optionally drop the 'type_priority' column if it's no longer needed
        return itineraries_df
    
    def spill_recaptured_variables_list(self, itenraries_df,itinerary_no_col):
        ''' return a list of t_p_r which is the spllied from itenrary p and recaptured by iternrary r'''
        
        spilled_recaptured_vars=[]
        # Spillage variables                
        for idx, itn in itenraries_df.iterrows():
            for spill_on in itn['spillage'].split(', '):
                if spill_on != itn.iloc[itinerary_no_col]:
                    
                    # Add spill on the other itinerary that's accounting for spill to other airlines
                    if spill_on == str(len(itenraries_df) + 1):
                        var_name = "t_" + str(itn.iloc[itinerary_no_col]) + "_" + str(spill_on)
                        spilled_recaptured_vars.append(var_name)
                        
                    
                    else:
                        #print("Itineraries data type")
                        #print(itenraries_df.dtypes)
                        #spill_on_type = itenraries_df[itenraries_df['itinerary'] == int(spill_on)]['type'].iloc[0]
                        
                        var_name = "t_" + str(itn.iloc[itinerary_no_col]) + "_" + str(spill_on)
                        spilled_recaptured_vars.append(var_name)
        
        
        # print(spilled_recaptured_vars)
        return(spilled_recaptured_vars)
    
##########################################################################################################     

class DemandCorrection():
    def __init__(self, itineraries_df, demand_increase_factor, demand_decrease_factor, optional_itineraries, optional_flight, itinerary_no_col, flights_col, demand_col):
        # Create an empty list to store each row of the new DataFrame
        self.data = []
        
        # Iterate over each itinerary
        for index1, row1 in itineraries_df.iterrows():
            # Ensure 'flights' is a list of strings
            flights_of_first_itinerary = str(row1.iloc[flights_col]).split(', ')    
            # Check if this itinerary is cancellable
            if row1.iloc[itinerary_no_col] in optional_itineraries:
                # Compare with every other itinerary
                for index2, row2 in itineraries_df.iterrows():
                    if index1 != index2:
                        flights_of_second_itinerary = str(row2.iloc[flights_col]).split(', ')
                        shared_flights = set(flights_of_first_itinerary).intersection(flights_of_second_itinerary)
                        
                        # Construct the column name
                        column_name = f"D_{row1.iloc[itinerary_no_col]}_{row2.iloc[itinerary_no_col]}"
                        append_data = True  # Initialize flag to append data
                        
                        if not shared_flights:
                            if row1['From'] == row2['From'] and row1['To'] == row2['To'] and row1['type_priority'] <= row2['type_priority']:
                                # Same origin and destination and no shared flights with valid priority
                                value = (demand_increase_factor/100) * row1.iloc[demand_col]  # Increase by 15%
                            else:
                                # Different origin or destination and no shared flights
                                value = (-demand_decrease_factor/100) * row1.iloc[demand_col]  # Decrease by 5%
                                
                        elif shared_flights:
                            for flight in flights_of_second_itinerary:
                                if flight in optional_flight:
                                    append_data = False  # Do not append data if the shared flight is cancellable
                                                
                                else:
                                    if row1['From'] == row2['From'] and row1['To'] == row2['To'] and row1['type_priority'] <= row2['type_priority']:
                                        # Same origin and destination and shared flights with valid priority
                                        value = (demand_increase_factor/100) * row1.iloc[demand_col]  # Increase by 15%
                                    else:
                                        # Different origin or destination and shared flights
                                        value = (-demand_decrease_factor/100) * row1.iloc[demand_col]  # Decrease by 5%
                        
                        # Check the flag before appending
                        if append_data:
                            if value >= 0:
                                value = math.ceil(value)
                            else:
                                value = math.floor(value)
                            self.data.append({'name': column_name, 'value': value})
                            
    def get_demand_correction_df(self):
        # Create DataFrame from the list
        self.demand_correction_factor_df = pd.DataFrame(self.data)
        return self.demand_correction_factor_df
    
    