from django import forms
from django.core.exceptions import ValidationError
from .models import AircraftData

class EnginesForm(forms.Form):
    num_engs = forms.IntegerField(label="Number Of Engines", min_value=1)

class AircraftDataForm(forms.ModelForm):
    class Meta:
        model = AircraftData
        exclude = ('num_engs',)  # Exclude num_aircrafts from the form
        fields = ['Airline_Name', 'Aircraft_Name', 'current_date', 'current_flight_hours', 'current_flight_cycles', 'apu_hours_to_flight_hours_ratio', 'apu_sn', 'apu_fh', 'apu_fc', 'num_engs']
        labels = {
            'Airline_Name': 'Airline Name',
            'Aircraft_Name': 'Aircraft Name',
            'current_date': 'Data Entry Date',
            'current_flight_hours': 'Current Total Flight Hours',
            'current_flight_cycles': 'Current Total Flight Cycles',
            'apu_hours_to_flight_hours_ratio': 'APU HRS to AC HRS',
            'apu_sn': 'APU Serial Number',
            'apu_fh': 'APU Flight Hours',
            'apu_fc': 'APU Flight Cycles',
            'num_engs': 'Number of Engines',
        }
        widgets = {
            'current_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def clean_current_flight_hours(self):
        flight_hours = self.cleaned_data['current_flight_hours']
        # Validate the format
        try:
            hours, minutes = flight_hours.split(':')
            hours = int(hours)
            minutes = int(minutes)
            if not (0 <= minutes < 60):
                raise ValidationError('Minutes must be between 0 and 59.')
        except ValueError:
            raise ValidationError('Invalid format. Please use HH:MM format.')
        return flight_hours
    
    def clean_apu_fh(self):
        flight_hours = self.cleaned_data['apu_fh']
        # Validate the format
        try:
            hours, minutes = flight_hours.split(':')
            hours = int(hours)
            minutes = int(minutes)
            if not (0 <= minutes < 60):
                raise ValidationError('Minutes must be between 0 and 59.')
        except ValueError:
            raise ValidationError('Invalid format. Please use HH:MM format.')
        return flight_hours