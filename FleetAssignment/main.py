import pyomo.environ as pyo
from pyomo.environ import *
from pyomo.opt import SolverFactory
import pandas as pd
import numpy as np
from .utils import FlightColumnIndex, ItinColumnIndex, ClockToMinutes, FlightsCategorization, NodesGenerator, VariableY, VariableZ, spilled_and_captured_variables, flights_oeprating_costs, DemandCorrection


# ****************** Read Excel **************** #
# Paths of the data files
flights_data_filepath = "flights 3.xlsx"
fleets_data_filepath = "fleets 3.xlsx"
itineraries_data_filepath="itineraries 3 .xlsx"


# Read data files
flights_df = pd.read_excel(flights_data_filepath)
fleets_df = pd.read_excel(fleets_data_filepath)
itineraries_df= pd.read_excel(itineraries_data_filepath)


# ****************** Recapture ratio bpr **************** #
recapture_ratio = 0.9


# ****************** Find Flights columns **************** #
Flight_Column_index =  FlightColumnIndex(flights_df)
flight_no_col = Flight_Column_index.get_flight_number_column()
origin_col = Flight_Column_index.get_origin_column()
departure_col = Flight_Column_index.get_departure_column()
destination_col = Flight_Column_index.get_destination_column()
arrival_col = Flight_Column_index.get_arrival_column()
distance_col = Flight_Column_index.get_distance_column()
duration_col = Flight_Column_index.get_duration_column()


# ****************** Find Itinerary columns **************** #
itinerary_column_index = ItinColumnIndex(itineraries_df)
itinerary_no_col = itinerary_column_index.get_itinerary_number_column()
demand_col = itinerary_column_index.get_demand_column()
fare_col = itinerary_column_index.get_fare_column()
flights_col = itinerary_column_index.get_flights_column()
type_col = itinerary_column_index.get_type_column()


# list of our stations
station_list = np.unique(flights_df.iloc[:, origin_col].to_list())       # list of stations
flights_list = flights_df.iloc[:, flight_no_col].astype(str).tolist()    #List of flights
fleet_list = fleets_df['FleetType'].tolist()                 #List of fleet


# ****************** Convert time to minutes **************** #
dep_arriv = ClockToMinutes(flights_df, departure_col, arrival_col)
dep = dep_arriv.get_departure_minutes()
arriv = dep_arriv.get_arrival_minutes()

    
# ****************** Generate Balance Nodes **************** #
Nodes_df_instance = NodesGenerator(flights_df, station_list, flight_no_col, origin_col, destination_col, departure_col, arrival_col, dep, arriv)
Nodes_df = Nodes_df_instance.get_nodes()


# ****************** Ground Arc Variable (Y) **************** #
var_y_instance = VariableY(Nodes_df, station_list, fleet_list)
var_y = var_y_instance.get_y()
print(f'Variable Y:\n{var_y}\n')

# ****************** Number of Available ACs **************** #
Ne = {}
for number_of_airplane in range(len(fleets_df)):
    Ne[fleets_df.iloc[number_of_airplane]['FleetType']] = fleets_df.iloc[number_of_airplane]['NumberOfAirCrafts']
print(f'Number of Aircrafts:\n{Ne}\n')
    

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
cost_list= flights_costs.given_operating_cost(distance_col)
cost_list = [30000,16600,15100,13500,15500,45000,57000,13500,42000,16600,15500,45000]  #######################TAKECARE##################

# Creating the dictionary which has the flight,fleet as key equals to value from cost_list
C_fe = {}
cost_list_counter = 0
for i in model.setF:
    for j in model.setE:
        C_fe[f'{i},{j}'] = cost_list[cost_list_counter]
        cost_list_counter += 1
print(f'Cost List C_fe:\n{C_fe}\n')
        

# ****************** Find Optional Flights **************** #
ask_optional = input('Do you have optional flights? [Y/N]')
if ask_optional.lower() == 'n':
    flights_df['Optional'] = 0  # Set the entire column to 0 if there are no optional flights
else:
    optional_flight = input('Enter the optional flight numbers separated by comma(,): ')
    optional_flight_list = optional_flight.split(',')
    flights_df['Optional'] = flights_df.apply(lambda row: 1 if str(row[flight_no_col]) in optional_flight_list else 0, axis=1)

cat = FlightsCategorization(flights_df, flight_no_col)
optional_flights = cat.optional_flights
non_optional_flights = cat.non_optional_flights
print(f'Optional Flights:\n{optional_flights}\n')
print(f'Non Optional Flights:\n{non_optional_flights}\n')


# ****************** Define non/Optional Flight Sets**************** #
model.setF_optional = pyo.Set(initialize = optional_flights)             # set of optional flights
model.setF_non_optional = pyo.Set(initialize = non_optional_flights )    # set of non optional flights


# ****************** Find Optional Itineraries **************** #
optional_itineraries=[]
for idx, itn in itineraries_df.iterrows():
    for opt_flight in optional_flights:
        if str(opt_flight) in (str(itn[3]).split(", ")) and itn[0] not in optional_itineraries :
            optional_itineraries.append(itn[0])
print(f'Optional Itineraries:\n{optional_itineraries}\n')
            
            
# ****************** Define non/Optional Itinerary Sets**************** #
model.setp = pyo.RangeSet(len(itineraries_df))                            # set of itenraries
model.setp_optional=pyo.Set(initialize=optional_itineraries)                # set of optional itenraries


# ****************** Generate Zq Decision Variable**************** #
def optional_df(itineraries_df, optional_itineraries, itinerary_no_col):
    # Iterate over each row of the DataFrame
    for idx in range(len(itineraries_df)):
        # Check if the itinerary is in the list of optional itineraries
        if itineraries_df.iat[idx, itinerary_no_col] in optional_itineraries:
            # Set the 'Optional' column to 1 for this row
            itineraries_df.at[idx, 'Optional'] = 1
            
    itineraries_df.fillna(0,inplace = True)

    return itineraries_df
        
optional_dfs = optional_df(itineraries_df, optional_itineraries, itinerary_no_col)     
var_z = VariableZ(itineraries_df, itinerary_no_col)
var_z = var_z.get_z()
if var_z is not None:
    model.z = pyo.Var(var_z, within = Binary, bounds = (0,1))
print(f'Variable Z:\n{var_z}\n')

# ****************** Define spilled passenger from itinerary p (tp) **************** #
itineraries_demand_list =itineraries_df.iloc[:, demand_col].tolist() # Get column of demand from itenraries dataframe and convert to list
model.t_spilled = pyo.Var(model.setp, within=pyo.Integers, bounds=lambda model, i: (0, itineraries_demand_list[i-1]))
t_spilled=model.t_spilled


# ****************** Define spilled passenger from itinerary p and recaptured by itinerary r (tpr) **************** #
data1=spilled_and_captured_variables(flights_df)
itineraries_df=spilled_and_captured_variables.Itinraries_df_simplify(data1,itineraries_df,itinerary_no_col, flights_col, flight_no_col, origin_col, destination_col,type_col)

itineraries_df.iloc[:, itinerary_no_col] = itineraries_df.iloc[:, itinerary_no_col].astype('int64')
spilled_recaptured_vars=spilled_and_captured_variables.spill_recaptured_variables_list(data1, itineraries_df, itinerary_no_col)
print(f"Variable t_p_r:\n{spilled_recaptured_vars}")

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
print(f'Itinerary Data Frame:\n{itineraries_df}\n')


# ****************** Define Demand correction variable Delta Dqp **************** #
demand_correction = DemandCorrection(itineraries_df, optional_itineraries, optional_flight, itinerary_no_col, flights_col, demand_col)
demand_correction_factor_df = demand_correction.get_demand_correction_df()
print(f'Demand Correction Factor:\n{demand_correction_factor_df}\n')

#__C__Operating costs
C_Operating_cost=sum(C_fe[f"{f},{e}"] * model.x[f, e] for f in model.setF for e in model.setE)
print(f'Operating Cost (C):\n{C_Operating_cost}\n')
 
        
# ****************** Calculate Unconstrained Revenue (R) **************** #
R_Unconstrained_Revenue=sum(itineraries_df.iloc[idx, demand_col] * itineraries_df.iloc[idx, fare_col] for idx in range(len(itineraries_df)))
print(f'Unconstrained Revenue (R):\n{R_Unconstrained_Revenue}\n')


# ****************** Calculate Spill Cost (S) **************** #
S_Spill_Cost=sum(model.spilled_recaptured_vars[t_p_r] * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[1])).values , fare_col].values[0] for t_p_r in spilled_recaptured_vars)

print(f'Spill Cost (S):\n{S_Spill_Cost}\n')


# ****************** Calculate Recaptured Revenue (M) **************** #
M_Recaptured_Revenue=sum(model.spilled_recaptured_vars[t_p_r] * recapture_ratio * itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == int(t_p_r.split('_')[2])).values , fare_col].values[0] 
            if t_p_r.split('_')[1] == str(r) and int(t_p_r.split('_')[2]) != len(itineraries_df)+1  
            else 0 
            for t_p_r in spilled_recaptured_vars   
            for r in model.setp.data())
print(f'Recaptured Revenue (M):\n{M_Recaptured_Revenue}\n')


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
    (1 - model.z[f'z_{opt_iten}'])
    for opt_iten in optional_itineraries
)

print(f'Unconstrained Revenue Loss (Delta R):\n{DeltaR_Uncontrained_Revenue_Loss}\n')


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
                (1 - model.z[f'z_{opt_iten}'])
            )
            if str(f'D_{opt_iten}_{itn.iloc[itinerary_no_col]}') in demand_correction_factor_df['name'].values
            else 0
            for opt_iten in optional_itineraries
        )
        if str(flight.iloc[flight_no_col]) in (str(itn.iloc[flights_col]).split(", "))
        else 0
        for idx, itn in itineraries_df.iterrows()
    )
    
    print(f'Interaction constraind Demand correction part equation{idx1 + 1}:\n{flight_demand_correction}\n')

    model.flight_interaction.add(expr= spilled_passengers - recaptured_passengers >= flight_unconstrained_demand + flight_demand_correction - flight_seats_available)
           
# ****************** Spill-Recapture & Demand Constraints **************** #
model.demand = ConstraintList()
model.spill_recapture=ConstraintList()
for itn in range(len(itineraries_df)):  
    
    itenrary=itineraries_df.iloc[itn, itinerary_no_col]
    t_p_r__sum = sum(model.spilled_recaptured_vars[t_p_r] if t_p_r.split('_')[1] == str(itenrary) else 0 for t_p_r in spilled_recaptured_vars) # from I_FAM
    
    
    demand_correction_factor_sum = sum( 
                                       (demand_correction_factor_df[demand_correction_factor_df['name'] == str(f'D_{opt_iten}_{itenrary}')]['value'].iloc[0])
                                       * (1-model.z[f'z_{opt_iten}'])
                                       if str(f'D_{opt_iten}_{itenrary}') in demand_correction_factor_df['name'].values else 0
                                       for opt_iten in optional_itineraries)
    
    model.demand.add(expr= t_p_r__sum - itineraries_df.iloc[itn, demand_col] -  demand_correction_factor_sum <= 0) # Demand Constraints
    
    model.spill_recapture.add(expr=t_p_r__sum == model.t_spilled[itenrary])  # Spill_recapture Constraints
        
    
# ****************** Ensure Zq = 0 Constraint **************** #    
model.Ensure_Z_is_zero = ConstraintList()

for opt_iten in optional_itineraries:
    
    opt_iten_flights=str((itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , flights_col].iloc[0])).split(", ")

    for flight in opt_iten_flights:
        
        model.Ensure_Z_is_zero.add(expr=   model.z[f'z_{opt_iten}'] <= sum([x[flight,e] for e in model.setE ]  ))
        
        
# ****************** Ensure Zq = 1 Constraint **************** # 
model.Ensure_Z_is_ONE = ConstraintList()
for opt_iten in optional_itineraries:
    
    opt_iten_flights=str((itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values , flights_col].iloc[0])).split(", ")
    N_q=len(opt_iten_flights)  # Number of flights in optional itenrary
    
    model.Ensure_Z_is_ONE.add(expr = model.z[f'z_{opt_iten}'] - sum([x[flight,e] for e in model.setE for flight in opt_iten_flights]  ) >= 1-N_q)
        

# ****************** Solving **************** # 
opt = SolverFactory('gurobi')
print('\n\nSolving please wait\n\n')
problem_results = opt.solve(model)
        
for idx, flight in flights_df.iterrows():
    for opt_iten in optional_itineraries:
        flights_list_in_opt_iten = (
            str(itineraries_df.iloc[ (itineraries_df.iloc[:, itinerary_no_col] == opt_iten).values, flights_col].iloc[0])
        ).split(', ')

        if str(flight.iloc[0]) in flights_list_in_opt_iten and int(pyo.value(model.z[f'z_{opt_iten}'])) == 0:
            flights_df.iloc[ (flights_df.loc[:, flight_no_col] == flight.iloc[flight_no_col]) , 'status'] = 'removed'
        else:
            for e in range(1, len(fleets_df) + 1):
                try:
                    if pyo.value(model.x[(str(flight.iloc[flight_no_col]), e)]) == 1:
                        flights_df.iloc[ (flights_df.loc[:, flight_no_col] == flight.iloc[flight_no_col]), 'status'] = e
                except KeyError:
                    print(f"KeyError: Index {str(flight.iloc[flight_no_col]), e} is not valid for indexed component 'x'")

flights_df.fillna('Flight not in Itineraries file', inplace=True)
    

# Function to convert minutes to hh:mm:ss format
def minutes_to_time(minutes):
    hours = int(minutes // 60)
    minutes = int(minutes % 60)
    return '{:02d}:{:02d}:00'.format(hours, minutes)

# Convert DepartureTime and ArrivalTime columns
flights_df.iloc[:, departure_col] = flights_df.iloc[:, departure_col].apply(minutes_to_time)
flights_df.iloc[:, arrival_col] = flights_df.iloc[:, arrival_col].apply(minutes_to_time)


flights_df.to_excel('ISD_IFAM__routes_output.xlsx', index=False)


if problem_results.solver.termination_condition == TerminationCondition.optimal:
    # The solver was successful, and the optimal solution is available

    # Access and print the values of your Pyomo variables
    for i in model.component_objects(pyo.Var, active=True):  # Iterate over all Pyomo variables
        print(f"Variable {i.name}:")
        for idx in i:
            print(f"    {i[idx].name}: {pyo.value(i[idx])}")

    print("\n \n Objective (Profit): ", pyo.value(model.obj))

else:
    # The solver did not find an optimal solution
    print("Solver did not converge to an optimal solution.")


model.pprint()
# for idx in model.setp:
#     print(f'Value of tp at index {idx}: {value(model.t_spilled[idx])}')
#     print(f'Value of tpr at index {idx}: {value(model.spilled_recaptured_vars[idx])}')