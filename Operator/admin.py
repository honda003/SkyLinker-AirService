from django.contrib import admin
from .models import OperatorInput, AircraftDetails

# Define admin class for OperatorInput
class OperatorInputAdmin(admin.ModelAdmin):
    list_display = ('Airline_Name', 'FC_DY', 'FH_DY', 'Daily', 'Weekly', 'Service_DY', 'Service_FH', 'Service_FC', 'L_no', 'L1_DY', 'L1_FH', 'L1_FC', 'C_no', 'C1_YR', 'C1_FH', 'C1_FC', 'num_aircrafts')
    # You can add more customization here

# Define admin class for AircraftDetails
class AircraftDetailsAdmin(admin.ModelAdmin):
    list_display = ('Airline_Name', 'aircraft_name', 'aircraft_type', 'production_date', 'ac_sn', 'ac_ln', 'ac_bn')
    # You can add more customization here

# Register your models here with their respective admin class
admin.site.register(OperatorInput, OperatorInputAdmin)
admin.site.register(AircraftDetails, AircraftDetailsAdmin)