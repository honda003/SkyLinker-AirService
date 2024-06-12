from django import forms
from django.core.exceptions import ValidationError
from datetime import date

class HoursMinutesField(forms.Field):
    def to_python(self, value):
        if not value:
            return None
        try:
            hours, minutes = map(int, value.split(':'))
            if minutes < 0 or minutes >= 60:
                raise ValueError("Minutes must be between 00 and 59.")
            return hours  + minutes / 60
        except ValueError:
            raise forms.ValidationError("Enter a valid time format (HH:MM).")

    def prepare_value(self, value):
        if value is None:
            return ''
        try:
            total_hours = int(value)
            hours = total_hours %  60
            minutes = total_hours // 60
            return f"{hours}:{str(minutes).zfill(2)}"
        except (ValueError, TypeError):
            return value  # Return the original value if conversion is not applicable

class TaskIntervalForm(forms.Form):
    Calendar_status = forms.DateField(label='Date Interval', widget=forms.SelectDateWidget, required=False)
    FH_status = HoursMinutesField(label='Flight Hours Interval', required=False, help_text="Enter time in HH:MM format")
    FC_status = forms.IntegerField(label='Flight Cycles Interval', required=False)

    def clean(self):
        cleaned_data = super().clean()
        calendar_status = cleaned_data.get('Calendar_status')
        fh_status = cleaned_data.get('FH_status')
        fc_status = cleaned_data.get('FC_status')

        if not calendar_status and fh_status is None and fc_status is None:
            raise ValidationError("At least one interval must be provided.")
        return cleaned_data

    def clean_Calendar_status(self):
        input_date = self.cleaned_data['Calendar_status']
        if input_date and input_date <= date.today():
            raise ValidationError("The date must be in the future.")
        return input_date