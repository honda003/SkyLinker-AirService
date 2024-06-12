from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from LDND.models import LastDone
from SkyLinker.celery import app
from SkyLinker import settings
from Operator.models import OperatorInput, AircraftDetails
from AircraftData.models import AircraftData
from collections import defaultdict
import logging

def convert_to_total_hours(fh_str):
    fh_str = str(fh_str)
    if fh_str and ':' in fh_str:
        hours, minutes = map(int, fh_str.split(':'))
        return hours + minutes / 60.0
    return 0

@app.task(name='send_upcoming_tasks_monthly_email')
def send_upcoming_tasks_monthly_email():
    logging.info("Task started")
    operators = OperatorInput.objects.all()
    
    for operator in operators:
        aircrafts = AircraftDetails.objects.filter(Airline_Name=operator)
        
        for aircraft in aircrafts:
            airline_name = operator.Airline_Name
            aircraft_name = aircraft.aircraft_name
            
            all_tasks = LastDone.objects.filter(
                Airline_Name=operator,
                Aircraft_Name=aircraft
            )
            
            print(aircraft_name)
            print(all_tasks)
            
            current_date = timezone.now().date()
            one_month_ahead = timezone.now().date() + timedelta(days=30)
            tasks_next_month = [task for task in all_tasks if task.al_nd_date and task.al_nd_date <= one_month_ahead]
            
            # Sort tasks by date from latest to earliest
            tasks_next_month = sorted(tasks_next_month, key=lambda x: x.al_nd_date, reverse=True)
        
            if tasks_next_month:
                tasks_by_item = defaultdict(list)
                for task in tasks_next_month:
                    tasks_by_item[task.excel_data].append(task.al_nd_date)

                message_lines = [f"There are {len(tasks_next_month)} task have due within the next month:\n"]
                message_lines.append("MPD Item Number     Due By")
                message_lines.append("--------------------------    ---------")

                for item_number, due_dates in tasks_by_item.items():
                    for due_date in sorted(due_dates):
                        message_lines.append(f"{item_number}               {due_date.strftime('%Y-%m-%d')}")

                message = "\n".join(message_lines)
                subject = f'{airline_name} upcoming Due of Tasks for aircraft {aircraft_name}'
                email_from = settings.EMAIL_HOST_USER
                email_to = 'lotfytaha@cu.edu.eg'  # Ensure it's a list

                send_mail(
                    subject,
                    message,
                    email_from,
                    [email_to],
                    fail_silently=False,
                )
                logging.info(f"Email sent to {email_to} with {len(tasks_next_month)} tasks due")
            else:
                subject = f'{airline_name} upcoming Due of Tasks for aircraft {aircraft_name}'
                message = f"There are no tasks with dues within the next month from {current_date}:\n"
                email_from = settings.EMAIL_HOST_USER
                email_to = 'lotfytaha@cu.edu.eg'  # Ensure it's a list
                send_mail(
                    subject,
                    message,
                    email_from,
                    [email_to],
                    fail_silently=False,
                )
                logging.info(f"Email sent to {email_to} with {len(tasks_next_month)} tasks due")
                logging.info("No tasks due within the next month")

    logging.info("Task completed")