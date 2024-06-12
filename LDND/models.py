from django.db import models
from AMP.models import ExcelData, DueClearance
from Operator.views import L_Intervals, C_Intervals
from Operator.models import OperatorInput, AircraftDetails
from AircraftData.models import AircraftData
import pandas as pd
from datetime import timedelta
import logging
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from django.db.models import Q
import datetime

# Get an instance of a logger
logger = logging.getLogger(__name__)


class LastDone(models.Model):
    excel_data = models.ForeignKey(ExcelData, on_delete=models.CASCADE, verbose_name="MPD Item No.")  # Link to the ExcelData
    
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Airline Name") #Data to link
    Aircraft_Name = models.ForeignKey(AircraftDetails, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Aircraft Name") #Data to link
    
    last_done_date = models.DateField(null=True, blank=True, verbose_name="LD Date")  # Allow NULL and empty values from forms/admin
    last_done_fh = models.CharField(max_length=255, null=True, blank=True, verbose_name="LD FH")   # Allow NULL and empty values from forms/admin
    last_done_fc = models.FloatField(null=True, blank=True, verbose_name="LD FC")   # Allow NULL and empty values from forms/admin
    
    done = models.CharField(max_length=1, blank=True, null=True, verbose_name="Done")
    
    al_nd_date = models.DateField(null=True, blank=True, verbose_name="Airline ND DATE")
    al_nd_fh = models.CharField(max_length=255, null=True, blank=True, verbose_name="Airline ND FH")
    al_nd_fc = models.FloatField(null=True, blank=True, verbose_name="Airline ND FC")
    al_due = models.CharField(max_length=255, null=True, blank=True, verbose_name="Airline DUE")
    
    mpd_nd_date = models.DateField(null=True, blank=True, verbose_name="MPD ND DATE")
    mpd_nd_fh = models.CharField(max_length=255,null=True, blank=True, verbose_name="MPD ND FH")
    mpd_nd_fc = models.FloatField(null=True, blank=True, verbose_name="MPD ND FC")
    mpd_due = models.CharField(max_length=255, null=True, blank=True, verbose_name="MPD DUE")
    
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) #new
    modified_on = models.DateTimeField(auto_now=True) #new 

    def save(self, *args, **kwargs):
        # Prevent recursive call to save method
        if 'skip_recursive' in kwargs:
            del kwargs['skip_recursive']
            super(LastDone, self).save(*args, **kwargs)
            return

        with transaction.atomic():
            
            print(f'self.Airline_Name: {self.Airline_Name}')
            print(f'self.Aircraft_Name: {self.Aircraft_Name}')
            if not self.Airline_Name or not self.Aircraft_Name:
                raise ValueError("Airline and Aircraft must be set before saving.")
            
            # Fetching the exact AircraftDetails entry using both the airline and aircraft name
            try:
                ac_details = AircraftDetails.objects.get(
                    Airline_Name=self.Airline_Name,  # Ensures the airline is correct
                    id=self.Aircraft_Name_id        # Ensures the specific aircraft is selected
                )
            except AircraftDetails.DoesNotExist:
                raise ValueError("The specified aircraft details do not exist for the given airline.")
            
            # Fetch related data for validation or calculation
            operator = OperatorInput.objects.get(Airline_Name=self.Airline_Name)

            # Filter and fetch related records
            excel_data = ExcelData.objects.get(Airline_Name=self.Airline_Name, Aircraft_Name=self.Aircraft_Name, MPD_ITEM_NUMBER=self.excel_data.MPD_ITEM_NUMBER)
            ac_data = AircraftData.objects.get(Airline_Name=self.Airline_Name, Aircraft_Name=self.Aircraft_Name)
            due_clearance, created = DueClearance.objects.get_or_create(
                Airline_Name=self.Airline_Name,
                defaults= {
                    'DY_clearance': 0,
                    'FH_clearance': 0,
                    'FC_clearance': 0
                    
                })
            # Since DueClearance has a ManyToManyField with AircraftDetails, let's set it correctly
            if created or not due_clearance.Aircraft_Name.filter(id=self.Aircraft_Name_id).exists():
                due_clearance.Aircraft_Name.add(self.Aircraft_Name)  # Use .add() for ManyToManyField relation
      
            # Print debug information, remove in production or replace with logging
            # print(f'operator: {operator.Airline_Name if operator else "No Operator"}')
            # print(f'aircraft: {ac_details.aircraft_name if ac_details else "No Aircraft"}')
            # print(f'ac_data: {ac_data}')
            # print(f'due_clearance: {due_clearance}')

            if operator:
                                        
                operator_input = operator
                service_dy = operator.Service_DY
                service_fh = operator.Service_FH
                service_fc = operator.Service_FC

                current_date = ac_data.current_date
                current_fh = ac_data.current_flight_hours
                current_fc = ac_data.current_flight_cycles
                
                print(f'current_date: {current_date}')
                print(f'current_fh: {current_fh}')
                print(f'current_fc: {current_fc}')

                last_done_fh = self.last_done_fh if self.last_done_fh != 'null' else None
                last_done_fh_float = float(last_done_fh) / 60 if last_done_fh else None
                package = excel_data.PACKAGE
            
                ac_type = ac_details.aircraft_type
                production_date = ac_details.production_date 

                
                if self.last_done_fh is not None and self.last_done_fh != 'null':
                    last_done_fh_float = float(self.last_done_fh) / 60
                else:
                    last_done_fh_float = None
                    
                #print(f"Debug: last_done_fh_float is '{last_done_fh_float}' and type is {type(last_done_fh_float)}")
                
                if self.last_done_date or self.last_done_fh or self.last_done_fc:
                    self.done = 'Y'
                else:
                    self.done = 'N'
                
                if self.done == 'Y':

                    if package is not None and package.startswith('L'):
                        num_L_packages = operator_input.L_no
                        l_intervals = L_Intervals(num_L_packages, operator_input)
                        interval_key = package  # e.g., 'L1'
                        if interval_key in l_intervals:
                            
                            print(f'self.last_done_date: {self.last_done_date}\n\n')
                            
                            if self.last_done_date is not None:
                                self.al_nd_date = self.last_done_date + timedelta(days=l_intervals[interval_key]['DY_Interval']['lower_bound'])
                                print(f'self.al_nd_date: {self.al_nd_date}\n\n')
                                
                            if last_done_fh_float is not None:     
                                al_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + l_intervals[interval_key]['FH_Interval']['lower_bound']))
                                self.al_nd_fh = al_nd_fh_str
                            
                            if self.last_done_fc is not None:
                                self.al_nd_fc = self.last_done_fc + l_intervals[interval_key]['FC_Interval']['lower_bound']
                            
                            if self.excel_data.Calendar_Repeat is not None and self.excel_data.Calendar_Repeat != 'null' :
                                self.mpd_nd_date = self.get_interval_date(self.last_done_date, self.excel_data.Calendar_Repeat, self.excel_data.Calendar_Unit_Repeat)
                                
                            if self.excel_data.FH_Repeat and last_done_fh_float  is not None and self.excel_data.FH_Repeat != 'null':
                                mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + self.excel_data.FH_Repeat))
                                self.mpd_nd_fh = mpd_nd_fh_str 
                                
                            if self.excel_data.FC_Repeat is not None and self.excel_data.FC_Repeat != 'null':
                                self.mpd_nd_fc = self.last_done_fc + self.excel_data.FC_Repeat
                                
                    elif package is not None and package.startswith('C'):
                        num_C_packages = operator_input.C_no
                        c_intervals = C_Intervals(num_C_packages, operator_input)
                        interval_key = package  # e.g., 'C1'
                        if interval_key in c_intervals:
                            
                            if self.last_done_date is not None:
                                self.al_nd_date = self.last_done_date + timedelta(days=c_intervals[interval_key]['YR_Interval']['lower_bound'] * 365)
                            
                            if last_done_fh_float is not None:  
                                al_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + c_intervals[interval_key]['FH_Interval']['lower_bound']))
                                self.al_nd_fh = al_nd_fh_str
                            
                            if self.last_done_fc is not None:
                                self.al_nd_fc = self.last_done_fc + c_intervals[interval_key]['FC_Interval']['lower_bound']
                            
                            if self.excel_data.Calendar_Repeat is not None and self.excel_data.Calendar_Repeat != 'null':
                                self.mpd_nd_date = self.get_interval_date(self.last_done_date, self.excel_data.Calendar_Repeat, self.excel_data.Calendar_Unit_Repeat)
                                                        
                            if self.excel_data.FH_Repeat and last_done_fh_float is not None and self.excel_data.FH_Repeat != 'null':
                                mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + self.excel_data.FH_Repeat))
                                self.mpd_nd_fh = mpd_nd_fh_str
                                
                            if self.excel_data.FC_Repeat is not None and self.excel_data.FC_Repeat != 'null':
                                self.mpd_nd_fc = self.last_done_fc + self.excel_data.FC_Repeat

                    elif package is not None and package == 'SERVICE':
                        # Use Calendar_Repeat and Calendar_Unit_Repeat for SERVICE
                        # Assuming Calendar_Repeat is in days, months, or years
                        
                        if self.last_done_date is not None:
                            self.al_nd_date = self.last_done_date + timedelta(days=service_dy)
                        
                        if last_done_fh_float is not None:  
                            al_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + service_fh))
                            self.al_nd_fh = al_nd_fh_str
                        
                        if self.last_done_fc is not None:
                            self.al_nd_fc = self.last_done_fc + service_fc
                        
                        if self.excel_data.Calendar_Repeat is not None and self.excel_data.Calendar_Repeat != 'null':
                                self.mpd_nd_date = self.get_interval_date(self.last_done_date, self.excel_data.Calendar_Repeat, self.excel_data.Calendar_Unit_Repeat)
                                
                        if self.excel_data.FH_Repeat and last_done_fh_float is not None and self.excel_data.FH_Repeat != 'null':
                            mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + self.excel_data.FH_Repeat))
                            self.mpd_nd_fh = mpd_nd_fh_str
                            
                        if self.excel_data.FC_Repeat is not None and self.excel_data.FC_Repeat != 'null':
                            self.mpd_nd_fc = self.last_done_fc + self.excel_data.FC_Repeat

                    else:
                        # Fallback to Calendar_Repeat if package doesn't start with L or C
                            
                        if self.excel_data.Calendar_Repeat is not None and self.excel_data.Calendar_Repeat != 'null':
                                self.mpd_nd_date = self.get_interval_date(self.last_done_date, self.excel_data.Calendar_Repeat, self.excel_data.Calendar_Unit_Repeat)
                                self.al_nd_date = self.mpd_nd_date
                                
                        if self.excel_data.FH_Repeat and last_done_fh_float is not None and self.excel_data.FH_Repeat != 'null':
                            mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(last_done_fh_float + self.excel_data.FH_Repeat))
                            self.mpd_nd_fh = mpd_nd_fh_str
                            self.al_nd_fh = self.mpd_nd_fh
                            
                        if self.excel_data.FC_Repeat is not None and self.excel_data.FC_Repeat != 'null':
                            self.mpd_nd_fc = self.last_done_fc + self.excel_data.FC_Repeat
                            self.al_nd_fc = self.mpd_nd_fc
                            
                else:
                    
                    if package is not None and package.startswith('L'):
                        num_L_packages = operator_input.L_no
                        l_intervals = L_Intervals(num_L_packages, operator_input)
                        interval_key = package  # e.g., 'L1'
                        if interval_key in l_intervals:
                            
                            self.al_nd_date = production_date + timedelta(days=l_intervals[interval_key]['DY_Interval']['lower_bound'])
                                
                            al_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + l_intervals[interval_key]['FH_Interval']['lower_bound']))
                            self.al_nd_fh = al_nd_fh_str
                            
                            self.al_nd_fc = l_intervals[interval_key]['FC_Interval']['lower_bound']
                            
                            if self.excel_data.Calendar_Thres is not None and self.excel_data.Calendar_Thres != 'null' :
                                self.mpd_nd_date = self.get_interval_date(production_date, self.excel_data.Calendar_Thres, self.excel_data.Calendar_Unit_Thres)
                                
                            if self.excel_data.FH_Thres and last_done_fh_float  is not None and self.excel_data.FH_Thres != 'null':
                                mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + self.excel_data.FH_Thres))
                                self.mpd_nd_fh = mpd_nd_fh_str 
                                
                            if self.excel_data.FC_Thres is not None and self.excel_data.FC_Thres != 'null':
                                self.mpd_nd_fc = self.excel_data.FC_Thres
                                
                    elif package is not None and package.startswith('C'):
                        num_C_packages = operator_input.C_no
                        c_intervals = C_Intervals(num_C_packages, operator_input)
                        interval_key = package  # e.g., 'C1'
                        if interval_key in c_intervals:
                            
                            self.al_nd_date = production_date + timedelta(days=c_intervals[interval_key]['YR_Interval']['lower_bound'] * 365)

                            al_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + c_intervals[interval_key]['FH_Interval']['lower_bound']))
                            self.al_nd_fh = al_nd_fh_str

                            self.al_nd_fc = c_intervals[interval_key]['FC_Interval']['lower_bound']
                            
                            if self.excel_data.Calendar_Thres is not None and self.excel_data.Calendar_Thres != 'null':
                                self.mpd_nd_date = self.get_interval_date(production_date, self.excel_data.Calendar_Thres, self.excel_data.Calendar_Unit_Thres)
                                                        
                            if self.excel_data.FH_Thres and last_done_fh_float is not None and self.excel_data.FH_Thres != 'null':
                                mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + self.excel_data.FH_Thres))
                                self.mpd_nd_fh = mpd_nd_fh_str
                                
                            if self.excel_data.FC_Thres is not None and self.excel_data.FC_Thres != 'null':
                                self.mpd_nd_fc = self.excel_data.FC_Thres

                    elif package is not None and package == 'SERVICE':
                        # Use Calendar_Repeat and Calendar_Unit_Repeat for SERVICE
                        # Assuming Calendar_Repeat is in days, months, or years
                        
                        self.al_nd_date = production_date + timedelta(days=service_dy)
                    
                        al_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + service_fh))
                        self.al_nd_fh = al_nd_fh_str

                        self.al_nd_fc = service_fc
                    
                        if self.excel_data.Calendar_Thres is not None and self.excel_data.Calendar_Thres != 'null':
                                self.mpd_nd_date = self.get_interval_date(production_date, self.excel_data.Calendar_Thres, self.excel_data.Calendar_Unit_Thres)
                                
                        if self.excel_data.FH_Thres and last_done_fh_float is not None and self.excel_data.FH_Thres != 'null':
                            mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + self.excel_data.FH_Thres))
                            self.mpd_nd_fh = mpd_nd_fh_str
                            
                        if self.excel_data.FC_Thres is not None and self.excel_data.FC_Thres!= 'null':
                            self.mpd_nd_fc = self.excel_data.FC_Thres

                    else:
                        # Fallback to Calendar_Repeat if package doesn't start with L or C
                            
                        if self.excel_data.Calendar_Thres is not None and self.excel_data.Calendar_Thres != 'null':
                                self.mpd_nd_date = self.get_interval_date(production_date, self.excel_data.Calendar_Thres, self.excel_data.Calendar_Unit_Thres)
                                self.al_nd_date = self.mpd_nd_date
                                
                        if self.excel_data.FH_Thres and last_done_fh_float is not None and self.excel_data.FH_Thres != 'null':
                            mpd_nd_fh_str = self.convert_fh_to_hours_minutes(str(0 + self.excel_data.FH_Thres))
                            self.mpd_nd_fh = mpd_nd_fh_str
                            self.al_nd_fh = self.mpd_nd_fh
                            
                        if self.excel_data.FC_Thres is not None and self.excel_data.FC_Thres != 'null':
                            self.mpd_nd_fc = self.excel_data.FC_Thres
                            self.al_nd_fc = self.mpd_nd_fc
                            
                if due_clearance:
                    dy_clearance = due_clearance.DY_clearance or 0
                    fh_clearance = self.convert_to_total_hours(due_clearance.FH_clearance) if due_clearance.FH_clearance else 0
                    fc_clearance = due_clearance.FC_clearance or 0
                    
                    print(f'dy_clearance: {dy_clearance}')
                    print(f'fh_clearance : {fh_clearance }')
                    print(f'fc_clearance: {fc_clearance}')

                    current_fh_total = self.convert_to_total_hours(current_fh) if current_fh else 0
                    
                    # Checks for al_due
                    if ((self.al_nd_date and current_date + timedelta(days=dy_clearance) >= self.al_nd_date) or
                        (self.al_nd_fh and current_fh_total + fh_clearance >= self.convert_to_total_hours(self.al_nd_fh)) or
                        (self.al_nd_fc and current_fc + fc_clearance >= self.al_nd_fc)):
                        self.al_due = 'DUE'

                    # Checks for mpd_due
                    if ((self.mpd_nd_date and current_date + timedelta(days=dy_clearance) >= self.mpd_nd_date) or
                        (self.mpd_nd_fh and current_fh_total + fh_clearance >= self.convert_to_total_hours(self.mpd_nd_fh)) or
                        (self.mpd_nd_fc and current_fc + fc_clearance >= self.mpd_nd_fc)):
                        self.mpd_due = 'DUE'
                                                
        super(LastDone, self).save(*args, **kwargs)
        
    def calculate_next_due_date(self, last_done_date, interval_days):
        if last_done_date and interval_days:
            return last_done_date + timedelta(days=interval_days)
        return None

    def get_interval_date(self, last_done_date, interval, unit):
        if unit == 'DY':
            return last_done_date + timedelta(days=float(interval))
        elif unit == 'MO':
            return last_done_date + timedelta(days=float(interval) * 30)  # Approximating a month as 30 days
        elif unit == 'YR':
            return last_done_date + timedelta(days=float(interval) * 365)  # Approximating a year as 365 days
        return last_done_date
    
    def convert_fh_to_hours_minutes(self, fh_str):
        try:
            # Convert the string to float first
            total_hours = float(fh_str)
            
            # Split into whole hours and fractional hours
            hours = int(total_hours)
            minutes = (total_hours - hours) * 60  # Convert the fractional hour to minutes

            # Format the hours and minutes into HH:MM format
            return f"{hours}:{int(minutes):02d}"
        except ValueError:
            return None
        
    def convert_to_total_hours(self, fh_str):
        if fh_str and ':' in fh_str:
            hours, minutes = map(int, fh_str.split(':'))
            return hours + minutes / 60.0
        return 0
    
    
    class Meta:
        verbose_name = "Last Done Next Due"

        