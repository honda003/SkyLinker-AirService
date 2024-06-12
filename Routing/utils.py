import pandas as pd
import re
from io import BytesIO
import io
from datetime import datetime, timedelta
import pandas as pd
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
    
class ColumnIndex:
    def __init__(self, flights_pd):
        self.flights_pd = flights_pd
        self.column_name_mappings = {
            "flight number": ['Flight', 'flight', 'Flights', 'flights', 'Flight Number', 'flight number', 'FlightNumber', 'flightnumber'],
            "origin": ['Origin', 'origin', 'FROM', 'from', 'From'],
            "departure": ['Departure', 'departure', 'dep', 'departuretime', 'DepartureTime', 'departure time'],
            "destination": ['Destination', 'destination', 'DESTINATION', 'dest', 'TO', 'to', 'To', 'Dest'],
            "arrival": ['Arrival', 'arrival', 'arr', 'arrivaltime', 'ArrivalTime', 'arrival time'],
            "flight duration": ['flight duration', 'Flight Duration', 'Duration', 'duration', 'DURATION', 'flightduration', 'FlightDuration','FLIGHTDURATION'],
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
        elif column_type in ['flight duration']:
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
    
    
###############################################################################################################

class MaxFpd:
    def __init__(self, one_day_flights, departure, arrival, TAT):
        self.departure = departure
        self.arrival = arrival
        self.TAT = TAT
        self.sorted_flights = sorted((i, dep) for i, dep in enumerate(departure))
        self.max_fpd = self.calculate_max_fpd()

    def calculate_max_fpd(self):
        last_end_time = 0
        max_fpd = 0
        for flight_idx, _ in self.sorted_flights:
            if self.departure[flight_idx] >= last_end_time + self.TAT:
                last_end_time = self.arrival[flight_idx]
                max_fpd += 1
        return max_fpd

    def get_max_fpd(self):
        return self.max_fpd
    
    
    #################################################################################################
    
class CombinationsGenerator:
    def __init__(self, user_decided_fpd, days_in_cycle):
        self.user_decided_fpd = user_decided_fpd
        self.days_in_cycle = days_in_cycle
        self.max_fpd = self.user_decided_fpd
        self.digits = list(range(1, self.max_fpd + 1))
        self.combos = self.generate_combinations()

    def generate_combinations(self):
        def generate_combinations_recursive(curr_combo, depth):
            if depth == 0:
                return [curr_combo.copy()]
            combos = []
            for digit in self.digits:
                curr_combo.append(digit)
                combos.extend(generate_combinations_recursive(curr_combo, depth - 1))
                curr_combo.pop()
            return combos
        return generate_combinations_recursive([], self.days_in_cycle)

    def get_combos(self):
        return self.combos
    
################################################################################

class FlightPerDay:  
    def __init__(self, fpd):
        if not 0 < fpd <= 5:
            raise ValueError(f"Flights per day must be between 1 and {fpd}")
        self.fpd = fpd
    
    def get_fpd(self):
        return self.fpd
    
################################################################################


class FpdSchedule:
    def __init__(self, one_day_flights, fpd, departure, arrival, TAT, origin_col, destination_col):
        """
        Initializes the FpdSchedule object with flight details and scheduling constraints.
        
        Parameters:
        - one_day_flights: List of flight details for one day.
        - fpd: Integer, flights per day constraint.
        - departure: List of departure times for each flight.
        - arrival: List of arrival times for each flight.
        - TAT: Integer, minimum turn-around time required between flights.
        - origin_col: Integer, column index for the flight's origin.
        - destination_col: Integer, column index for the flight's destination.
        """
        self.__One_Day_Flights = one_day_flights
        self.__fpd = fpd
        self.__departure = departure
        self.__arrival = arrival
        self.__TAT = TAT
        self.__origin_col = origin_col
        self.__destination_col = destination_col
        self.__schedules = []
        
        while self.__schedules == []:
            
            if self.__fpd == 1:
                self.__schedules = self.__One_Day_Flights
                
            elif self.__fpd > 1:
                
                for n in range(1, self.__fpd):
                    current_schedule = [] 
                    
                    if self.__schedules == []:
                        
                        for i in range(len(self.__One_Day_Flights)):
                            prev_flight = self.__One_Day_Flights[i]

                            for j in range(len(self.__One_Day_Flights)):
                                current_flight = self.__One_Day_Flights[j]

                                if prev_flight[self.__destination_col] == current_flight[self.__origin_col]:
                                    if self.__departure[j] - self.__arrival[i] >= self.__TAT:
                                        current_schedule.append(prev_flight)
                                        current_schedule.append(current_flight)
                                        
                        self.__schedules = current_schedule
                    
                    else:
                        n_arriv = []
                        for m in range(n-1, len(self.__schedules), n):
                            prev_flight = self.__schedules[m]
                            for i in range(len(self.__One_Day_Flights)):
                                if self.__schedules[m] == self.__One_Day_Flights[i]:
                                    n_arriv = self.__arrival[i]
                                
                            for j in range(len(self.__One_Day_Flights)):
                                current_flight = self.__One_Day_Flights[j]

                                if prev_flight[self.__destination_col] == current_flight[self.__origin_col]:
                                    if self.__departure[j] - n_arriv >= self.__TAT:
                                        current_schedule.extend(self.__schedules[m - n + 1 : m + 1])
                                        current_schedule.append(current_flight)
                        self.__schedules = current_schedule
                    # Append the current schedule to self.__schedules
                    
                    if not self.__schedules:
                        self.__fpd -= 1  # Decrease fpd by 1
                        self.__is_empty = True
                        break  # Break out of the loop as a non-empty schedule is obtained
            

    def get_schedule(self):
        return self.__schedules
            
    def get_schedule_rows(self):
        return len(self.__schedules)
    
    def get_schedule_columns(self):
        return len(self.__schedules[0])
    

##################################################################

def process_combos(combos, one_day_flights, departure, arrival, TAT, origin_col, destination_col, hubs, days_no, fpd):
    total = 0
    valid_combos = []
    all_options_lists = []
    m = []

    for combo in combos:
        Schedule = []
        schedule_columns = []
        schedule_rows = []
        rows_tot = 0
        Routes = []

        # Generating Routes Starts here
        for day in range(1, days_no + 1):
            fpd_instance = FlightPerDay(combo[day - 1])
            fpd = fpd_instance.get_fpd()
            Schedule_instance = FpdSchedule(one_day_flights=one_day_flights, fpd=fpd, departure=departure, arrival=arrival, TAT=TAT, origin_col=origin_col, destination_col=destination_col)
            Schedule.append(Schedule_instance.get_schedule())
            schedule_columns.append(Schedule_instance.get_schedule_columns())
            schedule_rows.append(Schedule_instance.get_schedule_rows())
            rows_tot += Schedule_instance.get_schedule_rows()

            #print(f"Day {day} Schedule: {Schedule[-1]}")

        # Create a list to hold the indices of the loops for each day
        loop_indices = [range(0 + combo[d] - 1, schedule_rows[d], combo[d]) for d in range(days_no)]
        #print(f"Loop Indices for combo {combo}: {loop_indices}")

        # Use itertools.product to create all combinations of loop indices
        for indices in itertools.product(*loop_indices):
            valid_combo = True
            #print(f"Checking combination: {indices}")

            for d in range(days_no):
                next_day_indices = [(indices[i] - combo[i] + 1) % schedule_rows[i] for i in range(days_no)]
                current_dest = Schedule[d][indices[d]][destination_col]
                next_origin = Schedule[(d + 1) % days_no][next_day_indices[(d + 1) % days_no]][origin_col]
                #print(f"Day {d+1} transition: current dest {current_dest} to next day origin {next_origin}")

                if current_dest != next_origin:
                    valid_combo = False
                    #print(f"Invalid transition from day {d+1} to day {(d+2) % days_no}")
                    break

            if valid_combo:
                #print(f"Valid combo found: {combo} with indices {indices}")
                for hub in hubs:
                    if any(Schedule[d][indices[d]][destination_col] == hub for d in range(days_no)):
                        valid_combos.append(combo)
                        for d in range(days_no):
                            for idx in range(indices[d] - combo[d] + 1, indices[d] + 1):
                                Routes.append(Schedule[d][idx])

                        m.append(sum(1 for d in range(days_no) if Schedule[d][indices[d]][destination_col] == hub))

        options_length = int(len(Routes) / sum(combo))
        total += options_length

        if options_length != 0:
            sublists = [Routes[i:i + int(len(Routes) / options_length)] for i in range(0, len(Routes), int(len(Routes) / options_length))]
            all_options_lists.extend(sublists)

    # print(f"\n\n combos {combos} \n\n")
    # print(f"\n\n one_day_flights {one_day_flights} \n\n")
    # print(f"\n\n departure {departure} \n\n")
    # print(f"\n\n arrival  {arrival} \n\n")
    # print(f"\n\n TAT  {TAT} \n\n")
    # print(f"\n\n origin_col  {origin_col} \n\n")
    # print(f"\n\n destination_col  {destination_col} \n\n")
    # print(f"\n\n hubs  {hubs} \n\n")
    # print(f"\n\n days_no  {days_no} \n\n")
    # print(f"\n\n FPD {fpd} \n\n")
    # print(f"\n\n Schedule {Schedule} \n\n")
    # print(f"\n\n Valid Combos {valid_combos} \n\n")
    # print(f"\n\n m {m} \n\n")
    # print(f"\n\n all_options_lists {all_options_lists} \n\n")
            
    data = []

    for flight in one_day_flights:
            for days in range(len(combo)):
                b = 0
                for option, combo in zip(all_options_lists, valid_combos):
                    c = 0
                    if days == 0:
                        for a in range(0, combo[days]):
                            if flight[0] == option[a][0]:
                                data.append({
                                    'Day': days + 1,
                                    'Route': b,
                                    'Flight Number': flight[0],
                                    'X': b
                                })
                    else:
                        c += sum(combo[0:days])
                        for a in range(c, c + combo[days]):
                            if flight[0] == option[a][0]:
                                data.append({
                                    'Day': days + 1,
                                    'Route': b,
                                    'Flight Number': flight[0],
                                    'X': b
                                })
                    b += 1
                        
    # Create a DataFrame from the data
    
    
    return valid_combos, all_options_lists, total, m, data


######################################################################################
def convert_time_to_minutes(time_str):
    """Converts a time string to minutes since midnight, allowing for >24 hours."""
    try:
        if ':' in time_str and time_str.count(':') == 2:
            time_format = '%H:%M:%S'
        else:
            time_format = '%H:%M'
        time_obj = datetime.strptime(time_str, time_format)
        return time_obj.hour * 60 + time_obj.minute
    except ValueError:
        # Handle time strings that go beyond 24:00
        if time_str.startswith('24:'):
            # Replace '24:' with '00:' and add 24 hours worth of minutes
            time_str = '00:' + time_str[3:]
            time_obj = datetime.strptime(time_str, '%H:%M')
            return 24 * 60 + time_obj.minute
        else:
            raise

def convert_minutes_to_time(minutes):
    """Converts minutes since midnight to a time string, allowing for >24 hours."""
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        hours -= 24  # Adjust hours if they are >= 24
    return f"{int(hours):02d}:{int(minutes):02d}"

def analyze_flight_schedule(flights_df, TAT_minutes, flight_number_index, origin_index, departure_index, arrival_index, destination_index, flight_duration_index):
    """Analyzes the flight schedule to find infeasibilities and suggest delays within a 3-hour limit."""
    suggestions = []
    original_flights_df = flights_df.copy()  # Keep a copy of the original schedule for reference
    flights_df = flights_df.sort_values(by=flights_df.columns[departure_index])  # Sort by 'Departure' column

    for idx, current_flight in original_flights_df.iterrows():
        # Accessing data using iloc
        current_flight_ready_time = convert_time_to_minutes(current_flight.iloc[arrival_index]) + TAT_minutes

        next_flights = original_flights_df[(original_flights_df.iloc[:, origin_index] == current_flight.iloc[destination_index]) & (original_flights_df.index > idx)]
        for _, next_flight in next_flights.iterrows():
            next_flight_departure = convert_time_to_minutes(next_flight.iloc[departure_index])
            delay_needed = current_flight_ready_time - next_flight_departure

            if delay_needed > 0:
                new_departure_time_minutes = current_flight_ready_time
                # Access 'Flight Duration' using iloc
                flight_duration_minutes = next_flight.iloc[flight_duration_index] * 60  # Convert hours to minutes
                new_arrival_time_minutes = new_departure_time_minutes + flight_duration_minutes

                if delay_needed <= 180:
                    suggestions.append({
                        'Flight Number': next_flight.iloc[flight_number_index],
                        'Current Departure': next_flight.iloc[departure_index],
                        'Suggested Departure': convert_minutes_to_time(new_departure_time_minutes),
                        'Current Arrival': next_flight.iloc[arrival_index],
                        'Suggested Arrival': convert_minutes_to_time(new_arrival_time_minutes),
                        'Reason': 'Insufficient turnaround time for aircraft, requiring a delay within 3 hours.',
                        'Conflict With Flight Number': current_flight.iloc[flight_number_index],
                        'Conflict Arrival Time': current_flight.iloc[arrival_index],
                        'Delay Needed': delay_needed
                    })

    return suggestions

def optimization(flights_df, TAT_minutes, all_options_lists, m, data, valid_combos, number_of_aircrafts, flight_number_index, origin_index, departure_index, arrival_index, destination_index, flight_duration_index):

    # Integration of Part 3 starts here
    model = pyo.ConcreteModel()
    if all_options_lists != []:
        model.x = pyo.Var(range(len(all_options_lists)), within=Integers, bounds=(0, 1))
        x = model.x
        
        #print(f"\n\n Options {all_options_lists} \n\n")
        # Assuming m is defined and accessible. If not, you need to define or calculate it before this point.
        model.obj = pyo.Objective(expr=sum(m[i] * x[i] for i in range(len(all_options_lists))), sense=maximize)
        
        model.C1 = pyo.ConstraintList()
        x_values_by_key = {}
        for item in data:
            day_flight_key = (item['Day'], item['Flight Number'])
            if day_flight_key in x_values_by_key:
                x_values_by_key[day_flight_key].append(item['X'])
            else:
                x_values_by_key[day_flight_key] = [item['X']]

        for key, x_values in x_values_by_key.items():
            model.C1.add(expr=sum(x[index] for index in x_values) == 1)
        
        ac_availabe = number_of_aircrafts
        model.C2 = pyo.Constraint(expr=sum(x[i] for i in range(len(all_options_lists))) <= ac_availabe)
        
        opt = SolverFactory('glpk')
        results = opt.solve(model)
        
        # Check if the solution is feasible
        if results.solver.status == SolverStatus.ok and results.solver.termination_condition == TerminationCondition.optimal:
            # Initialize the list for optimized data
            optimized_data = []

            for i, (option, combo) in enumerate(zip(all_options_lists, valid_combos)):
                current_index = 0
                if pyo.value(x[i]) == 1:
                    for day_index, day_value in enumerate(combo, start=1):
                        flights_data = []
                        for _ in range(day_value):
                            if current_index < len(option):
                                # Create a dictionary for each flight's data
                                flight_data_dict = {
                                    'FlightNumber': option[current_index][flight_number_index],
                                    'Origin': option[current_index][origin_index],
                                    'Departure': option[current_index][departure_index],
                                    'Destination': option[current_index][destination_index],
                                    'Arrival': option[current_index][arrival_index],
                                    'Duration': option[current_index][flight_duration_index],
                                    'FleetType': option[current_index][6],
                                }
                                
                                flights_data.append(flight_data_dict)
                                current_index += 1
                        # Append a dictionary for each day, including the flights data
                        optimized_data.append({
                            'RouteNumber': i + 1,
                            'Day': day_index,
                            'FlightsData': flights_data
                        })

            # Create DataFrame for non-nested data
            df_base = pd.DataFrame(optimized_data, columns=['RouteNumber', 'Day'])

            # Extract FlightsData as a list of DataFrames, then concatenate horizontally
            flights_data_frames = [pd.DataFrame(data['FlightsData']) for data in optimized_data if data['FlightsData']]
            df_flights = pd.concat(flights_data_frames, keys=range(len(flights_data_frames)), names=['FlightSet', 'FlightIndex'])

            # Reset index to align with df_base
            df_flights = df_flights.reset_index(level='FlightSet').rename(columns={'FlightSet': 'Index'})

            # Merge the base DataFrame with flights data
            Output_df = pd.merge(df_base, df_flights, left_index=True, right_on='Index', how='left').drop(columns=['Index'])
            
            # Generate the routing results summary
            routing_results = []
            unique_route_numbers = Output_df['RouteNumber'].unique()
            c = 1
            for route in unique_route_numbers:
                route_df = Output_df[Output_df['RouteNumber'] == route]
                route_summary = f"Your AC {c} of type {route_df.iloc[0]['FleetType']} should fly the route number {route}\n"
                unique_days = route_df['Day'].unique()
                
                for day in unique_days:
                    day_df = route_df[route_df['Day'] == day]
                    route_summary += f"Starting Day {day}, "
                    
                    for i, flight in day_df.iterrows():
                        if i == day_df.index[0]:
                            route_summary += f"By making Flight Number {flight['FlightNumber']} From {flight['Origin']} at {flight['Departure']} To {flight['Destination']} at {flight['Arrival']}\n"
                        else:
                            route_summary += f"Followed by Flight Number {flight['FlightNumber']} From {flight['Origin']} at {flight['Departure']} To {flight['Destination']} at {flight['Arrival']}\n"
                    
                    route_summary += "\n"  # Add a newline for spacing between days
                    
                c += 1
                
                routing_results.append(route_summary)
            
            # Combine all routing results into a single string
            routing_results_str = "\n".join(routing_results)
            
            return pyo.value(model.obj), Output_df, routing_results_str, True, "Optimization successful"
        
        elif results.solver.termination_condition == TerminationCondition.infeasible:
            # Assuming flights_df is a DataFrame constructed from the flight data
            suggestions = analyze_flight_schedule(flights_df, TAT_minutes, flight_number_index, origin_index, departure_index, arrival_index, destination_index, flight_duration_index)

            # Initialize message before appending to it
            message = "No feasible solution found for the given constraints.\nWe advice to make the following:\n\nIncrease number of aircrafts.\n\nOr\n\n"
            # Convert suggestions to a user-friendly format
            for suggestion in suggestions:
                message += f"Flight {suggestion['Flight Number']} should be delayed. Current departure at " \
                        f"{suggestion['Current Departure']} is not feasible. Suggest new departure at " \
                        f"{suggestion['Suggested Departure']} and new arrival at {suggestion['Suggested Arrival']}.\n" \
                        f"Reason: {suggestion['Reason']}, Conflict with Flight {suggestion['Conflict With Flight Number']} arriving at {suggestion['Conflict Arrival Time']}.\n\n"
            
            return 0, None, message, False, "No feasible solution"
        else:
            # Handle other cases such as solver failure
            return 0, None, "Solver failed to find a solution.", False, "Solver failure"
    else:
        return 0, None, "Solver failed to find a solution.", False, "The entered number of flights per day is insufficient for the required operational capacity based on the provided schedule"