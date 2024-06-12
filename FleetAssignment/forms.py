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

class FleetCountForm(forms.Form):
    number_of_fleets = forms.IntegerField(label='Enter the number of fleets you have', min_value=1)


def create_fleet_detail_form(post_data, number_of_fleets, fleet_number):
    class FleetDetailForm(forms.Form):
        fleet_type = forms.CharField(label=f'Fleet Type for Fleet {fleet_number}', required=True)
        number_of_aircrafts = forms.IntegerField(label=f'Number of Aircrafts in Fleet {fleet_number}', required=True, min_value=1)
        number_of_seats = forms.IntegerField(label=f'Number of Seats per Aircraft in Fleet {fleet_number}', required=True, min_value=1)
        operating_cost_per_mile = forms.FloatField(label=f'Operating Cost of Aircraft Per Mile {fleet_number}', required=True, min_value=0.0)

    if post_data:
        return FleetDetailForm(post_data, prefix=f'fleet_{fleet_number}')
    else:
        return FleetDetailForm(prefix=f'fleet_{fleet_number}')


def create_solver_selection_form():
    class SolverSelectionForm(forms.Form):
        pass

    SolverSelectionForm.base_fields['solver'] = forms.ChoiceField(
        choices=[(solver, solver) for solver in ['FAM', 'IFAM', 'ISD-IFAM']],
        widget=forms.RadioSelect,
        label="Select Solver",
        error_messages={'required': 'Please choose Solver).'}
    )
    
    return SolverSelectionForm

class RecaptureRatioForm(forms.Form):
    recapture_ratio = forms.FloatField(
        label='Recapture Ratio',
        help_text='How good are your itineraries compared to competitors, indicating their ability to attract passengers in case of cancellation.',
        min_value=0,
        max_value=1,
        initial=0.9,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
class DemandAdjustmentForm(forms.Form):
    recapture_ratio = forms.FloatField(
        label='Recapture Ratio',
        help_text='How good are your itineraries compared to competitors, indicating their ability to attract passengers in case of cancellation.',
        min_value=0,
        max_value=1,
        initial=0.9,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    decrease_demand_percentage = forms.FloatField(
        label='Decrease in Demand Percentage',
        help_text='Approximation percentage for reputation effect or any other decrease in demand on your itineraries due to cancellation of one of your flights.',
        min_value=0,
        max_value=100,
        initial=15.0,
        widget=forms.NumberInput(attrs={'step': '0.1'})
    )
    increase_demand_percentage = forms.FloatField(
        label='Increase in Demand Percentage',
        help_text='Approximation percentage for how many substitutable, high-quality itineraries you have for the same market, e.g., if one itinerary is cancelled, another will recapture 20% of its passengers.',
        min_value=0,
        max_value=100,
        initial=20.0,
        widget=forms.NumberInput(attrs={'step': '0.1'})
    )
    
def create_optional_flights_form(flights_df, flight_no_col):
    class OptionalFlightsForm(forms.Form):
        has_optional_flights = forms.ChoiceField(
            choices=[('yes', 'Yes'), ('no', 'No')],
            widget=forms.RadioSelect,
            label="Do you have optional flights?",
            initial='no'
        )
        all_flights_optional = forms.BooleanField(
            required=False,
            label="All my flights are optional",
            widget=forms.CheckboxInput
        )
        select_optional_flights = forms.MultipleChoiceField(
            choices=[(str(flight), str(flight)) for flight in flights_df.iloc[:, flight_no_col]],
            required=False,
            widget=forms.CheckboxSelectMultiple,
            label="Select optional flights"
        )

        def clean(self):
            cleaned_data = super().clean()
            has_optional = cleaned_data.get('has_optional_flights')
            all_optional = cleaned_data.get('all_flights_optional')
            selected_optional = cleaned_data.get('select_optional_flights')

            if has_optional == 'yes':
                if not all_optional and not selected_optional:
                    raise ValidationError('You must choose whether all flights are optional or select specific optional flights.')

    return OptionalFlightsForm