import pandas as pd
import re
from io import BytesIO
from datetime import datetime, timedelta
import datetime as dt
import numpy as np
import random
import warnings
from sklearn import linear_model
import math
import seaborn as sns
import matplotlib.pyplot as plt
import warnings

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
                self.df = pd.read_excel(BytesIO(self.file_content), dtype=self.dtype)
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

class Itin_ColumnIndex:
    def __init__(self, itineraries_df):
        """Initialize the ColumnIndex object.

        Parameters:
        - itineraries_df: pandas.DataFrame, representing the flight data.
        """
        self.itinerary_pd = itineraries_df
        
        # Mapping of column types to their potential names
        self.column_name_mappings = {
            "Airline":['airline', 'AIRLINE','Airline'],
            "origin": ['Origin', 'origin', 'ORIGIN', 'FROM', 'from', 'From'],
            "departure": ['Departure', 'departure', 'DEPARTURE', 'dep', 'departuretime', 'DepartureTime', 'departure time', 'Departure Time'],
            "destination": ['Destination', 'destination', 'DESTINATION', 'dest', 'TO', 'to', 'Dest', 'To'],
            "arrival": ['Arrival', 'arrival', 'ARRIVAL', 'arr', 'arrivaltime', 'ArrivalTime', 'arrival time', 'Arrival Time'],
            "duration": ['duration', 'DURATION', 'Duration', 'Durations', 'Time', 'Times', 'TIME', 'time', 'DURATIONs', 'durations', 'flight hours', 'flight hour', 'Flight Hours', 'Flight hours', 'Flight Hour', 'FLIGHT HOUR', 'FLIGHT HOURS', 'Hours', 'HOURS', 'Hour', 'hour'],
            "type": ['Type', 'type', 'TYPE', 'category', 'Category', 'CATEGORY', 'class', 'Class', 'CLASS'],
            "First Stop":['FIRST STOP','First Stop','first stop'],
            "First Transit Time":['First Transit Time','FIRST TRANSIT TIME','first transit time'],
            "Second Stop":['SECOND STOP','Second Stop','second stop'],
            "Second Transit Time":['Second Transit Time','SECOND TRANSIT TIME','second transit time'],
            "Itinerary Price":['Itenrary Price','itenrary price','ITENRARY PRICE', 'Itinerary Price'],
            "distance": ['Distance', 'distance', 'miles', 'mile', 'Distances', 'DISTANCE', 'distances', 'MILE', 'MILES'],
        }


        self.columns = {key: None for key in self.column_name_mappings}  # Initialize columns dict
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
        sample_data = self.itinerary_pd.iloc[:, column_index].dropna().head(10)
        
        if column_type in ['origin', 'Airline', 'destination', 'type', 'First Stop', 'First Transit Time', 'Second Stop', 'Second Transit Time', 'duration']:
            if not all(self.is_valid_alphabetic(value) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected alphabetic format: {sample_data.tolist()}"
        elif column_type in ['departure', 'arrival']:
            if not all(self.is_valid_time_format(str(value)) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected time format (HH:MM): {sample_data.tolist()}"
        elif column_type in ['Itinerary Price', 'distance' ]:
            if not all(self.is_valid_numeric(value) for value in sample_data):
                return False, f"Sample data for '{column_type}' column does not match expected numeric format: {sample_data.tolist()}"
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
        columns = self.itinerary_pd.columns
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
        try:
            str(data)
            return True
        except ValueError:
            return False

    def is_valid_time_format(self, data):
        """Check if data is in a valid time format (HH:MM)."""
        return bool(re.match(r'\d{2}:\d{2}', data))
    
    def get_airline_name_column (self):
        """Get the column index for airline name."""
        return self.columns["Airline"]
    
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
    
    def get_duration_column(self):
        """Get the column index for duration."""
        return self.columns["duration"]
    
    def get_type_column(self):
        """Get the column index for type."""
        return self.columns["type"]
    
    def get_First_Stop_column(self):
        """Get the column index for First Stop."""
        return self.columns["First Stop"]
    
    def get_First_Transit_Time_column(self):
        """Get the column index for First Transit Time."""
        return self.columns["First Transit Time"]
    
    def get_Second_Stop_column(self):
        """Get the column index for Second Stop."""
        return self.columns["Second Stop"]
    
    def get_Second_Transit_Time_column(self):
        """Get the column index for Second Transit Time."""
        return self.columns["Second Transit Time"]
    
    def get_Itinerary_price_column(self):
        """Get the column index for itinerary price."""
        return self.columns["Itinerary Price"]
    
    def get_distance_column(self):
        """Get the column index for distance."""
        return self.columns["distance"]


#################################################################################################################

class DataEditing:
    def __init__(self, historical_Itineraries_df,airline_name_col,type_col,origin_col,destination_col,itinerary_price_col,duration_col,distance_col,user_airline_name,First_transit_col):
        
        self.historical_Itineraries_df = historical_Itineraries_df
        self.type_col = type_col
        self.origin_col = origin_col # From
        self.destination_col = destination_col # To 
        self.itinerary_price_col = itinerary_price_col
        self.airline_name_col =airline_name_col
        self.distance_col = distance_col
        self.user_airline_name = user_airline_name
        self.duration_col = duration_col
        self.First_transit_col= First_transit_col
        
    def read_data(self):
        ''' Read the itineraries file using its path and remove space after airline name'''
        self.data = self.historical_Itineraries_df
        
        self.data.iloc[:,self.airline_name_col] = self.data.iloc[:,self.airline_name_col] .apply(lambda x: x.strip())
        
        # print(self.data.iloc[:,self.airline_name_col].unique())


    def Sort_airlines_column(self):
        '''Sort the airlines column and start with User airline then add Itinerary ID'''
        airline_col_values = self.data.iloc[:,self.airline_name_col]
        # self.data.iloc[:,self.airline_name_col] = pd.Categorical( airline_col_values, categories=['Egypt Air'] + sorted( airline_col_values.unique()), ordered=True)
        airline_name_col = self.data.columns[self.airline_name_col]
        
        self.data=self.data.sort_values(by=[airline_name_col])
        
        # Create a new column to mark rows containing 'C'
        self.data['Sort_Order'] = self.data[airline_name_col].apply(lambda x: 0 if x == self.user_airline_name else 1)

        # Sort the DataFrame based on the custom sort order
        self.data = self.data.sort_values(by=['Sort_Order', airline_name_col])

        # Drop the 'Sort_Order' column if not needed
        self.data.drop(columns=['Sort_Order'], inplace=True)
        
        # Add itinerary ID column
        self.data['Itinerary ID'] = range(1, len(self.data) + 1)
    
    # Define a function to determine the market level of service
    def determine_market_level(self):
        ''' In this function we will make 2 columns.
            First column is called Priority.
            Second column is called Best Priority.
            For each market you will see level of service
            for each itinerary and for this market all the values
            in the column Best priority will be the same indicating the best itinerary level of service
            then each itinerary will has it's own priority depending on its level of service'''
            
        # Create a mapping from itinerary type to a numerical priority
        priority_map = {'Non Stop': 1, 'Direct':2 , '1 Stop': 3, '2 Stop': 4}
        
        # Map the Itineraries types to their numerical priorities
        self.data['Priority'] = self.data.iloc[:,self.type_col].map(priority_map)
        
        # Determine the best (minimum) priority per market (From-To combination)
        origin_col = self.data.columns.to_numpy()[self.origin_col]
        destination_col = self.data.columns.to_numpy()[self.destination_col]
        
        # print(f'origin_col: {origin_col}')
        # print(f'destination_col: {destination_col}')
        # print(f'self.data: {self.data}')
        
        
        self.data['Best Priority'] = self.data.groupby([origin_col, destination_col])['Priority'].transform('min')
        

    # Define a function to assign the "level of service" based on the best itinerary type
    def assign_level_of_service(self, row):
        levels = {
            (1, 1): 'Non Stop in Non Stop',
            (2,1): 'Direct in Non Stop',
            (2,2): 'Direct in Direct',
            (3, 1): 'Single Stop in Non Stop',
            (3,2): 'Single Stop in Direct',
            (3, 3): 'Single Stop in Single Stop',
            (4, 1): 'Double Stop in Non Stop',
            (4,2): 'Double Stop in Direct',
            (4, 3): 'Double Stop in Single Stop',
            (4, 4): 'Double Stop in Double Stop'  
        }


        return levels.get((row['Priority'], row['Best Priority']), 'Undefined')


    def calculate_level_of_service(self):
        self.data['Level of Service'] = self.data.apply(self.assign_level_of_service, axis=1)
        columns_to_drop = ['Priority', 'Best Priority']
        self.data = self.data.drop(columns=columns_to_drop)
        return self.data
    


    # def aircraft_type_and_size(self):
        
    #     aircraft_data = {
    #         '737-800': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         '747': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         '777': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         '787': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A320': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A320neo': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A321': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A330': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         'A340': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         'Embraer 190': {'Size': 'Small Aircraft', 'Type': 'Jet'},
    #         'Bombardier': {'Size': ' Aircraft', 'Type': 'Jet'},  
    #         'ATR': {'Size': 'Small Aircraft', 'Type': 'Propeller'},
    #         'A220-300': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #     }
        
       
        
    #     self.data['Aircraft Type'] = self.data['Airplane of first leg'].map(lambda x: aircraft_data.get(str(x).strip(), {}).get('Type', 'Other'))
    #     self.data['Aircraft Size'] = self.data['Airplane of first leg'].map(lambda x: aircraft_data.get(str(x).strip(), {}).get('Size', 'Unknown'))
        
    #     return self.data


    

    # def fill_known_aircraft(self, row):
        
    #     aircraft_data = {
    #         '737-800': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         '747': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         '777': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         '787': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A320': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A320neo': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A321': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #         'A330': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         'A340': {'Size': 'Large Aircraft', 'Type': 'Jet'},
    #         'Embraer 190': {'Size': 'Small Aircraft', 'Type': 'Jet'},
    #         'Bombardier': {'Size': 'Medium Aircraft', 'Type': 'Jet'},  
    #         'ATR': {'Size': 'Small Aircraft', 'Type': 'Propeller'},
    #         'A220-300': {'Size': 'Medium Aircraft', 'Type': 'Jet'},
    #     }
    #     model = row['Airplane of first leg']
    #     aircraft_info = aircraft_data.get(str(model).strip(), {})
    #     row['Aircraft Size'] = aircraft_info.get('Size', 'Unknown')
    #     row['Aircraft Type'] = aircraft_info.get('Type', 'Other')
    #     return row
    
    
    # def fill_missing_aircraft_details(self):
    #     def random_aircraft_type():
    #         # Define a list of aircraft types
    #         aircraft_types = ['737-800', '747', '777', '787', 'A320', 'A320neo', 'A321', 'A330', 'A340', 'Embraer 190', 'Bombardier', 'ATR', 'A220-300']
    #         # Choose a random type from the list
    #         return random.choice(aircraft_types)

    #     self.data['Airplane of first leg'].fillna(value=random_aircraft_type(), inplace=True)
    #     self.data = self.data.apply(lambda row: self.fill_known_aircraft(row), axis=1)
    #     return self.data
    
    
    
    # def size_category(self, row):
    #     size = row['Aircraft Size']
    #     if size == 'Small Aircraft':
    #         return (1, 0, 0)
    #     elif size == 'Medium Aircraft':
    #         return (0, 1, 0)
    #     elif size == 'Large Aircraft':
    #         return (0, 0, 1)
    #     else:
    #         return (0, 0, 0)  
        

    # def apply_size_category(self):
    #     self.data[['Small Aircraft', 'Medium Aircraft', 'Large Aircraft']] = self.data.apply(self.size_category, axis=1, result_type='expand')
    #     return self.data
    
    


    # def create_code_share_column(self):
    #     self.data['code share'] = self.data['Airline'].apply(lambda x: 1 if '->' in str(x) else 0)
    #     return self.data



    def calculate_fare_ratio(self):
        self.data.iloc[:,self. itinerary_price_col] = pd.to_numeric(self.data.iloc[:,self. itinerary_price_col] , errors='coerce')
        
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        itinerary_price_col = self.data.columns[self. itinerary_price_col]
        
        
        min_price = self.data.groupby([origin_col, destination_col])[itinerary_price_col].transform("min")
        self.data['Fare Ratio'] = self.data.iloc[:,self. itinerary_price_col] / min_price
        return self.data


    def calculate_market_average_fare_ratio(self):
        
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        
        market_avg = self.data.groupby([origin_col, destination_col])['Fare Ratio'].mean()
        return market_avg
    

    def categorize_fare(self, row, market_avg):
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        market_key = (row[origin_col], row[destination_col])
        if row['Fare Ratio'] > market_avg.get(market_key, 0):
            return pd.Series([0, 1])  # High Fare
        else:
            return pd.Series([1, 0])  # Low Fare

    def apply_fare_categorization(self):
        market_avg = self.calculate_market_average_fare_ratio()
        self.data[['Low Fare', 'High Fare']] = self.data.apply(
            lambda row: self.categorize_fare(row, market_avg),
            axis=1
        )


    def calculate_total_itineraries_per_market(self):
        
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        airline_name_col = self.data.columns[self.airline_name_col]
        
        self.data['Total Itineraries per Market'] = self.data.groupby([origin_col, destination_col])[airline_name_col].transform('count')
        return self.data

    def calculate_itineraries_per_airline_per_market(self):
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        airline_name_col = self.data.columns[self.airline_name_col]
        
        self.data['Itineraries per Airline per Market'] = self.data.groupby([origin_col, destination_col,airline_name_col])[airline_name_col].transform('count')
        return self.data

    def calculate_proportion_per_airline_per_market(self):
        self.data['Point of Sale Weighted City Presence'] = self.data['Itineraries per Airline per Market'] / self.data['Total Itineraries per Market']
        columns_to_drop = ['Total Itineraries per Market', 'Itineraries per Airline per Market']
        self.data = self.data.drop(columns=columns_to_drop)
        return self.data



    def time_to_minutes(self, time_str):
        if 'h' in time_str or 'm' in time_str:
            hours = minutes = 0
            parts = time_str.split()
            for part in parts:
                if 'h' in part:
                    hours = int(part.replace('h', ''))
                elif 'm' in part:
                    minutes = int(part.replace('m', ''))
            return hours * 60 + minutes
        return None  # Return None for 'Non', 'none', or other non-time values
    
    
    def second_shortest_times(self, group):
        sorted_times = group.dropna().sort_values()
        if len(sorted_times) > 1:
            return sorted_times.iloc[1]
        return None


    def calculate_second_shortest_transit_time(self):
        
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        duration_col = self.data.columns[self.duration_col]
        First_transit_col = self.data.columns[self.First_transit_col]
        
        time_column = First_transit_col if First_transit_col in self.data.columns else duration_col
        
        if time_column == First_transit_col:
            # Convert Transit Time into minutes
            self.data['Transit Time Minutes'] = self.data[First_transit_col].apply(lambda x: self.time_to_minutes(str(x).strip()))
            second_shortest_per_market = self.data.groupby([origin_col, destination_col])['Transit Time Minutes'].transform(self.second_shortest_times)
            self.data['Transit Time Minutes'] = self.data[First_transit_col].apply(lambda x: self.time_to_minutes(str(x).strip()))
            # Create the 'second best connection' column
            self.data['second best connection'] = (self.data['Transit Time Minutes'] == second_shortest_per_market).astype(int)
        else:
            second_shortest_per_market = self.data.groupby([origin_col, destination_col])[duration_col].transform(self.second_shortest_times)
            mask = self.data.iloc[:,self.type_col].isin(['2 Stop', '1 Stop'])
            group_data = self.data[mask].groupby([origin_col, destination_col])[time_column]
            second_shortest_per_market = group_data.transform(self.second_shortest_times)
            self.data.loc[mask, 'second best connection'] = (self.data.loc[mask, time_column] == second_shortest_per_market).astype(int)
            self.data['second best connection'].fillna(0, inplace=True)
            
        return self.data




    

    def get_time_slot(self, time_str):
        if isinstance(time_str, str):  # Check if the input is a string
            try:
                time = dt.datetime.strptime(time_str, '%H:%M:%S').time()
                # Continue with your logic to determine the time slot
                if time >= dt.time(0, 0) and time < dt.time(6, 0):
                    return "midnight–6 a.m."
                elif time >= dt.time(6, 0) and time < dt.time(9, 0):
                    return "6–9 a.m."
                elif time >= dt.time(9, 0) and time < dt.time(12, 0):
                    return "9–noon"
                elif time >= dt.time(12, 0) and time < dt.time(15, 0):
                    return "12–3 p.m."
                elif time >= dt.time(15, 0) and time < dt.time(18, 0):
                    return "3–6 p.m."
                elif time >= dt.time(18, 0) and time < dt.time(21, 0):
                    return "6–9 p.m."
                elif time >= dt.time(21, 0) or time < dt.time(1, 0):
                    return "9–midnight"
            except ValueError:
                return "Invalid time format"
        else:
            return "Non-time data"  # Handle non-string or missing values


    def apply_time_slots(self, column_name):
        self.data['Time of Day'] = self.data[column_name].apply(self.get_time_slot)
        time_slots = ['midnight–6 a.m.', '6–9 a.m.', '9–noon', '12–3 p.m.', '3–6 p.m.', '6–9 p.m.', '9–midnight']
        for slot in time_slots:
            self.data[slot] = (self.data['Time of Day'] == slot).astype(int)
        self.data.drop('Time of Day', axis=1, inplace=True)
        return self.data



    def calculate_min_distance(self):
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        distance_col = self.data.columns[self.distance_col]
        
        self.data['min_distance'] = self.data.groupby([origin_col, destination_col])[distance_col].transform('min')
        

    def calculate_distance_ratio(self):
        distance_col = self.data.columns[self.distance_col]
        self.data['Distance Ratio'] = self.data[distance_col] / self.data['min_distance']
        

    def calculate_market_average(self):
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        
        
        market_avg = self.data.groupby([origin_col, destination_col])['Distance Ratio'].mean()
        return market_avg

    def categorize_distance(self, row, market_avg):
        origin_col = self.data.columns[self.origin_col]
        destination_col = self.data.columns[self.destination_col]
        market_key = (row[origin_col], row[destination_col])
        if row['Distance Ratio'] > market_avg.get(market_key, 0):
            return pd.Series([0, 1])  # Long Distance
        else:
            return pd.Series([1, 0])  # Short Distance

    def apply_distance_categorization(self):
        market_avg = self.calculate_market_average()
        self.data[['Short Distance', 'Long Distance']] = self.data.apply(
            lambda row: self.categorize_distance(row, market_avg),
            axis=1
        )
        return self.data


    def drop_columns(self, columns_to_drop):
        self.data = self.data.drop(columns=[col for col in columns_to_drop if col in self.data.columns])

    def replace_empty_values(self):
        self.data.replace('', np.nan, inplace=True)
        # self.data.loc[self.data['From'].isna(), :] = ''
        
    def save_summary(self):
        ''' Last step exporting or Ssaving the excel file'''
        # self.data.to_excel(output_file, index=False)
        return self.data

#################################################################################################################

class ItineraryAnalyzer:
    def __init__(self, Itineraries_df__edited):
        self.data = Itineraries_df__edited
        self.group_columns = ['Level of Service', 
                              'second best connection', 'midnight–6 a.m.', '6–9 a.m.', '9–noon', '12–3 p.m.', '3–6 p.m.',
                              '6–9 p.m.', '9–midnight','Short Distance', 'Long Distance','Low Fare', 'High Fare']
        
        # self.group_columns = ['Level of Service', 'Small Aircraft' , 'Medium Aircraft', 'Large Aircraft', 
        #                       'second best connection', 'midnight–6 a.m.', '6–9 a.m.', '9–noon', '12–3 p.m.', '3–6 p.m.',
        #                       '6–9 p.m.', '9–midnight','Short Distance', 'Long Distance','Low Fare', 'High Fare']
        
        self.summary_columns = ['ID Common itineraris'] + self.group_columns + ['count']
        
    # def read_data(self):
    #     self.data = pd.read_excel(self.file_path)
        
    def create_itinerary_id(self):
        self.data['ID Common itineraris'] = self.data.groupby(self.group_columns).ngroup()
        
    def count_unique_itineraries(self):
        id_counts = self.data['ID Common itineraris'].value_counts().reset_index()
        id_counts.columns = ['ID Common itineraris', 'count']
        unique_itineraries = self.data.drop_duplicates(subset='ID Common itineraris')
        self.summary_df = unique_itineraries.merge(id_counts, on='ID Common itineraris')

        
    def save_summary(self):
        # self.summary_df.to_excel(output_file, index=False)
        
        return self.summary_df
    
#################################################################################################################

class propabilities_and_demand:
    
    def __init__(self,Itineraries_df__edited,betas_df,airline_name_col,origin_col,departure_col,arrival_col,destination_col) :
        
        self.Itineraries_df__edited = Itineraries_df__edited
        self.airline_name_col = airline_name_col
        self.betas_df = betas_df
        self.origin_col = origin_col # From
        self. destination_col = destination_col # To 
        self. departure_col = departure_col
        self. arrival_col = arrival_col
        
    
    def Itineraries_filter_for_demand(self):
        ''' Getting data ready for probability calculation'''
        
        self.df_columns_to_keep_2 = self.Itineraries_df__edited.iloc[:,[self.airline_name_col,self.origin_col,self.departure_col,self.destination_col,self.arrival_col,]]
        
        columns_to_keep = ['Itinerary ID','Level of Service','Low Fare','High Fare', 'Point of Sale Weighted City Presence', 'second best connection','midnight–6 a.m.','6–9 a.m.','9–noon','12–3 p.m.','3–6 p.m.','6–9 p.m.','9–midnight', 'Short Distance', 'Long Distance', 'ID Common itineraris', 'count']
        self.Itineraries_df__edited = self.Itineraries_df__edited.filter(columns_to_keep)
        
        
        Level_of_Service_spread = pd.get_dummies(self.Itineraries_df__edited['Level of Service'],drop_first=False)
        
        self.Itineraries_df__edited.drop(['Level of Service'],axis=1,inplace=True)
        
        self.Itineraries_df__edited = pd.concat([Level_of_Service_spread,self.Itineraries_df__edited],axis=1)
        
        self.Itineraries_df__edited.to_excel('Itineraries_for_deman.xlsx', index=False)
        
        
        
    def Utility_calculation(self,betas_file, output_file= 'Utility_calculation.xlsx'):
        
        # Load the Excel files
        self.df_values = self.Itineraries_df__edited
        
        df_betas = betas_file

        # Assuming that the beta values are in the same order and there's only one row of betas
        betas = df_betas.iloc[0]  # Take the first row if multiple rows of betas exist

        # Ensure that the columns in df_values are in the same order as in df_betas
        self.df_values = (self.df_values)[betas.index]
        
        # Element-wise multiplication
        result = self.df_values * betas

        # Sum the multiplied values in each row
        self.df_values["Utility Values"] = result.sum(axis=1)  # axis=1 for row-wise summation

        # Save the summed results to a new Excel file
        self.df_values.to_excel(output_file, index=False)

        # print(f"Utility results saved to {output_file}")

        # Example usage:
        # multiply_by_betas_and_sum('values.xlsx', 'betas.xlsx', 'summed_output.xlsx')
    
    def probability_calculation(self):
        
        self.df_values = pd.concat([self.df_columns_to_keep_2,self.df_values],axis=1 )
        
        
         # Compute the exponential of the utility values for each row
        self.df_values['Exp_Utility'] = np.exp(self.df_values['Utility Values'])

        # Group by the market ('From', 'To') and calculate the sum of exponentials for each market
        
        origin_col = self.df_values.columns[self.origin_col]
        destination_col = self.df_values.columns[self.destination_col]
        # print(origin_col,destination_col)
        sum_exp_utilities = self.df_values.groupby([origin_col, destination_col])['Exp_Utility'].transform('sum')

        # Calculate the probability of each itinerary within its market
        
        self.df_values['Probability'] = self.df_values['Exp_Utility'] / sum_exp_utilities

        # self.df_values.drop(['Exp_Utility'])
        self.df_values['exp_sum'] =  sum_exp_utilities
        self.df_values.to_excel('probability.xlsx', index=False)
        
    def calculate_qsi_hhi(self):
        # Group by market and airline, and calculate the total probability for each group
        self.origin_col_name = self.df_values.columns[self.origin_col]
        self.destination_col_name= self.df_values.columns[self.destination_col]
        self.airline_col_name= self.df_values.columns[self.airline_name_col]
        
        airline_group = self.df_values.groupby([self.origin_col_name, self.destination_col_name, self.airline_col_name])['Probability'].sum().reset_index(name='Airline Probability')

        # Group by market and calculate the total probability for each market
        market_total = self.df_values.groupby([self.origin_col_name, self.destination_col_name])['Probability'].sum().reset_index(name='Market Total Probability')

        # Merge the airline and market total dataframes
        merged_df = pd.merge(airline_group, market_total, on=[self.origin_col_name, self.destination_col_name])

        # Calculate QSI for each airline in each market
        merged_df['QSI'] = merged_df['Airline Probability'] / merged_df['Market Total Probability']

        # Calculate HHI for each market
        merged_df['QSI Squared'] = merged_df['QSI'] ** 2
        self.qsi = merged_df[[self.origin_col_name,self.destination_col_name, self.airline_col_name, 'QSI']]
        self.hhi = merged_df.groupby([self.origin_col_name, self.destination_col_name])['QSI Squared'].sum().reset_index(name='HHI')
        
        # print(f'hhi : {self.hhi}\n\n')
        return self.qsi, self.hhi
    
    def empty_unconstrained_demand(self):
        # print(f'hhi : {self.hhi}\n\n')
        empty_unconstrained_demand_df=self.hhi.iloc[:,[0,1]].copy()
        # print(empty_unconstrained_demand_df)
        empty_unconstrained_demand_df['Unconstrained_demand']=0
        
        return empty_unconstrained_demand_df
        

    def demand_calculation(self, unconstrained_demand_df):       
        
        Unconstrained_demand_df = unconstrained_demand_df

        # Merging the DataFrames on 'From' and 'To' columns
        
        self.merged_df = pd.merge(self.df_values, Unconstrained_demand_df, on=[self.origin_col_name,self.destination_col_name], how='left')
        
        self.merged_df['Itinerary no'] = range(1, len(self.merged_df) + 1)
        
        self.merged_df['Demand'] =( self.merged_df['Probability']  * self.merged_df['Unconstrained_demand']).apply(np.floor)
        # merged_df.to_excel('DEMAAAAND.xlsx',index=False)
        
        # print(f'\n\n merged_df: {self.merged_df} \n\n')
        
    
    def get_demand_dataframe(self):
        return self.merged_df
    
#################################################################################################################

warnings.simplefilter(action='ignore', category=FutureWarning)

class regression_coefficients():
    
    def __init__(self, Itineraries_df__edited):
        self.Itineraries_df__edited_df = Itineraries_df__edited
        
        
        # print(self.Itineraries_df__edited_df.head())
        
        
    def data_filter(self):
        ''' Getting data ready for regression calculation'''
        
        
        
        columns_to_keep = ['Itinerary ID','Level of Service', 'Low Fare','High Fare', 'Point of Sale Weighted City Presence', 'second best connection','midnight–6 a.m.','6–9 a.m.','9–noon','12–3 p.m.','3–6 p.m.','6–9 p.m.','9–midnight', 'Short Distance', 'Long Distance', 'count']
        self.Itineraries_features = self.Itineraries_df__edited_df.filter(columns_to_keep)
        
        
        Level_of_Service_spread = pd.get_dummies(self.Itineraries_features['Level of Service'],drop_first=False)
        
        self.Itineraries_features.drop(['Itinerary ID','Level of Service'],axis=1,inplace=True)
        
        self.Itineraries_features = pd.concat([Level_of_Service_spread,self.Itineraries_features],axis=1)
        
        
    def regression_calculation(self):
        ''' Calculation of betas'''
        
        self.Itineraries_features.to_excel('Data.xlsx')
        y =  self.Itineraries_features['count']
        X =  self.Itineraries_features.drop(['count'],axis=1)
        
        
        clf = linear_model.PoissonRegressor()
        clf.fit(X, y)
        
        Data_score= clf.score(X, y)*100
        mean = np.mean(y)
        std = np.std(y)
        self.coefficients = clf.coef_
        # print(f' Data score = {Data_score } %, mean = {mean}, std = {std} \n')

        
        
    def save_coefficients_to_excel(self, filename='Historical_data_betas.xlsx'):
        ''' Save coefficients to Excel file'''
        column_names = ['Double Stop in Double Stop',	'Double Stop in Non Stop',	'Non Stop in Non Stop',	'Single Stop in Non Stop',	'Single Stop in Single Stop',	'Low Fare',	'High Fare',	'Point of Sale Weighted City Presence',	'second best connection',	'midnight–6 a.m.',	'6–9 a.m.',	'9–noon',	'12–3 p.m.',	'3–6 p.m.',	'6–9 p.m.',	'9–midnight',	'Short Distance',	'Long Distance']
        df_coefficients = pd.DataFrame([self.coefficients], columns=column_names)
        df_coefficients.to_excel(filename, index=False)
        return df_coefficients

        
    
        
        