from django.shortcuts import render, redirect
from .forms import LastDoneTaskForm, LastDonePackageForm, LastDoneUploadForm
import pandas as pd
from .models import LastDone
from AMP.models import ExcelData
from .models import LastDone
from AMP.models import ExcelData, DueClearance
from Operator.models import OperatorInput, AircraftDetails
from .forms import LastDoneEditForm, FilterForm, PackageUpdateForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django import forms
from django.contrib.contenttypes.models import ContentType

def convert_to_minutes(fh_str):
        if fh_str and ':' in fh_str:
            hours, minutes = map(int, fh_str.split(':'))
            return hours * 60 + minutes
        return 0
    
class ChooseAirlineAircraftForm(forms.Form):
    airline = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label="Choose Airline")
    aircraft = forms.ModelChoiceField(queryset=AircraftDetails.objects.all(), label="Choose Aircraft")
    
class DueClearanceForm(forms.ModelForm):
    class Meta:
        model = DueClearance
        fields = ['DY_clearance', 'FH_clearance', 'FC_clearance']  # Include other fields as needed
    
@login_required
def choose_airline_aircraft(request):
    if request.method == 'POST':
        form = ChooseAirlineAircraftForm(request.POST)
        if form.is_valid():
            request.session['airline_id'] = form.cleaned_data['airline'].id
            request.session['aircraft_id'] = form.cleaned_data['aircraft'].id
            return redirect('state_due_clearance')
    else:
        form = ChooseAirlineAircraftForm()
    return render(request, 'pages/ldnd.html', {'form': form})

def state_due_clearance(request):
    airline_id = request.session.get('airline_id')
    aircraft_id = request.session.get('aircraft_id')

    if not airline_id or not aircraft_id:
        return redirect('choose_airline_aircraft')  # Redirect if session data is missing

    due_clearances = DueClearance.objects.filter(
        Airline_Name_id=airline_id,
        Aircraft_Name__id=aircraft_id 
    )

    if request.method == 'POST':
        # Update the DueClearance objects here
        for due_clearance in due_clearances:
            form = DueClearanceForm(request.POST, instance=due_clearance)
            if form.is_valid():
                form.save()
        return redirect('last_done_list')
    else:
        forms = [DueClearanceForm(instance=due_clearance) for due_clearance in due_clearances]
    return render(request, 'pages/ldnd.html', {'forms': forms})

def last_done_list(request):
    
    airline_id = request.session.get('airline_id')
    aircraft_id = request.session.get('aircraft_id')
    
    if not airline_id or not aircraft_id:
        return redirect('choose_airline_aircraft')  # Redirect if session data is missing
    
    
    filter_form = FilterForm(request.GET)
    
    # Sorting
    sort_by = request.GET.get('sort', 'excel_data__MPD_ITEM_NUMBER')
    sort_order = request.GET.get('order', 'asc')
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
        
    data = LastDone.objects.filter(
        Airline_Name_id=airline_id,
        Aircraft_Name_id=aircraft_id
    ).order_by(request.GET.get('sort', 'excel_data__MPD_ITEM_NUMBER'))
    
    packages = data.values_list('excel_data__PACKAGE', flat=True).distinct()

    if filter_form.is_valid():
        filters = {
            'al_due': filter_form.cleaned_data['al_due'],
            'mpd_due': filter_form.cleaned_data['mpd_due'],
            'package': filter_form.cleaned_data.get('package'),
            'search_mpd_number': filter_form.cleaned_data['search_mpd_number']
        }

        if filters['al_due']:
            data = data.filter(al_due=filters['al_due'])

        if filters['mpd_due']:
            data = data.filter(mpd_due=filters['mpd_due'])

        if filters['search_mpd_number']:
            data = data.filter(excel_data__MPD_ITEM_NUMBER__icontains=filters['search_mpd_number'])

        if filters['package']:
            data = data.filter(excel_data__PACKAGE=filters['package'])

    # Perform data formatting after applying filters
    for item in data:
        if item.last_done_fh:
            total_minutes = int(item.last_done_fh)
            hours, minutes = divmod(total_minutes, 60)
            item.last_done_fh_formatted = f"{hours}:{minutes:02d}"
        else:
            item.last_done_fh_formatted = None
        item.package = item.excel_data.PACKAGE if item.excel_data else None

    paginator = Paginator(data, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    edit_form = LastDoneEditForm()

    if request.method == 'POST':
        if 'update_package' in request.POST:
            package_form = PackageUpdateForm(request.POST)
            if package_form.is_valid():
                package = package_form.cleaned_data['package']
                new_last_done_date = package_form.cleaned_data['last_done_date']
                new_last_done_fh = package_form.cleaned_data['last_done_fh']
                new_last_done_fc = package_form.cleaned_data['last_done_fc']

                affected_records = LastDone.objects.filter(excel_data__PACKAGE=package)

                for record in affected_records:
                    original_date = record.last_done_date
                    original_fh = record.last_done_fh
                    original_fc = record.last_done_fc

                    # Log the change for each record
                    change_message = []
                    if original_date != new_last_done_date:
                        change_message.append(f"Last Done Date changed from {original_date} to {new_last_done_date}")
                    if original_fh != new_last_done_fh:
                        change_message.append(f"Last Done FH changed from {original_fh} to {new_last_done_fh}")
                    if original_fc != new_last_done_fc:
                        change_message.append(f"Last Done FC changed from {original_fc} to {new_last_done_fc}")

                    # Update the record
                    record.last_done_date = new_last_done_date
                    record.last_done_fh = convert_to_minutes(new_last_done_fh)
                    record.last_done_fc = new_last_done_fc
                    record.save()

                    # If there were any changes, log them
                    if change_message:
                        LogEntry.objects.log_action(
                            user_id=request.user.id,
                            content_type_id=ContentType.objects.get_for_model(record).id,
                            object_id=record.id,
                            object_repr=str(record),
                            action_flag=CHANGE,
                            change_message=f"Package {package}: " + ", ".join(change_message)
                        )

                return redirect('last_done_list')
        else:
            last_done_id = request.POST.get('last_done_id')
            last_done_instance = LastDone.objects.get(id=last_done_id)
            original_instance = LastDone.objects.get(id=last_done_id)  # Get the original data
            edit_form = LastDoneEditForm(request.POST, instance=last_done_instance)

            if edit_form.is_valid():
                last_done = edit_form.save(commit=False)
                last_done.modified_by = request.user
                edit_form.save()

                # Detect changes
                changes = []
                for field in edit_form.changed_data:
                    original_value = getattr(original_instance, field, None)
                    new_value = getattr(last_done, field, None)
                    changes.append(f"{field} changed from {original_value} to {new_value}")

                change_message = f"MPD Item Number {original_instance.excel_data} Modified by {request.user.username}: " + ", ".join(changes)
                
                # Record change in custom ChangeLog
                # Log entry
                LogEntry.objects.log_action(
                    user_id=request.user.id,
                    content_type_id=ContentType.objects.get_for_model(last_done).id,
                    object_id=last_done.id,
                    object_repr=str(last_done),
                    action_flag=CHANGE,
                    change_message=change_message
                )

                return redirect('last_done_list')

    return render(request, 'pages/ldnd.html', {
        'packages': packages,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'edit_form': edit_form,
        'sort_by': sort_by.lstrip('-'),  # Keep the sort field without the '-' prefix for display
        'sort_order': 'desc' if sort_order == 'desc' else 'asc'  # Toggle sort order for the next click
    })
