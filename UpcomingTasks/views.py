from django.shortcuts import render, redirect
from .forms import TaskIntervalForm
from LDND.models import LastDone
from AircraftData.models import AircraftData
from django.core.paginator import Paginator
from AMP.models import ExcelData, DueClearance
from Operator.models import OperatorInput, AircraftDetails
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import pandas as pd

class ChooseAirlineAircraftForm(forms.Form):
    airline = forms.ModelChoiceField(queryset=OperatorInput.objects.all(), label="Choose Airline")
    aircraft = forms.ModelChoiceField(queryset=AircraftDetails.objects.all(), label="Choose Aircraft")
    
    
@login_required
def uk_choose_airline_aircraft(request):
    if request.method == 'POST':
        form = ChooseAirlineAircraftForm(request.POST)
        if form.is_valid():
            request.session['airline_id'] = form.cleaned_data['airline'].id
            request.session['aircraft_id'] = form.cleaned_data['aircraft'].id
            
            return redirect('upcoming_tasks')
    else:
        form = ChooseAirlineAircraftForm()
    return render(request, 'pages/upcomingtasks.html', {'form': form})

def upcoming_tasks(request):
      
    airline_id = request.session.get('airline_id')
    aircraft_id = request.session.get('aircraft_id')
    
    if airline_id and aircraft_id:
        airline = OperatorInput.objects.get(id=airline_id)
        aircraft = AircraftDetails.objects.get(id=aircraft_id)
        # Now use airline and aircraft as needed
    else:
        # Handle the case where the session data is not available
        return redirect('uk_choose_airline_aircraft')
    

    
    if request.method == 'POST':
        form = TaskIntervalForm(request.POST)
        if form.is_valid():
            calendar_status = form.cleaned_data['Calendar_status']
            fh_status_input = form.cleaned_data['FH_status']  # This is a string in HH:MM
            fc_status = form.cleaned_data['FC_status']
            
            aircraft_data = AircraftData.objects.filter(
                                Airline_Name_id=airline_id,
                                Aircraft_Name_id=aircraft_id
                            )

            current_date = aircraft_data.latest('current_date').current_date
            current_fh = aircraft_data.latest('current_flight_hours').current_flight_hours  # Assuming this is also a string in HH:MM
            current_fc = aircraft_data.latest('current_flight_cycles').current_flight_cycles

            # Convert current flight hours and input flight hours to total hours
            current_fh_hours = convert_to_total_hours(current_fh)
            fh_status = fh_status_input if fh_status_input else None
            
            # print(current_fh_hours)
            # print(fh_status_input)
            # print(fh_status)

            # Fetch all potential tasks
            all_tasks = LastDone.objects.filter(
                            Airline_Name_id=airline_id,
                            Aircraft_Name_id=aircraft_id
                        ).order_by(request.GET.get('sort', 'excel_data__MPD_ITEM_NUMBER'))
            
        # Define column names
            airline_column = ['MPD ITEM NUMBER', 'Airline Next Due By Date', 'Airline Next Due By Flight Hours', 'Airline Next Due By Flight Cycles']
            MPD_column = ['MPD ITEM NUMBER', 'MPD Next Due By Date', 'MPD Next Due By Flight Hours', 'MPD Next Due By Flight Cycles']

            # Initialize empty DataFrames
            airline_df = pd.DataFrame(columns=airline_column)
            MPD_df = pd.DataFrame(columns=MPD_column)

            # Filter tasks where any of the conditions are met
            al_due_tasks = []
            mpd_due_tasks = []

            # Lists to store row data for DataFrames
            airline_data = []
            mpd_data = []

            for task in all_tasks:
                al_task_date_due = (task.al_nd_date and task.al_nd_date <= calendar_status) if calendar_status and task.al_nd_date is not None else False
                al_task_fh_due = (task.al_nd_fh and convert_to_total_hours(task.al_nd_fh) <= current_fh_hours + fh_status) if fh_status and task.al_nd_fh is not None else False
                al_task_fc_due = (task.al_nd_fc and task.al_nd_fc <= current_fc + fc_status) if fc_status and task.al_nd_fc is not None else False
                
                if al_task_date_due or al_task_fh_due or al_task_fc_due:
                    al_due_tasks.append(task)
                    airline_data.append([
                        task.excel_data,
                        task.al_nd_date,
                        task.al_nd_fh,
                        task.al_nd_fc
                    ])
                    
                mpd_task_date_due = (task.mpd_nd_date and task.mpd_nd_date <= calendar_status) if calendar_status and task.mpd_nd_date is not None else False
                mpd_task_fh_due = (task.mpd_nd_fh and convert_to_total_hours(task.mpd_nd_fh) <= current_fh_hours + fh_status) if fh_status and task.mpd_nd_fh is not None else False
                mpd_task_fc_due = (task.mpd_nd_fc and task.mpd_nd_fc <= current_fc + fc_status) if fc_status and task.mpd_nd_fc is not None else False
                
                if mpd_task_date_due or mpd_task_fh_due or mpd_task_fc_due:
                    mpd_due_tasks.append(task)
                    mpd_data.append([
                        task.excel_data,
                        task.mpd_nd_date,
                        task.mpd_nd_fh,
                        task.mpd_nd_fc
                    ])

            # Convert lists to DataFrames
            airline_df = pd.DataFrame(airline_data, columns=airline_column)
            MPD_df = pd.DataFrame(mpd_data, columns=MPD_column)
            
            airline_df['Airline Next Due By Date'] = airline_df['Airline Next Due By Date'].fillna('No Due Date')
            airline_df['Airline Next Due By Flight Hours'] = airline_df['Airline Next Due By Flight Hours'].fillna('No Due Flight Hours')
            airline_df['Airline Next Due By Flight Cycles'] = airline_df['Airline Next Due By Flight Cycles'].fillna('No Due Flight Cycle')

            MPD_df['MPD Next Due By Date'] = MPD_df['MPD Next Due By Date'].fillna('No Due Flight Date')
            MPD_df['MPD Next Due By Flight Hours'] = MPD_df['MPD Next Due By Flight Hours'].fillna('No Due Flight Hours')
            MPD_df['MPD Next Due By Flight Cycles'] = MPD_df['MPD Next Due By Flight Cycles'].fillna('No Due Flight Cycle')
                        
            return render(request, 'pages/upcomingtasks.html', {
                'airline': airline,
                'aircraft': aircraft,
                'forms': form,
                'al_due_tasks': al_due_tasks,
                'mpd_due_tasks': mpd_due_tasks,
                'airline_df': airline_df.to_html(classes=["table", "table-striped"], index=False),
                'MPD_df': MPD_df.to_html(classes=["table", "table-striped"], index=False),
            })
    else:
        form = TaskIntervalForm()

    return render(request, 'pages/upcomingtasks.html', {
        'airline' : airline,
        'aircraft': aircraft,
        'forms': form,
        'due_tasks': None
    })
    
# def send_upcoming_tasks_email(request):
#     all_tasks = LastDone.objects.all()
    
#     # Define one month ahead
#     one_month_ahead = timezone.now().date() + timedelta(days=30)

#     # Filter tasks due within the next month
#     tasks_next_month = [task for task in all_tasks if task.al_nd_date and task.al_nd_date <= one_month_ahead]
    
#     # If there are tasks due within the next month, send an email
#     if tasks_next_month:
#         message = "The following tasks have dues within the next month:\n" + "\n".join([f"{task.excel_data} due by {task.al_nd_date}" for task in tasks_next_month])
#         send_mail(
#             'Upcoming Due Tasks',
#             message,
#             'eslammahmoud01.eng@gmail.com',
#             [request.user.email],
#             fail_silently=False,
#     )
    

def convert_to_total_hours(fh_str):
    fh_str = str(fh_str)
    if fh_str and ':' in fh_str:
        hours, minutes = map(int, fh_str.split(':'))
        return hours + minutes / 60.0
    return 0