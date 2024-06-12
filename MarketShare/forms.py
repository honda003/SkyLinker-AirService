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

def has_historical_data_form():
    class HistoricalDataForm(forms.Form):
        has_historical_data = forms.ChoiceField(
            choices=[('yes', 'Yes'), ('no', 'No')],
            widget=forms.RadioSelect,
            label="Do you have historical data excel file?",
            initial='no'
        )
    return HistoricalDataForm
