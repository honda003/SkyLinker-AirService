from django.shortcuts import render, redirect
from .forms import OperatorForm, AircraftsForm
from .models import OperatorInput, AircraftDetails
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.forms import formset_factory
from django.db import transaction


def L_Intervals(num_L_packages, operator_input):
    L_intervals = {}
    # Initialize intervals for L1
    L1_FC_interval_lower = operator_input.L1_FC
    L1_FH_interval_lower = operator_input.L1_FH
    L1_DY_interval_lower = operator_input.L1_DY

    L1_FC_interval_upper = L1_FC_interval_lower * 2
    L1_FH_interval_upper = L1_FH_interval_lower * 2
    L1_DY_interval_upper = L1_DY_interval_lower * 2
    L_intervals["L1"] = {
        "FC_Interval": {"lower_bound": L1_FC_interval_lower, "upper_bound": L1_FC_interval_upper},
        "FH_Interval": {"lower_bound": L1_FH_interval_lower, "upper_bound": L1_FH_interval_upper},
        "DY_Interval": {"lower_bound": L1_DY_interval_lower, "upper_bound": L1_DY_interval_upper}
    }
    # Calculate intervals for rest of Ls
    for i in range(2, num_L_packages + 1):
        prev_L_interval = L_intervals[f"L{i-1}"]
        # Calculate lower bound based on upper bound of previous L interval
        L_FC_interval_lower = prev_L_interval["FC_Interval"]["upper_bound"]
        L_FH_interval_lower = prev_L_interval["FH_Interval"]["upper_bound"]
        L_DY_interval_lower = prev_L_interval["DY_Interval"]["upper_bound"]
        # Calculate upper bound twice the lower bound
        L_FC_interval_upper = L_FC_interval_lower + L1_FC_interval_lower
        L_FH_interval_upper = L_FH_interval_lower + L1_FH_interval_lower
        L_DY_interval_upper = L_DY_interval_lower + L1_DY_interval_lower
        L_intervals[f"L{i}"] = {
            "FC_Interval": {"lower_bound": L_FC_interval_lower, "upper_bound": L_FC_interval_upper},
            "FH_Interval": {"lower_bound": L_FH_interval_lower, "upper_bound": L_FH_interval_upper},
            "DY_Interval": {"lower_bound": L_DY_interval_lower, "upper_bound": L_DY_interval_upper}
        }

    return L_intervals


def C_Intervals(num_C_packages, operator_input):
    C_intervals = {}
    # Initialize intervals for L1
    C1_FC_interval_lower = operator_input.C1_FC
    C1_FH_interval_lower = operator_input.C1_FH
    C1_YR_interval_lower = operator_input.C1_YR

    C1_FC_interval_upper = C1_FC_interval_lower * 2
    C1_FH_interval_upper = C1_FH_interval_lower * 2
    C1_YR_interval_upper = C1_YR_interval_lower * 2
    C_intervals["C1"] = {
        "FC_Interval": {"lower_bound": C1_FC_interval_lower, "upper_bound": C1_FC_interval_upper},
        "FH_Interval": {"lower_bound": C1_FH_interval_lower, "upper_bound": C1_FH_interval_upper},
        "YR_Interval": {"lower_bound": C1_YR_interval_lower, "upper_bound": C1_YR_interval_upper}
    }
    # Calculate intervals for rest of Ls
    for i in range(2, num_C_packages + 1):
        prev_C_interval = C_intervals[f"C{i-1}"]
        # Calculate lower bound based on upper bound of previous L interval
        C_FC_interval_lower = prev_C_interval["FC_Interval"]["upper_bound"]
        C_FH_interval_lower = prev_C_interval["FH_Interval"]["upper_bound"]
        C_YR_interval_lower = prev_C_interval["YR_Interval"]["upper_bound"]
        # Calculate upper bound twice the lower bound
        C_FC_interval_upper = C_FC_interval_lower + C1_FC_interval_lower
        C_FH_interval_upper = C_FH_interval_lower + C1_FH_interval_lower
        C_YR_interval_upper = C_YR_interval_lower + C1_YR_interval_lower
        C_intervals[f"C{i}"] = {
            "FC_Interval": {"lower_bound": C_FC_interval_lower, "upper_bound": C_FC_interval_upper},
            "FH_Interval": {"lower_bound": C_FH_interval_lower, "upper_bound": C_FH_interval_upper},
            "YR_Interval": {"lower_bound": C_YR_interval_lower, "upper_bound": C_YR_interval_upper}
        }

    return C_intervals
    

@login_required
def operator(request):
    form_submitted = False
    operator_input = None  # Initialize to None to handle cases where it's not set

    if request.method == 'POST':
        form = OperatorForm(request.POST)
        aircrafts_form = AircraftsForm(request.POST)

        if form.is_valid() and aircrafts_form.is_valid():
            airline_name = form.cleaned_data['Airline_Name']
            num_aircrafts = aircrafts_form.cleaned_data['num_aircrafts']
            FC_DY = form.cleaned_data['FC_DY']
            FH_DY = form.cleaned_data['FH_DY']
            Daily = form.cleaned_data['Daily']
            Weekly = form.cleaned_data['Weekly']
            Service_DY = form.cleaned_data['Service_DY']
            Service_FH = form.cleaned_data['Service_FH']
            Service_FC = form.cleaned_data['Service_FC']
            L_no = form.cleaned_data['L_no']
            L1_DY = form.cleaned_data['L1_DY']
            L1_FH = form.cleaned_data['L1_FH']
            L1_FC = form.cleaned_data['L1_FC']
            C_no = form.cleaned_data['C_no']
            C1_YR = form.cleaned_data['C1_YR']
            C1_FH = form.cleaned_data['C1_FH']
            C1_FC = form.cleaned_data['C1_FC']
            

            # Fetch existing OperatorInput or create new if not exist
            operator_input, created = OperatorInput.objects.get_or_create(
                Airline_Name=airline_name
            )
            if not created:
                # Update num_aircrafts if the operator already exists
                operator_input.FC_DY = FC_DY
                operator_input.FH_DY = FH_DY
                operator_input.Daily = Daily
                operator_input.Weekly = Weekly
                operator_input.Service_DY = Service_DY
                operator_input.Service_FH = Service_FH
                operator_input.Service_FC = Service_FC
                operator_input.L_no = L_no
                operator_input.L1_DY = L1_DY
                operator_input.L1_FH = L1_FH
                operator_input.L1_FC = L1_FC
                operator_input.C_no = C_no
                operator_input.C1_YR = C1_YR
                operator_input.C1_FH = C1_FH
                operator_input.C1_FC = C1_FC
                operator_input.num_aircrafts = num_aircrafts
                operator_input.save()

            # Clear existing aircraft details for this operator input
            AircraftDetails.objects.filter(Airline_Name=operator_input).delete()

            # Create new aircraft details
            for i in range(1, num_aircrafts + 1):
                aircraft_type = request.POST.get(f'aircraft_type_{i}', '')
                aircraft_name = request.POST.get(f'aircraft_name_{i}', '')
                production_date_str = request.POST.get(f'production_date_{i}', '')
                ac_sn = request.POST.get(f'ac_sn_{i}', '')
                ac_bn = request.POST.get(f'ac_bn_{i}', '')
                ac_ln = request.POST.get(f'ac_ln_{i}', '')
                production_date = parse_date(production_date_str) if production_date_str else None

                AircraftDetails.objects.create(
                    Airline_Name=operator_input,
                    aircraft_type=aircraft_type,
                    aircraft_name=aircraft_name,
                    production_date=production_date,
                    ac_sn=ac_sn,
                    ac_ln=ac_ln,
                    ac_bn=ac_bn,
                )

            form_submitted = True
    else:
        form = OperatorForm()
        aircrafts_form = AircraftsForm()
        
    if operator_input:
        num_L_packages = operator_input.L_no
        L_intervals = L_Intervals(num_L_packages, operator_input)

        num_C_packages = operator_input.C_no
        C_intervals = C_Intervals(num_C_packages, operator_input)
    else:
        # Initialize these variables to None or appropriate defaults
        L_intervals = None
        C_intervals = None

    return render(request, 'pages/operator.html', {
        'aircrafts_form': aircrafts_form,
        'form': form,
        'operator_input': operator_input,
        'L_intervals': L_intervals,
        'C_intervals': C_intervals,
        'form_submitted': form_submitted  # Pass the flag to the template
    })