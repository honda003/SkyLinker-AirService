from django import forms
from .models import ExcelData, DueClearance
from django.core.exceptions import ValidationError
from import_export.forms import ImportForm, ConfirmImportForm
from .models import AircraftData
from Operator.models import OperatorInput, AircraftDetails 


class ExcelDataImportForm(forms.Form):
    airline = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label='Choose Airline')
    aircraft = forms.ModelMultipleChoiceField(queryset=AircraftDetails.objects.all(), label='Choose Aircraft', widget=forms.CheckboxSelectMultiple())  # Changed to ModelMultipleChoiceField
    import_file = forms.FileField(label='Upload Excel File')
    
        
class ExcelDataForm(forms.ModelForm):
    Airline_Name = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label='Choose Airline')
    Aircraft_Name = forms.ModelMultipleChoiceField(queryset=AircraftDetails.objects.all(), label='Choose Aircraft', widget=forms.CheckboxSelectMultiple())  # Changed to ModelMultipleChoiceField
    class Meta:
        model = ExcelData
        fields = ['Airline_Name', 'Aircraft_Name', 'MPD_ITEM_NUMBER', 'TASK_CARD_NUMBER', 'THRES', 'REPEAT', 'ZONE', 'ACCESS', 'APL', 'ENG', 'ACCESS_HOURS', 'MAN_HOURS', 'TOTAL_HOURS', 'TASK_DESCREPTION', 'TASK_TYPE', 'TASK_TITLE', 'PROGRAM', 'AREA', 'PACKAGE', 'REMARKS', 'CHECK', 'dynamic_applicability']
        # Add other fields as needed
        
class DueClearanceForm(forms.ModelForm):
    class Meta:
        model = DueClearance
        fields = ['Airline_Name', 'Aircraft_Name', 'DY_clearance', 'FH_clearance', 'FC_clearance']

    def clean_FH_clearance(self):
        fh_clearance = self.cleaned_data.get('FH_clearance')
        if fh_clearance:
            parts = fh_clearance.split(':')
            if len(parts) != 2:
                raise ValidationError('Invalid format. Please use HH:MM format.')
            hours, minutes = parts
            try:
                hours = int(hours)
                minutes = int(minutes)
                if not (0 <= minutes < 60):
                    raise ValidationError('Minutes must be between 0 and 59.')
            except ValueError:
                raise ValidationError('Invalid format. Hours and minutes must be integers.')
        return fh_clearance