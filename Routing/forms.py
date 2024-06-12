from django import forms
from django.core.exceptions import ValidationError


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='Upload Excel File')
    
def create_column_index_form(missing_columns):
    """
    Dynamically creates a form to ask for missing column indices, considering Excel's 1-based indexing.
    
    Parameters:
    - missing_columns: A list of strings representing the names of missing columns.
    """
    class ColumnIndexForm(forms.Form):
        pass

    for column_name in missing_columns:
        # Note for users about Excel's 1-based indexing
        help_text = f"Enter the 1-based column number for {column_name}. (e.g., '1' for the first column)"
        
        field_name = f"{column_name}_index"
        ColumnIndexForm.base_fields[field_name] = forms.IntegerField(
            label=f"{column_name.capitalize()} Column Number",
            help_text=help_text,
            required=True,
            min_value=1  # Adjusted to 1 to align with Excel's 1-based indexing
        )
    
    return ColumnIndexForm

class TurnAroundTimeForm(forms.Form):
    turn_around_time = forms.FloatField(label='Turn Around Time in Minutes', min_value=0.0)

def create_hub_selection_form(unique_stations):
    class HubSelectionForm(forms.Form):
        pass

    HubSelectionForm.base_fields['hubs'] = forms.MultipleChoiceField(
        choices=[(station, station) for station in unique_stations],
        widget=forms.CheckboxSelectMultiple,
        label="Select Hubs",
        error_messages={'required': 'Please choose your hub(s).'}
    )
    
    return HubSelectionForm

class FpdForm(forms.Form):
    use_max_fpd = forms.BooleanField(required=False, label='Use Obtained Maximum Flights Per Day')
    specified_fpd = forms.IntegerField(required=False, label='Specify Different Flights Per Day', min_value=1)

    def clean(self):
        cleaned_data = super().clean()
        use_max_fpd = cleaned_data.get('use_max_fpd')
        specified_fpd = cleaned_data.get('specified_fpd')
        max_fpd = self.initial.get('max_fpd', None)

        if not use_max_fpd and specified_fpd is None:
            raise forms.ValidationError('Please specify flights per day.')

        if specified_fpd is not None and (specified_fpd < 1 or specified_fpd > max_fpd):
            raise forms.ValidationError(f'Specify a value between 1 and {max_fpd}.')

        return cleaned_data
    
class CycleAndAircraftForm(forms.Form):
    days_in_cycle = forms.IntegerField(label='Number of Days in Cycle', min_value=1)
    number_of_aircrafts = forms.IntegerField(label='Number of Available Aircrafts in Your Fleet', min_value=1)