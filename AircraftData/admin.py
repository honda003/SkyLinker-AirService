from django.contrib import admin
from .models import AircraftData, EngineDetails

# Define admin class for AircraftData
class AircraftDataAdmin(admin.ModelAdmin):
    list_display = ('Airline_Name', 'Aircraft_Name','current_date', 'current_flight_hours', 'current_flight_cycles', 'apu_hours_to_flight_hours_ratio', 'apu_sn', 'apu_fh', 'apu_fc', 'num_engs')
    # You can add more customization here
    

# Define admin class for EngineDetails
class EngineDetailsAdmin(admin.ModelAdmin):
    list_display = ('Airline_Name', 'Aircraft_Name','eng_sn', 'eng_fh', 'eng_fc')
    # You can add more customization here



# Register your models here with their respective admin class
admin.site.register(AircraftData, AircraftDataAdmin)
admin.site.register(EngineDetails, EngineDetailsAdmin)