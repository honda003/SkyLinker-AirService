from django import forms
from .models import OperatorInput

class AircraftsForm(forms.Form):
    num_aircrafts = forms.IntegerField(label="Number Of Aircrafts", min_value=1)

class OperatorForm(forms.ModelForm):
    class Meta:
        model = OperatorInput
        exclude = ('num_aircrafts',)  # Exclude num_aircrafts from the form
        labels = {
            'Airline_Name': 'Airline Name',
            'FC_DY': 'Flight Cycles Per Day',
            'FH_DY': 'Flight Hours Per Day',
            'Daily': 'Daily Checks Interval in Days',
            'Weekly': 'Weekly Checks Time Interval in Days',
            'Service_DY': 'Service Check Interval in Days',
            'Service_FH': 'Service Check Interval in FH',
            'Service_FC': 'Service Check Interval in FC',
            'L_no': 'Number of L Packages',
            'L1_DY': 'L1 Check Interval in Days',
            'L1_FH': 'L1 Check Interval in FH',
            'L1_FC': 'L1 Check Interval in FC',
            'C_no': 'Number of C Packages',
            'C1_YR': 'C1 Check Interval in Years',
            'C1_FH': 'C1 Check Interval in FH',
            'C1_FC': 'C1 Check Interval in FC',
        }
        