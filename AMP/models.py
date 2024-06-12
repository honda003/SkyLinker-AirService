from django.db import models
from django.utils.html import mark_safe
from datetime import datetime
from Operator.models import OperatorInput, AircraftDetails 
from AircraftData.models import AircraftData
import logging
from Operator.views import L_Intervals, C_Intervals
import json
from django.db.models import Q
import re

# Create your models here.
class DueClearance(models.Model):
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, null=True, blank=True) #Data to link
    Aircraft_Name = models.ManyToManyField(AircraftDetails, blank=True)  # Changed to ManyToManyField
    DY_clearance = models.IntegerField(default=0, null=True, blank=True)  # Allow NULL and empty values from forms/admin
    FH_clearance = models.CharField(default='0:00', max_length=255, null=True, blank=True)  # Allow NULL and empty values from forms/admin
    FC_clearance = models.IntegerField(default=0, null=True, blank=True)   # Allow NULL and empty values from forms/admin
    
    class Meta:
        verbose_name = "Due Clearance"

class ExcelData(models.Model):
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, null=True, blank=True) #Data to link
    Aircraft_Name = models.ManyToManyField(AircraftDetails, blank=True)  # Changed to ManyToManyField
    
    MPD_ITEM_NUMBER = models.CharField(max_length=255, default='xx-xxx-xx')
    SPECIAL_REQUIREMENTS = models.CharField(max_length=255, default='null')
    ATTACHED_EO = models.CharField(max_length=255, default='xx-xxx-xx-xx')
    TASK_CARD_NUMBER = models.CharField(max_length=255, default='null')
    TASK_CARD_NOTE= models.CharField(max_length=255, default='null')
    RELATED_TASK_CARD_NUMBER= models.CharField(max_length=255, default='null')
    AMM_REFERENCE = models.CharField(max_length=255, default='null')
    CAT = models.CharField(max_length=255, default='null')
    PGM = models.CharField(max_length=255, default='null')
    TASK = models.CharField(max_length=255, default='null')
    THRES = models.CharField(max_length=255, default='null')
    REPEAT = models.CharField(max_length=255, default='null')
    ZONE = models.CharField(max_length=255, default='null')
    ACCESS = models.CharField(max_length=255, default='null')
    APL = models.CharField(max_length=255, default='null')
    ENG = models.CharField(max_length=255, default='null')
    ACCESS_HOURS = models.DecimalField(max_digits=7, decimal_places=2, null = True , blank = True) 
    MAN_HOURS = models.DecimalField(max_digits=7, decimal_places=2, null = True , blank = True)
    TOTAL_HOURS = models.DecimalField(max_digits=7, decimal_places=2, null = True , blank = True)
    TASK_DESCREPTION = models.CharField(max_length=255, default='null')
    TASK_TYPE = models.CharField(max_length=255, default='null')
    TASK_TITLE = models.CharField(max_length=255, default='null')
    PROGRAM = models.CharField(max_length=255, default='null')
    APPLICABLE_TO_32692 = models.CharField(max_length=255, default='null')
    APPLICABILITY_NOTE = models.CharField(max_length=255, default='null')
    AREA = models.CharField(max_length=255, default='null')
    PACKAGE = models.CharField(max_length=255, null = True , blank = True)
    REMARKS = models.CharField(max_length=255, default='null')
    
    #Zawed Doll fyl EXCEL
    CHECK = models.CharField(max_length=255, null = True , blank = True)

    FC_Thres = models.FloatField(null=True, blank=True)
    FH_Thres = models.FloatField(null=True, blank=True)
    Calendar_Thres = models.CharField(max_length=255, default='null')
    Calendar_Unit_Thres = models.CharField(max_length=255, default='null')
    Is_Notes_Thres = models.CharField(max_length=255, null=True, blank=True)

    FC_Repeat = models.FloatField(null=True, blank=True)
    FH_Repeat = models.FloatField(null=True, blank=True)
    Calendar_Repeat = models.CharField(max_length=255, default='null')
    Calendar_Unit_Repeat = models.CharField(max_length=255, default='null')
    Is_Notes_Repeat = models.CharField(max_length=255, null=True, blank=True)
    
    # Add other fields as needed
    uploaded_at = models.DateTimeField(auto_now_add=True)
    dynamic_applicability = models.JSONField(default=dict)
    
    def save(self, *args, **kwargs):
            
        # Replace newlines with spaces before saving
        self.APL = self.APL.replace('\n', ' ')
        self.ENG = self.ENG.replace('\n', ' ')
        
        # print(f'self.Airline_Name: {self.Airline_Name}')
        if self.Airline_Name:
            # Attempt to fetch the OperatorInput based on the provided Airline_Name
            try:
                # print(f'airline_name: {self.Airline_Name}')
                operator_input = OperatorInput.objects.get(Airline_Name=self.Airline_Name)
            except OperatorInput.DoesNotExist:
                # Handle the error if OperatorInput is not found
                raise ValueError("No OperatorInput found with the specified Airline_Name.")
        else:
            # Optionally handle the case where no airline_name is provided
            if not self.Airline_Name:
                raise ValueError("Airline_Name must be provided for saving ExcelData.")

        # Handling ManyToMany relationships for Aircraft_Name
        aircraft_name = kwargs.pop('aircraft_name', None)
        if aircraft_name:
            self.Aircraft_Name.set(aircraft_name)
        # Dynamically generate L and C checks based on operator input
        num_L_packages = operator_input.L_no
        num_C_packages = operator_input.C_no

         # Fetch unique aircraft types from the AircraftDetails model or another source
        unique_aircraft_types = list(AircraftDetails.objects.values_list('aircraft_type', flat=True).distinct())
        applicability = {}  # Prepare a dict to hold our applicability data


        # APL_data = self.APL
        # for aircraft_type in unique_aircraft_types:
        #     applicable_column_name = f"APPLICABLE_FOR_{aircraft_type}"
            
        #     # Define patterns for exact match and general applicability
        #     exact_pattern = rf'\b{aircraft_type}\b'  # Matches exactly "800" as a whole word
        #     general_patterns = ['ALL', 'ALL NOTE']
            
        #     # Check for exact match or general applicability
        #     if re.search(exact_pattern, APL_data) or any(pat in APL_data for pat in general_patterns):
        #         applicability[applicable_column_name] = 'Y'
        #     else:
        #         applicability[applicable_column_name] = 'N'

        # # Now, update the dynamic_applicability field with our constructed dictionary
        # self.dynamic_applicability = json.dumps(applicability)

        # Extract and manipulate data from the first column
        first_column_data = self.THRES
        if first_column_data:
            fc_interval, fh_interval, calendar_interval, calendar_unit, notes = self.extract_info(first_column_data)

            # Update the row with the extracted data only if not already assigned
            if not self.FC_Thres:
                self.FC_Thres = fc_interval
            if not self.FH_Thres:
                self.FH_Thres = fh_interval
            if not self.Calendar_Thres:
                self.Calendar_Thres = calendar_interval
            if not self.Calendar_Unit_Thres:
                self.Calendar_Unit_Thres = calendar_unit
            if not self.Is_Notes_Thres:
                self.Is_Notes_Thres = notes
            
        # Extract and manipulate data from the second column
        second_column_data = self.REPEAT
        if second_column_data:
            fc_interval, fh_interval, calendar_interval, calendar_unit, notes = self.extract_info(first_column_data)

            # Update the row with the extracted data only if not already assigned
            if not self.FC_Repeat:
                self.FC_Repeat = fc_interval
            if not self.FH_Repeat:
                self.FH_Repeat = fh_interval
            if not self.Calendar_Repeat:
                self.Calendar_Repeat = calendar_interval
            if not self.Calendar_Unit_Repeat:
                self.Calendar_Unit_Repeat = calendar_unit
            if not self.Is_Notes_Repeat:
                self.Is_Notes_Repeat = notes
            
            
             # Get the dynamically calculated intervals
        
        # Assuming get_intervals() is a function that fetches L and C intervals from the Operator app
        L_intervals, C_intervals = self.get_intervals()

        
        # Convert and compare logic
        if self.FC_Repeat is not None and self.FC_Repeat != 'null':
            fc_repeat = float(self.FC_Repeat or 0)
        else:
            fc_repeat = self.FC_Repeat
        if self.FH_Repeat is not None and self.FH_Repeat != 'null':
            fh_repeat = float(self.FH_Repeat or 0)
        else:
            fh_repeat = self.FH_Repeat
        if self.Calendar_Repeat is not None and self.Calendar_Repeat != 'null':
            calendar_repeat = float(self.Calendar_Repeat or 0)
        else:
            calendar_repeat = self.Calendar_Repeat
        calendar_unit = self.Calendar_Unit_Repeat

        # Convert calendar_repeat to days or years as needed for comparison
        if calendar_unit == 'MO':
            calendar_repeat_days = calendar_repeat * 30  # Approximate conversion to days
        elif calendar_unit == 'YR':
            calendar_repeat_days = calendar_repeat * 365  # Approximate conversion to days
        elif calendar_unit == 'HR':
            calendar_repeat_days = calendar_repeat / 24 # Approximate conversion to days
        else:
            calendar_repeat_days = calendar_repeat  # Assuming it's already in days

        # Merge L and C intervals for easier processing
        intervals = {**L_intervals, **C_intervals}

        # New logic for determining PACKAGE based on Daily, Weekly, and Service intervals
        daily_dy = operator_input.Daily
        weekly_dy = operator_input.Weekly
        service_dy = operator_input.Service_DY
        service_fh = operator_input.Service_FH
        service_fc = operator_input.Service_FC

        if self.PACKAGE is None or self.PACKAGE == 'null':

            # Check if the conditions for Daily, Weekly, or Service are met
            if calendar_repeat_days is not None and calendar_repeat_days != 'null' and 1 < calendar_repeat_days <= daily_dy :
                self.PACKAGE = 'DAILY'
            elif calendar_repeat_days is not None and calendar_repeat_days != 'null' and daily_dy < calendar_repeat_days <= weekly_dy :
                self.PACKAGE = 'WEEKLY'
            elif calendar_repeat_days is not None and calendar_repeat_days != 'null' and (service_dy <= calendar_repeat_days < L_intervals['L1']['DY_Interval']['lower_bound']) or \
                fh_repeat is not None and fh_repeat != 'null' and (service_fh <= fh_repeat < L_intervals['L1']['FH_Interval']['lower_bound']) or \
                fc_repeat is not None and fc_repeat != 'null' and  (service_fc <= fc_repeat < L_intervals['L1']['FC_Interval']['lower_bound']):
                self.PACKAGE = 'SERVICE'
            else:
                # Find the matching interval
                for interval_name, values in intervals.items():
                    is_match = False
                    if fc_repeat is not None and fc_repeat != 'null' and (values['FC_Interval']['lower_bound'] <= fc_repeat < values['FC_Interval']['upper_bound']):
                        is_match = True
                    if fh_repeat is not None and fh_repeat != 'null' and (values['FH_Interval']['lower_bound'] <= fh_repeat < values['FH_Interval']['upper_bound']):
                        is_match = True

                    # Convert years to days for C intervals comparison if necessary
                    if 'YR_Interval' in values:
                        lower_bound_days = values['YR_Interval']['lower_bound'] * 365
                        upper_bound_days = values['YR_Interval']['upper_bound'] * 365
                    else:
                        lower_bound_days = values['DY_Interval']['lower_bound']
                        upper_bound_days = values['DY_Interval']['upper_bound']

                    if calendar_repeat_days is not None and calendar_repeat_days != 'null' and (lower_bound_days <= calendar_repeat_days < upper_bound_days):
                        is_match = True

                    if is_match:
                        self.PACKAGE = interval_name
                        break
                else:
                    self.PACKAGE = None
                    
         # After calculating the 'Package', directly calculate and assign checks
        package = self.PACKAGE
        checks = self.calculate_checks_based_on_package(package, num_L_packages, num_C_packages )
        if checks is not None:
            self.CHECK = ','.join(checks)  # Convert list to comma-separated string for CharField
        else:
            self.CHECK = None
            
        
        super().save(*args, **kwargs)
    
    def get_intervals(self):
        operator_input = OperatorInput.objects.get(Airline_Name=self.Airline_Name)
        num_L_packages = operator_input.L_no
        num_C_packages = operator_input.C_no
        L_intervals = L_Intervals(num_L_packages, operator_input)
        C_intervals = C_Intervals(num_C_packages, operator_input)
        return L_intervals, C_intervals
    
    def extract_info(self, text):
        fc_interval = fh_interval = calendar_interval = calendar_unit = notes = None

        if 'FC' in text:
            match = re.search(r'(\d+)(?= FC)', text)
            fc_interval = match.group(1) if match else None

        if 'FH' in text:
            match = re.search(r'(\d+)(?= FH)', text)
            fh_interval = match.group(1) if match else None

        if 'YR' in text:
            calendar_unit = 'YR'
            match = re.search(r'(\d+)(?= YR)', text)
            calendar_interval = match.group(1) if match else None

        if 'MO' in text:
            calendar_unit = 'MO'
            match = re.search(r'(\d+)(?= MO)', text)
            calendar_interval = match.group(1) if match else None

        if 'DY' in text:
            calendar_unit = 'DY'
            match = re.search(r'(\d+)(?= DY)', text)
            calendar_interval = match.group(1) if match else None

        if 'HR' in text:
            calendar_unit = 'HR'
            match = re.search(r'(\d+)(?= HR)', text)
            calendar_interval = match.group(1) if match else None

        if 'NOTE' in text:
            notes = 'NOTE'

        return fc_interval, fh_interval, calendar_interval, calendar_unit, notes
    
    def calculate_checks_based_on_package(self, package, num_L_packages, num_C_packages):
        checks = []

        # Logic to dynamically generate checks based on num_L_packages and num_C_packages
        if package is not None and package != 'null':
            if package.startswith('L'):
                l_package_num = int(package[1:])
                checks.extend([f'L{i}' for i in range(1, l_package_num + 1) if l_package_num % i == 0])
            elif package.startswith('C'):
                c_package_num = int(package[1:])
                # All L packages are included in any C package
                checks.extend([f'L{i}' for i in range(1, num_L_packages + 1)])
                # Include this C package and its divisible predecessors
                checks.extend([f'C{i}' for i in range(1, c_package_num + 1) if c_package_num % i == 0])
            else:
                checks = None

            return checks

    def __str__(self):
        return self.MPD_ITEM_NUMBER
    
    class Meta:
        verbose_name = "AMP Data'"
        
        
