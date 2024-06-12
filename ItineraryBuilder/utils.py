import pandas as pd
import re
from io import BytesIO
import io
import pandas as pd
import itertools
from datetime import datetime,timedelta
import numpy as np
from tabulate import tabulate
from .forms import TurnAroundTimeForm, ConnectionTimeForm
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2


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
    
class ColumnIndex:
    def __init__(self, flights_pd):
        self.flights_pd = flights_pd
        self.column_name_mappings = {
            "flight number": ['Flight', 'flight', 'Flights', 'flights', 'Flight Number', 'flight number', 'FlightNumber', 'flightnumber'],
            "origin": ['Origin', 'origin', 'FROM', 'from', 'From'],
            "departure": ['Departure', 'departure', 'dep', 'departuretime', 'DepartureTime', 'departure time'],
            "destination": ['Destination', 'destination', 'DESTINATION', 'dest', 'TO', 'To', 'to', 'Dest'],
            "arrival": ['Arrival', 'arrival', 'arr', 'arrivaltime', 'ArrivalTime', 'arrival time']
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
        return True, "Data format is correct"

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
    
##############################################################################################

class ColumnIndex_Airport:
    def __init__(self, airport_pd):
        self.airport_pd = airport_pd
        self.column_name_mappings = {
            "airport": ['name', 'airport', 'airports', 'Airports', 'Airport', 'AIRPORTS'],
            "longitude": ['lon', 'longitude', 'LON', 'LONGITUDE', 'Longitude'],
            "latitude": ['lat', 'latitude', 'LAT', 'LATITUDE', 'Latitude'],
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
        sample_data = self.airport_pd.iloc[:, column_index].dropna().head(10)
        
        if column_type == 'airport':
            if not all(self.is_valid_alphabetic(value) for value in sample_data):
                return False, f"Sample data for 'Airport' column does not match expected numeric format: {sample_data.tolist()}"
        elif column_type in ['longitude', 'latitude']:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected numeric format: {sample_data.tolist()}"
        return True, "Data format is correct"

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
        columns = self.airport_pd.columns
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

    def is_valid_alphabetic(self, data):
        """Check if data is alphabetic."""
        if isinstance(data, str):
            return data.isalpha()
        
    def is_valid_numeric(self, data):
        """Check if data is numeric."""
        try:
            float(data)  # Attempt to convert to float to handle numbers with decimals
            return True
        except ValueError:
            return False
    
    def get_airport_column(self):
        """Get the column index for airport."""
        return self.columns["airport"]

    def get_longitude_column(self):
        """Get the column index for longitude."""
        return self.columns["longitude"]

    def get_latitude_column(self):
        """Get the column index for latitude."""
        return self.columns["latitude"]
    
##############################################################################################

class ClockToMinutes:
    def __init__(self, flights_pd, departure_index, arrival_index):
        self.flights_pd = flights_pd
        self.departure_index = departure_index
        self.arrival_index = arrival_index
        self.convert_times_to_minutes()

    def convert_times_to_minutes(self):
        # Assuming departure and arrival times are in 'HH:MM:SS' format
        self.flights_pd['departure_minutes'] = self.flights_pd.iloc[:, self.departure_index].apply(self.convert_to_minutes)
        self.flights_pd['arrival_minutes'] = self.flights_pd.iloc[:, self.arrival_index].apply(self.convert_to_minutes)

    @staticmethod
    def convert_to_minutes(time_str):
        h, m, *s = map(int, time_str.split(':'))
        return h * 60 + m + (s[0] / 60 if s else 0)

    def get_departure_minutes(self):
        """Return a list of departure times in minutes."""
        return self.flights_pd['departure_minutes'].tolist()

    def get_arrival_minutes(self):
        """Return a list of arrival times in minutes."""
        return self.flights_pd['arrival_minutes'].tolist()
    
##############################################################################################################

class UniqueStations:
    def __init__(self, flights, origin_index):
        self.flights = flights
        self.origin_index = origin_index

    def get_stations(self):
        return self.flights.iloc[:, self.origin_index].unique().tolist()
    
##############################################################################################################
# Function to calculate Haversine distance between two points
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 3959 * (2 * atan2(sqrt(a), sqrt(1 - a)))  # Earth radius in miles


# Function to create a distance DataFrame
def create_distance_dataframe(locations, airport_index, latitude_index, longitude_index):
    distances = []
    for i in range(len(locations)):
        for j in range(len(locations)):
            if i != j:
                lat1, lon1 = locations.iloc[i, latitude_index], locations.iloc[i, longitude_index]
                lat2, lon2 = locations.iloc[j, latitude_index], locations.iloc[j, longitude_index]
                distance = haversine(lat1, lon1, lat2, lon2)
                distances.append({
                    "origin": locations.iloc[i, airport_index],
                    "destination": locations.iloc[j, airport_index],
                    "distance": distance
                })
                # unique_airports = UniqueStations(distances, airport_index)
                # airports_distances = unique_airports.get_stations()
                airports_distances_df = pd.DataFrame(distances)
                
    return airports_distances_df


# Now you can use distance_df for further processing in your code

##############################################################################################################

class Flights_Distance_Duration:
    """This class generates single stop itineraries based on flight schedule and connection times."""

    def __init__(self, one_day_flights, dep, arriv, flight_number_index, origin_column_no, departure_index, destination_column_no, arrival_index, min_connection, max_connection, airports_distances_df, distance_ratio):
        self.flights = one_day_flights
        self.dep = dep
        self.arriv = arriv
        self.flight_number_index = int(flight_number_index)
        self.origin_column_no = int(origin_column_no)
        self.departure_index = int(departure_index)
        self.destination_column_no = int(destination_column_no)
        self.arrival_index = int(arrival_index)
        self.airports_distances_df = airports_distances_df
        self.distance_ratio = distance_ratio

        # Initialize 'Distance' and 'Duration' columns if they do not exist
        if 'Distance' not in self.flights.columns:
            self.flights['Distance'] = 0
        elif 'distance' not in self.flights.columns:
            self.flights['Distance'] = 0
        elif 'DISTANCE' not in self.flights.columns:
            self.flights['Distance'] = 0
        if 'Duration' not in self.flights.columns:
            self.flights['Duration'] = "0h"
        elif 'duration' not in self.flights.columns:
            self.flights['Duration'] = "0h"
        elif 'DURATION' not in self.flights.columns:
            self.flights['Duration'] = "0h"

        self.calculate_distances()
        self.calculate_durations()
        self.remove_temporary_columns()

    def calculate_distances(self):
        # Calculate distances using vectorized operations where possible
        for i in range(len(self.flights)):
            origin = self.flights.iloc[i, self.origin_column_no]
            destination = self.flights.iloc[i, self.destination_column_no]
            
            mask = (self.airports_distances_df['origin'] == origin) & (self.airports_distances_df['destination'] == destination)
            distances = self.airports_distances_df.loc[mask, 'distance']
            
            if not distances.empty:
                self.flights.at[i, 'Distance'] = round(distances.sum(),1)  # Use sum if multiple entries, else just assign

    # def calculate_durations(self):
    #     # Calculate durations
    #     for i in range(len(self.flights)):
    #         try:
    #             first_departure_time = datetime.strptime(self.flights.iloc[i, self.departure_index], '%H:%M:%S')
    #             last_arrival_time = datetime.strptime(self.flights.iloc[i, self.arrival_index], '%H:%M:%S')
    #         except ValueError:
    #             continue  # Skip rows where time format does not match
            
    #         if first_departure_time < last_arrival_time:
    #             delta = last_arrival_time - first_departure_time
    #             hours = delta.seconds // 3600
    #             minutes = (delta.seconds % 3600) // 60
    #             duration = f"{hours}h {minutes}m" if minutes else f"{hours}h"
    #         else:
    #             duration = "0h"  # If departure is not after arrival, set duration to "0h"

    #         self.flights.at[i, 'Duration'] = duration
    
    def calculate_durations(self):
    # Calculate durations
        for i in range(len(self.flights)):
            try:
                first_departure_time = datetime.strptime(self.flights.iloc[i, self.departure_index], '%H:%M:%S')
                last_arrival_time = datetime.strptime(self.flights.iloc[i, self.arrival_index], '%H:%M:%S')
            except ValueError:
                continue  # Skip rows where time format does not match

            # Adjust for flights that end after midnight
            if last_arrival_time < first_departure_time:
                last_arrival_time += timedelta(days=1)

            delta = last_arrival_time - first_departure_time
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            duration = f"{hours}h {minutes}m" if minutes else f"{hours}h"

            self.flights.at[i, 'Duration'] = duration
    
    def remove_temporary_columns(self):
        # Remove the temporary columns from the DataFrame
        self.flights.drop(['departure_minutes', 'arrival_minutes'], axis=1, inplace=True)
            
    def get_flights_distance_duration(self):
        """Returns the single stop itineraries as a DataFrame."""
        return self.flights
            

##############################################################################################################

class ItinSSBuilder:
    """This class generates single stop itineraries based on flight schedule and connection times."""
    
    def __init__(self, one_day_flights, dep, arriv, flight_number_index, origin_column_no, departure_index, destination_column_no, arrival_index, min_connection, max_connection, airports_distances_df, distance_ratio):
        self.flights = one_day_flights
        self.dep = dep
        self.arriv = arriv
        self.flight_number_index = int(flight_number_index)
        self.origin_column_no = int(origin_column_no)
        self.departure_index = int(departure_index)
        self.destination_column_no = int(destination_column_no)
        self.arrival_index = int(arrival_index)
        self.min_connection = min_connection
        self.max_connection = max_connection
        self.airports_distances_df = airports_distances_df
        self.distance_ratio = distance_ratio
        self.itin_list = []

    def generate_itineraries(self):
        for i in range(len(self.flights)):
            for j in range(i + 1, len(self.flights)):
                if self.is_valid_connection(i, j):
                    self.add_itinerary(i, j)
        
        # Convert list to DataFrame after all itineraries are collected
        
        self.itin_df = pd.DataFrame(self.itin_list, columns=[
            'Itinerary_Number', 'Flight_Number_1', 'Origin_1', 'Departure_1', 'Destination_1', 'Arrival_1',
            'Flight_Number_2', 'Origin_2', 'Departure_2', 'Destination_2', 'Arrival_2', 'First_Transit_Time', 'Duration'
        ])
        
        
        for i in range(len(self.itin_df)):
            distance_itin = 0
            for j in range(len(self.airports_distances_df)):
                for k in range(len(self.airports_distances_df)):
                    if (self.itin_df.loc[i, 'Origin_1'] == self.airports_distances_df.loc[j, 'origin'] and
                        self.itin_df.loc[i, 'Destination_1'] == self.airports_distances_df.loc[j, 'destination'] and
                        self.itin_df.loc[i, 'Origin_2'] == self.airports_distances_df.loc[k, 'origin'] and
                        self.itin_df.loc[i, 'Destination_2'] == self.airports_distances_df.loc[k, 'destination']):
                        
                        
                        distance_itin += round(self.airports_distances_df.loc[j, 'distance'], 1)
                        distance_itin += round(self.airports_distances_df.loc[k, 'distance'], 1)

            self.itin_df.loc[i, 'Distance'] = distance_itin
            
        # Create a boolean mask initialized to keep all rows
        mask = pd.Series(True, index=self.itin_df.index)
            
        for i in range(len(self.itin_df)):
            for j in range(len(self.airports_distances_df)):
                if (self.itin_df.loc[i, 'Origin_1'] == self.airports_distances_df.loc[j, 'origin'] and
                        self.itin_df.loc[i, 'Destination_2'] == self.airports_distances_df.loc[j, 'destination']):
                    if self.itin_df.loc[i, 'Distance'] > self.distance_ratio * self.airports_distances_df.loc[j, 'distance']:
                        mask[i] = False
                        
        # After the loops, drop the marked rows
        self.itin_df = self.itin_df[mask]
        c=1
        for idx, itins in self.itin_df.iterrows():
            self.itin_df.loc[idx, 'Itinerary_Number'] = c
            c += 1
            
                    

    def is_valid_connection(self, i, j):
        # Check if destination of first leg is the origin of the second leg
        valid_destination_origin = self.flights.iloc[i, self.destination_column_no] == self.flights.iloc[j, self.origin_column_no]
        not_circular_route = self.flights.iloc[i, self.origin_column_no] != self.flights.iloc[j, self.destination_column_no]
        connection_time = self.dep[j] - self.arriv[i]
        valid_connection_time = self.min_connection <= connection_time <= self.max_connection

        return valid_destination_origin and not_circular_route and valid_connection_time
    
    
    # def add_itinerary(self, i, j):
    #     itinerary_number = len(self.itin_list) + 1
    #     flight1 = self.flights.iloc[i, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()
    #     flight2 = self.flights.iloc[j, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()

    #     # Convert departure and arrival times from string to datetime objects
    #     # Convert departure and arrival times from string to datetime objects
    #     departure_time = datetime.strptime(self.flights.iloc[j, self.departure_index], '%H:%M:%S')
    #     arrival_time = datetime.strptime(self.flights.iloc[i, self.arrival_index], '%H:%M:%S')
        

    #     # Calculate the transit time difference
    #     if departure_time > arrival_time:
    #         delta_1 = departure_time - arrival_time
    #         hours_1 = delta_1.seconds // 3600
    #         minutes_1 = (delta_1.seconds % 3600) // 60
    #         if minutes_1 > 0:
    #             first_transit_time = [f"{hours_1}h {minutes_1}"]
    #         else:
    #             first_transit_time = [f"{hours_1}h"]
    #     else:
    #         first_transit_time = ["0h"]  # If departure is not after arrival, set transit time to "0h"
        
    #     first_departure_time = datetime.strptime(self.flights.iloc[i, self.departure_index], '%H:%M:%S')
    #     last_arrival_time = datetime.strptime(self.flights.iloc[j, self.arrival_index], '%H:%M:%S')
            
    #     if first_departure_time < last_arrival_time:
    #         delta_2 = last_arrival_time - first_departure_time
    #         hours_2 = delta_2.seconds // 3600
    #         minutes_2 = (delta_2.seconds % 3600) // 60
    #         if minutes_2 > 0:
    #             duration = [f"{hours_2}h {minutes_2}"]
    #         else:
    #             duration = [f"{hours_2}h"]
    #     else:
    #         duration = ["0h"]  # If departure is not after arrival, set transit time to "0h"


    #     row = [itinerary_number] + flight1 + flight2 + first_transit_time + duration
    #     self.itin_list.append(row)

    def add_itinerary(self, i, j):
        itinerary_number = len(self.itin_list) + 1
        flight1 = self.flights.iloc[i, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()
        flight2 = self.flights.iloc[j, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()

        # Convert departure and arrival times from string to datetime objects
        departure_time = datetime.strptime(self.flights.iloc[j, self.departure_index], '%H:%M:%S')
        arrival_time = datetime.strptime(self.flights.iloc[i, self.arrival_index], '%H:%M:%S')
        
        # Calculate the transit time difference
        if departure_time > arrival_time:
            delta_1 = departure_time - arrival_time
            hours_1 = delta_1.seconds // 3600
            minutes_1 = (delta_1.seconds % 3600) // 60
            first_transit_time = f"{hours_1}h {minutes_1}m" if minutes_1 else f"{hours_1}h"
        else:
            # Handling crossing midnight: Adjust arrival time to the next day
            arrival_time += timedelta(days=1)
            delta_1 = departure_time - arrival_time
            hours_1 = delta_1.seconds // 3600
            minutes_1 = (delta_1.seconds % 3600) // 60
            first_transit_time = f"{hours_1}h {minutes_1}m" if minutes_1 else f"{hours_1}h"

        first_departure_time = datetime.strptime(self.flights.iloc[i, self.departure_index], '%H:%M:%S')
        last_arrival_time = datetime.strptime(self.flights.iloc[j, self.arrival_index], '%H:%M:%S')
            
        if first_departure_time > last_arrival_time:
            last_arrival_time += timedelta(days=1)

        delta_2 = last_arrival_time - first_departure_time
        hours_2 = delta_2.seconds // 3600
        minutes_2 = (delta_2.seconds % 3600) // 60
        duration = f"{hours_2}h {minutes_2}m" if minutes_2 else f"{hours_2}h"

        row = [itinerary_number] + flight1 + flight2 + [first_transit_time] + [duration]
        self.itin_list.append(row)
    
    def get_ss_itin(self):
        """Returns the single stop itineraries as a DataFrame."""
        return self.itin_df
    
##############################################################################################################

class ItinDSBuilder:
    """Generates double stop itineraries based on single stop itineraries."""
    
    def __init__(self, one_day_flights, ss_itin_df, dep, arriv, flight_number_index, origin_column_no, departure_index, destination_column_no, arrival_index, min_connection, max_connection, airports_distances_df, distance_ratio):
        self.flights = one_day_flights
        self.ss_flights = ss_itin_df
        self.dep = dep
        self.arriv = arriv
        self.flight_number_index = flight_number_index
        self.origin_column_no = origin_column_no
        self.departure_index = departure_index
        self.destination_column_no = destination_column_no
        self.arrival_index = arrival_index
        self.min_connection = min_connection
        self.max_connection = max_connection
        self.airports_distances_df = airports_distances_df
        self.distance_ratio = distance_ratio
        self.itin_list = []

    def generate_itineraries(self):
        for idx, ss_flight in self.ss_flights.iterrows():
            try:
                ss_arrival_time = self.parse_time(ss_flight['Arrival_2'])
                ss_arrival_total_minutes = ss_arrival_time.hour * 60 + ss_arrival_time.minute

                for j in range(len(self.flights)):
                    if self.is_valid_connection(idx, j, ss_arrival_total_minutes):
                        self.add_itinerary(idx, j, ss_arrival_total_minutes)

            except KeyError as e:
                print(f"KeyError: {e} - likely due to a missing column in the DataFrame.")
            except Exception as e:
                print(f"An error occurred: {e}")
                
        print('klk',self.itin_list)
        self.ds_itin_df = pd.DataFrame(self.itin_list, columns=[
            'Itinerary_Number', 'Flight_Number_1', 'Origin_1', 'Departure_1', 'Destination_1', 'Arrival_1',
            'Flight_Number_2', 'Origin_2', 'Departure_2', 'Destination_2', 'Arrival_2',
            'Flight_Number_3', 'Origin_3', 'Departure_3', 'Destination_3', 'Arrival_3', 'First_Transit_Time' , 'Second_Transit_Time', 'Duration'
        ])
        
        for i in range(len(self.ds_itin_df)):
            distance_itin = 0
            for j in range(len(self.airports_distances_df)):
                for k in range(len(self.airports_distances_df)):
                    for m in range(len(self.airports_distances_df)):
                        if (self.ds_itin_df.loc[i, 'Origin_1'] == self.airports_distances_df.loc[j, 'origin'] and
                            self.ds_itin_df.loc[i, 'Destination_1'] == self.airports_distances_df.loc[j, 'destination'] and
                            self.ds_itin_df.loc[i, 'Origin_2'] == self.airports_distances_df.loc[k, 'origin'] and
                            self.ds_itin_df.loc[i, 'Destination_2'] == self.airports_distances_df.loc[k, 'destination'] and
                            self.ds_itin_df.loc[i, 'Origin_3'] == self.airports_distances_df.loc[m, 'origin'] and
                            self.ds_itin_df.loc[i, 'Destination_3'] == self.airports_distances_df.loc[m, 'destination']):
                            
                            distance_itin += round(self.airports_distances_df.loc[j, 'distance'], 1)
                            distance_itin += round(self.airports_distances_df.loc[k, 'distance'], 1)
                            distance_itin += round(self.airports_distances_df.loc[m, 'distance'], 1)

            self.ds_itin_df.loc[i, 'Distance'] = distance_itin
            
        # Create a boolean mask initialized to keep all rows
        mask = pd.Series(True, index=self.ds_itin_df.index)
            
        for i in range(len(self.ds_itin_df)):
            for j in range(len(self.airports_distances_df)):
                if (self.ds_itin_df.loc[i, 'Origin_1'] == self.airports_distances_df.loc[j, 'origin'] and
                        self.ds_itin_df.loc[i, 'Destination_3'] == self.airports_distances_df.loc[j, 'destination']):
                    if self.ds_itin_df.loc[i, 'Distance'] > self.distance_ratio * self.airports_distances_df.loc[j, 'distance']:
                        mask[i] = False

        # After the loops, drop the marked rows
        self.ds_itin_df = self.ds_itin_df[mask]
        c=1
        for idx, itins in self.ds_itin_df .iterrows():
            self.ds_itin_df.loc[idx, 'Itinerary_Number'] = c
            c += 1

    def is_valid_connection(self, i, j, ss_arrival_total_minutes):
        destination_match = self.ss_flights.loc[i, 'Destination_2'] == self.flights.iloc[j, self.origin_column_no]
        not_circular_route_1 = self.ss_flights.loc[i, 'Origin_1'] != self.flights.iloc[j, self.destination_column_no]
        not_circular_route_2 = self.ss_flights.loc[i, 'Origin_2'] != self.flights.iloc[j, self.destination_column_no]
        connection_time = self.dep[j] - ss_arrival_total_minutes
        valid_connection_time = self.min_connection <= connection_time <= self.max_connection

        return destination_match and not_circular_route_1 and not_circular_route_2 and valid_connection_time
    # def add_itinerary(self, i, j, ss_arrival_total_minutes):
        itinerary_number = len(self.itin_list) + 1
        flight1 = self.ss_flights.loc[i, ['Flight_Number_1', 'Origin_1', 'Departure_1', 'Destination_1', 'Arrival_1']].tolist()
        flight2 = self.ss_flights.loc[i, ['Flight_Number_2', 'Origin_2', 'Departure_2', 'Destination_2', 'Arrival_2']].tolist()
        flight3 = self.flights.iloc[j, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()
        
        # Convert departure and arrival times from string to datetime objects
        departure_time = datetime.strptime(str(self.ss_flights.iloc[i]['Departure_1']), '%H:%M:%S')
        arrival_time = datetime.strptime(str(self.ss_flights.iloc[i]['Arrival_1']), '%H:%M:%S')
        departure_time_2 = datetime.strptime(self.flights.iloc[j, self.departure_index], '%H:%M:%S')
        

        # Calculate the transit time difference
        if departure_time > arrival_time:
            delta_1 = departure_time - arrival_time
            hours_1 = delta_1.seconds // 3600
            minutes_1 = (delta_1.seconds % 3600) // 60
            if minutes_1 > 0:
                first_transit_time = [f"{hours_1}h {minutes_1}"]
            else:
                first_transit_time = [f"{hours_1}h"]
        else:
            first_transit_time = ["0h"]  # If departure is not after arrival, set transit time to "0h"
            
        if arrival_time > departure_time_2:
            delta_3 =  arrival_time - departure_time_2
            hours_3 = delta_3.seconds // 3600
            minutes_3 = (delta_3.seconds % 3600) // 60
            if minutes_3 > 0:
                second_transit_time = [f"{hours_3}h {minutes_3}"]
            else:
                second_transit_time = [f"{hours_3}h"]
        else:
            second_transit_time = ["0h"]  # If departure is not after arrival, set transit time to "0h"
            
        
        first_departure_time = datetime.strptime(str(self.ss_flights.iloc[i]['Departure_1']), '%H:%M:%S')   
        last_arrival_time = datetime.strptime(self.flights.iloc[j, self.arrival_index], '%H:%M:%S')
            
        if first_departure_time < last_arrival_time:
            delta_2 =  last_arrival_time - first_departure_time
            hours_2 = delta_2.seconds // 3600
            minutes_2 = (delta_2.seconds % 3600) // 60
            if minutes_2 > 0:
                duration = [f"{hours_2}h {minutes_2}"]
            else:
                duration = [f"{hours_2}h"]
        else:
            duration = ["0h"]  # If departure is not after arrival, set transit time to "0h"

        
        row = [itinerary_number] + flight1 + flight2 + flight3 + first_transit_time + second_transit_time + duration
        
        self.itin_list.append(row)
        
    # def add_itinerary(self, i, j, ss_arrival_total_minutes):
        itinerary_number = len(self.itin_list) + 1
        flight1 = self.ss_flights.loc[i, ['Flight_Number_1', 'Origin_1', 'Departure_1', 'Destination_1', 'Arrival_1']].tolist()
        flight2 = self.ss_flights.loc[i, ['Flight_Number_2', 'Origin_2', 'Departure_2', 'Destination_2', 'Arrival_2']].tolist()
        flight3 = self.flights.iloc[j, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()
        
        # Convert departure and arrival times from string to datetime objects
        arrival_time_1 = datetime.strptime(flight1[-1], '%H:%M:%S')  # Arrival_1
        departure_time_2 = datetime.strptime(flight2[2], '%H:%M:%S')  # Departure_2

        # Adjust for crossing midnight if necessary
        if departure_time_2 < arrival_time_1:
            departure_time_2 += timedelta(days=1)

        # Calculate the transit time difference between Arrival_1 and Departure_2
        delta_transit_1 = departure_time_2 - arrival_time_1
        hours_transit_1 = int(delta_transit_1.total_seconds() // 3600)
        minutes_transit_1 = int((delta_transit_1.total_seconds() % 3600) // 60)
        first_transit_time = f"{hours_transit_1}h {minutes_transit_1}m" if minutes_transit_1 else f"{hours_transit_1}h"

        # For total duration from Departure_1 to Arrival_3
        first_departure_time = datetime.strptime(flight1[2], '%H:%M:%S')  # Departure_1
        last_arrival_time = datetime.strptime(flight3[-1], '%H:%M:%S')  # Arrival_3

        # Adjust for crossing midnight if necessary
        if last_arrival_time < first_departure_time:
            last_arrival_time += timedelta(days=1)

        delta_total_duration = last_arrival_time - first_departure_time
        hours_total_duration = int(delta_total_duration.total_seconds() // 3600)
        minutes_total_duration = int((delta_total_duration.total_seconds() % 3600) // 60)
        total_duration = f"{hours_total_duration}h {minutes_total_duration}m" if minutes_total_duration else f"{hours_total_duration}h"

        # Construct the row for the itinerary list
        row = [itinerary_number] + flight1 + flight2 + flight3 + [first_transit_time, total_duration]
        self.itin_list.append(row)
    
    def add_itinerary(self, i, j, ss_arrival_total_minutes):
        itinerary_number = len(self.itin_list) + 1
        flight1 = self.ss_flights.loc[i, ['Flight_Number_1', 'Origin_1', 'Departure_1', 'Destination_1', 'Arrival_1']].tolist()
        flight2 = self.ss_flights.loc[i, ['Flight_Number_2', 'Origin_2', 'Departure_2', 'Destination_2', 'Arrival_2']].tolist()
        flight3 = self.flights.iloc[j, [self.flight_number_index, self.origin_column_no, self.departure_index, self.destination_column_no, self.arrival_index]].tolist()
        
        # Convert departure and arrival times from string to datetime objects
        arrival_time_1 = datetime.strptime(flight1[-1], '%H:%M:%S')  # Arrival_1
        departure_time_2 = datetime.strptime(flight2[2], '%H:%M:%S')  # Departure_2
        arrival_time_2 = datetime.strptime(flight2[-1], '%H:%M:%S')   # Arrival_2
        departure_time_3 = datetime.strptime(flight3[2], '%H:%M:%S')  # Departure_3

        # Adjust for crossing midnight if necessary
        if departure_time_2 < arrival_time_1:
            departure_time_2 += timedelta(days=1)
        if departure_time_3 < arrival_time_2:
            departure_time_3 += timedelta(days=1)

        # Calculate the first transit time difference between Arrival_1 and Departure_2
        delta_transit_1 = departure_time_2 - arrival_time_1
        hours_transit_1 = int(delta_transit_1.total_seconds() // 3600)
        minutes_transit_1 = int((delta_transit_1.total_seconds() % 3600) // 60)
        first_transit_time = f"{hours_transit_1}h {minutes_transit_1}m" if minutes_transit_1 else f"{hours_transit_1}h"

        # Calculate the second transit time difference between Arrival_2 and Departure_3
        delta_transit_2 = departure_time_3 - arrival_time_2
        hours_transit_2 = int(delta_transit_2.total_seconds() // 3600)
        minutes_transit_2 = int((delta_transit_2.total_seconds() % 3600) // 60)
        second_transit_time = f"{hours_transit_2}h {minutes_transit_2}m" if minutes_transit_2 else f"{hours_transit_2}h"

        # For total duration from Departure_1 to Arrival_3
        first_departure_time = datetime.strptime(flight1[2], '%H:%M:%S')  # Departure_1
        last_arrival_time = datetime.strptime(flight3[-1], '%H:%M:%S')  # Arrival_3
        if last_arrival_time < first_departure_time:
            last_arrival_time += timedelta(days=1)

        delta_total_duration = last_arrival_time - first_departure_time
        hours_total_duration = int(delta_total_duration.total_seconds() // 3600)
        minutes_total_duration = int((delta_total_duration.total_seconds() % 3600) // 60)
        total_duration = f"{hours_total_duration}h {minutes_total_duration}m" if minutes_total_duration else f"{hours_total_duration}h"

        # Construct the row for the itinerary list
        row = [itinerary_number] + flight1 + flight2 + flight3 + [first_transit_time, second_transit_time, total_duration]
        self.itin_list.append(row)

    def get_ds_itin(self):
        """Returns the double stop itineraries as a DataFrame."""
        return self.ds_itin_df

    @staticmethod
    def parse_time(time_str):
        """Parses time in 'HH:MM' or 'HH:MM:SS' format."""
        try:
            return datetime.strptime(time_str, '%H:%M:%S')
        except ValueError:
            return datetime.strptime(time_str, '%H:%M')

