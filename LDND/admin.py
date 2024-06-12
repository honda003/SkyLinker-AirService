from django.contrib import admin
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from .models import LastDone
from AMP.models import ExcelData
import pandas as pd
from django.contrib import messages
from .forms import LastDoneTaskForm, LastDonePackageForm, LastDoneUploadForm
from datetime import timedelta
from Operator.views import L_Intervals, C_Intervals
from Operator.models import OperatorInput
from datetime import datetime
import openpyxl
from openpyxl.utils.cell import column_index_from_string
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.contrib.admin import SimpleListFilter
import re
import logging

logger = logging.getLogger(__name__)

########################### FILTERS #######################################

# Custom search that handles misspelling for MPD_ITEM_NUMBER

class AirlineDueFilter(SimpleListFilter):
    title = 'Airline Due'
    parameter_name = 'al_due'

    def lookups(self, request, model_admin):
        return [
            ('DUE', 'DUE'),
            (None, None),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'DUE':
            return queryset.filter(al_due='DUE')
        if self.value() == 'NOT DUE':
            return queryset.exclude(al_due='DUE')

class MPDDueFilter(SimpleListFilter):
    title = 'MPD Due'
    parameter_name = 'mpd_due'

    def lookups(self, request, model_admin):
        return [
            ('DUE', 'DUE'),
            ('NOT DUE', 'NOT DUE'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'DUE':
            return queryset.filter(mpd_due='DUE')
        if self.value() == 'NOT DUE':
            return queryset.exclude(mpd_due='DUE')
        
        
class PackageFilter(admin.SimpleListFilter):
    title = _('package')
    parameter_name = 'PACKAGE'

    def lookups(self, request, model_admin):
        packages = ExcelData.objects.values_list('PACKAGE', flat=True).distinct()
        non_empty_packages = [pkg for pkg in packages if pkg]

        def sort_key(x):
            numbers = re.findall(r'\d+', x)
            prefix = re.match(r'\D*', x).group()
            return (prefix, int(numbers[0]) if numbers else 0, x)

        sorted_packages = sorted(non_empty_packages, key=sort_key)

        return [(package, package) for package in sorted_packages if package]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(excel_data__PACKAGE=self.value())
        return queryset

########################################################################

# Custom admin for LastDone model
class LastDoneAdmin(admin.ModelAdmin):
    change_list_template = "admin/ldnd_changelist.html"
    list_display = ('Airline_Name', 'Aircraft_Name', 'excel_data', 'get_package', 'last_done_date', 'last_done_FH', 'last_done_fc', 'done', 'al_nd_date', 'al_nd_fh', 'al_nd_fc', 'al_due', 'mpd_nd_date', 'mpd_nd_fh', 'mpd_nd_fc', 'mpd_due')
    
    def get_package(self, obj):
        return obj.excel_data.PACKAGE
    get_package.short_description = 'PACKAGE'  # Sets column name
    
    def last_done_FH(self, obj):
        # Convert minutes to HH:MM format
        total_minutes = obj.last_done_fh
        if total_minutes is None or total_minutes == '':
            return None  # Return an empty string if the value is None or empty
        try:
            total_minutes = int(total_minutes)  # Ensure the value is an integer
            hours, minutes = divmod(total_minutes, 60)
            return f"{int(hours)}:{int(minutes):02d}"
        except (ValueError, TypeError):
            return "Invalid format"  # Handle conversion errors

    last_done_FH.short_description = 'Last Done FH (HH:MM)'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload/', self.admin_site.admin_view(self.upload_excel), name='LDND_lastdone_upload'),
            path('add_task/', self.admin_site.admin_view(self.add_task), name='LDND_lastdone_add_task'),
            path('add_package/', self.admin_site.admin_view(self.add_package), name='LDND_lastdone_add_package'),
        ]
        return my_urls + urls

    def add_task(self, request):
        if request.method == "POST":
            form = LastDoneTaskForm(request.POST)
            if form.is_valid():
                last_done_instance = form.save(commit=False)
                last_done_instance.save()
                messages.success(request, "Task data added successfully.")
                return redirect("..")
        else:
            form = LastDoneTaskForm()
        return render(request, "admin/task_form.html", {"form": form})

    def add_package(self, request):
        if request.method == "POST":
            form = LastDonePackageForm(request.POST)
            if form.is_valid():
                Airline_Name = form.cleaned_data['Airline_Name']
                Aircraft_Name = form.cleaned_data['Aircraft_Name']
                package_name = form.cleaned_data['package']
                last_done_date = form.cleaned_data['last_done_date']
                last_done_fh = form.cleaned_data['last_done_fh']
                last_done_fc = form.cleaned_data['last_done_fc']

                tasks_linked_to_package = ExcelData.objects.filter(PACKAGE=package_name)

                for task in tasks_linked_to_package:
                    LastDone.objects.update_or_create(
                                excel_data=task,
                                Airline_Name=Airline_Name,
                                Aircraft_Name=Aircraft_Name,
                                defaults={
                                    'Airline_Name': Airline_Name,
                                    'Aircraft_Name': Aircraft_Name,
                                    'last_done_date': last_done_date,
                                    'last_done_fh': last_done_fh,
                                    'last_done_fc': last_done_fc,
                                    
                                }
                            )
                    # LastDone.objects.update_or_create(
                    #     excel_data=task,
                    #     defaults={
                    #         'last_done_date': last_done_date,
                    #         'last_done_fh': last_done_fh,
                    #         'last_done_fc': last_done_fc,
                    #     }
                    # )

                messages.success(request, "Last done data added successfully for package and its associated tasks.")
                return redirect("..")
        else:
            form = LastDonePackageForm()
        return render(request, "admin/package_form.html", {"form": form})
    
    def upload_excel(self, request):
        if request.method == "POST":
            form = LastDoneUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    excel_file = request.FILES['excel_file']
                    workbook = openpyxl.load_workbook(excel_file)
                    worksheet = workbook.active
                    
                    Airline_Name = form.cleaned_data['Airline_Name']
                    Aircraft_Name = form.cleaned_data['Aircraft_Name']

                    for row in worksheet.iter_rows(min_row=2, values_only=True):  # Skipping the header
                        mpd_item_number, last_done_date_val, last_done_fh_str, last_done_fc_str = row[:4]

                        if not mpd_item_number:  # Skip rows with no MPD_ITEM_NUMBER
                            continue

                        # Check if 'last_done_date_val' is already a datetime object
                        if last_done_date_val is not None and last_done_date_val != 'null':
                            if isinstance(last_done_date_val, datetime):
                                last_done_date = last_done_date_val.date()
                            else:
                                # If it's a string, parse it
                                last_done_date = datetime.strptime(last_done_date_val, '%d/%m/%Y').date() if last_done_date_val else None
                        else:
                            last_done_date = None
                            
                        if last_done_fh_str is not None and last_done_fh_str != 'null':
                            hours, minutes = map(int, last_done_fh_str.split(':')[:2])
                            last_done_fh_in_minutes = hours * 60 + minutes
                            last_done_fh = str(last_done_fh_in_minutes)
                        else:
                            last_done_fh = None
                            
                        if last_done_fc_str is not None and last_done_fc_str != 'null':
                            last_done_fc = float(last_done_fc_str) if last_done_fc_str else None
                        else:
                            last_done_fc = None
                            
                        excel_data = ExcelData.objects.filter(MPD_ITEM_NUMBER=mpd_item_number).first()

                        if excel_data:
                            last_done_instance, created = LastDone.objects.update_or_create(
                                excel_data=excel_data,
                                Airline_Name=Airline_Name,
                                Aircraft_Name=Aircraft_Name,
                                defaults={
                                    'Airline_Name': Airline_Name,
                                    'Aircraft_Name': Aircraft_Name,
                                    'last_done_date': last_done_date,
                                    'last_done_fh': last_done_fh,
                                    'last_done_fc': last_done_fc,
                                    
                                }
                            )

                    messages.success(request, "Excel data processed successfully.")
                    return redirect("..")

                except Exception as e:  # This block will handle any unexpected error during the process.
                    messages.error(request, f"An error occurred while processing the file: {e}")
                    return render(request, "admin/excel_form.html", {"form": form})

            else:  # This will run if the form is not valid.
                messages.error(request, "Please upload a valid excel file.")
                return render(request, "admin/excel_form.html", {"form": form})

        else:  # This will handle GET requests.
            form = LastDoneUploadForm()
            return render(request, "admin/excel_form.html", {"form": form})
        
    def search_mpd_item_number(self, queryset, search_term):
        normalized_search_term = search_term.replace('-', '').replace(' ', '')  # Normalize the search term
        return queryset.filter(
            excel_data__MPD_ITEM_NUMBER__icontains=normalized_search_term
        )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            normalized_search_term = search_term.replace('-', '').replace(' ', '')
            queryset |= queryset.filter(excel_data__MPD_ITEM_NUMBER__icontains=normalized_search_term)
        return queryset, use_distinct
        
    search_fields = ['excel_data__MPD_ITEM_NUMBER']
    list_filter = (AirlineDueFilter, MPDDueFilter, PackageFilter)
    
admin.site.register(LastDone, LastDoneAdmin)


