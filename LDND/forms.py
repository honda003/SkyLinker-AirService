from django import forms
from .models import LastDone
from AMP.models import ExcelData  # Ensure you have access to this model\
import re
from Operator.models import OperatorInput, AircraftDetails 


class DateInput(forms.DateInput):
    input_type = 'date'

class HoursMinutesField(forms.Field):
    def to_python(self, value):
        if not value:
            return None
        try:
            hours, minutes = map(int, value.split(':'))
            if minutes < 0 or minutes >= 60:
                raise ValueError("Minutes must be between 00 and 59.")
            return hours * 60 + minutes
        except ValueError:
            raise forms.ValidationError("Enter a valid time format (HH:MM).")

    def prepare_value(self, value):
        if value is None:
            return ''
        try:
            total_minutes = int(value)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours}:{str(minutes).zfill(2)}"
        except (ValueError, TypeError):
            return value  # Return the original value if conversion is not applicable


class LastDoneTaskForm(forms.ModelForm):
    Airline_Name = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label='Choose Airline')
    Aircraft_Name = forms.ModelChoiceField(queryset=AircraftDetails.objects.all(), label='Choose Aircraft')
    last_done_fh = HoursMinutesField(required=False, label='Last Done Flight Hours', help_text="Enter time in HH:MM format")

    class Meta:
        model = LastDone
        fields = ['Airline_Name', 'Aircraft_Name', 'excel_data', 'last_done_date', 'last_done_fh', 'last_done_fc']
        labels = {
            'excel_data': 'MPD Item Number',
            'last_done_date': 'Last Done Date',
            'last_done_fh': 'Last Done Flight Hours',
            'last_done_fc': 'Last Done Flight Cycles',
        }
        widgets = {
            'last_done_date': DateInput(),
        }

class LastDonePackageForm(forms.ModelForm):
    Airline_Name = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label='Choose Airline')
    Aircraft_Name = forms.ModelChoiceField(queryset=AircraftDetails.objects.all(), label='Choose Aircraft')
    package = forms.ChoiceField(choices=[], required=True, label="Select Package")
    last_done_date = forms.DateField(required=False, widget=DateInput())
    last_done_fh = HoursMinutesField(required=False, label="Last Done Flight Hours", help_text="Enter time in HH:MM format")
    last_done_fc = forms.FloatField(required=False, label="Last Done Flight Cycles")

    class Meta:
        model = LastDone
        fields = ['Airline_Name', 'Aircraft_Name', 'package', 'last_done_date', 'last_done_fh', 'last_done_fc']
        labels = {
            'last_done_date': 'Last Done Date',
            'last_done_fh': 'Last Done Flight Hours',
            'last_done_fc': 'Last Done Flight Cycles',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        unique_packages = ExcelData.objects.values_list('PACKAGE', flat=True).distinct()
        self.fields['package'].choices = [(package, package) for package in unique_packages]
        
class LastDoneUploadForm(forms.Form):
    Airline_Name = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label='Choose Airline')
    Aircraft_Name = forms.ModelChoiceField(queryset=AircraftDetails.objects.all(), label='Choose Aircraft')
    excel_file = forms.FileField(label='Upload Excel File')
    
class FilterForm(forms.Form):
    AL_DUE_CHOICES = [
        ('', 'Airline Due'),  # Placeholder-like option
        ('DUE', 'DUE'),
        ('NOT DUE', 'NOT DUE'),
    ]
    MPD_DUE_CHOICES = [
        ('', 'MPD Due'),  # Placeholder-like option
        ('DUE', 'DUE'),
        ('NOT DUE', 'NOT DUE'),
    ]

    al_due = forms.ChoiceField(choices=AL_DUE_CHOICES, required=False, label='')
    mpd_due = forms.ChoiceField(choices=MPD_DUE_CHOICES, required=False, label='')
    package = forms.ChoiceField(required=False, label='')
    search_mpd_number = forms.CharField(required=False, label='', widget=forms.TextInput(attrs={'placeholder': 'Search MPD Number'}))

    def __init__(self, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)

        packages = ExcelData.objects.values_list('PACKAGE', flat=True).distinct()
        non_empty_packages = [pkg for pkg in packages if pkg]
        def sort_key(x):
            numbers = re.findall(r'\d+', x)
            prefix = re.match(r'\D*', x).group()
            return (prefix, int(numbers[0]) if numbers else 0, x)
        sorted_packages = sorted(non_empty_packages, key=sort_key)
        
        # Define package choices with an initial placeholder
        package_choices = [('','Package')] + [(package, package) for package in sorted_packages]
        self.fields['package'].choices = package_choices

    
class LastDoneEditForm(forms.ModelForm):
    last_done_date = forms.DateField(required=False, widget=DateInput())
    last_done_fh = HoursMinutesField(required=False, help_text="Enter time in HH:MM format")
    last_done_fc = forms.FloatField(required=False,)

    class Meta:
        model = LastDone
        fields = ['last_done_date', 'last_done_fh', 'last_done_fc']
        labels = {
            'last_done_date': 'Last Done Date',
            'last_done_fh': 'Last Done Flight Hours',
            'last_done_fc': 'Last Done Flight Cycles',
        }
        widgets = {
            'last_done_date': DateInput(),
        }
        
class PackageUpdateForm(forms.ModelForm):
    class Meta:
        model = LastDone
        fields = ['last_done_date', 'last_done_fh', 'last_done_fc']

    package = forms.ChoiceField(choices=[], required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].choices = [
            (pkg, pkg) for pkg in LastDone.objects.values_list('excel_data__PACKAGE', flat=True).distinct()
        ]
    

