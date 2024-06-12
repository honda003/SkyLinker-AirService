import re
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import ExcelData, DueClearance
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from Operator.models import OperatorInput, AircraftDetails  # Adjust the import path according to your project's structure
import logging
from Operator.views import L_Intervals, C_Intervals
import json
from django.db.models import Q
from .forms import DueClearanceForm, ExcelDataForm, ExcelDataImportForm
from django.urls import path
from import_export.admin import ImportExportModelAdmin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render, redirect
from tablib import Dataset
from django.contrib import admin, messages
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.db.models import ForeignKey
from import_export.admin import ImportMixin

logger = logging.getLogger(__name__)

class ExcelDataResource(resources.ModelResource):
    Airline_Name = Field(
        attribute='Airline_Name',
        column_name='Airline_Name',
        widget=ForeignKeyWidget(OperatorInput, 'id')
    )
    Aircraft_Name = Field(
        attribute='Aircraft_Name',
        column_name='Aircraft_Name',
        widget=ManyToManyWidget(AircraftDetails, field='id', separator=',')
    )

    class Meta:
        model = ExcelData
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('MPD_ITEM_NUMBER',)
        fields = ('Airline_Name', 'Aircraft_Name', 'MPD_ITEM_NUMBER', 'TASK_CARD_NUMBER', 'THRES', 'REPEAT', 'ZONE', 'ACCESS', 'APL', 'ENG', 'ACCESS_HOURS', 'MAN_HOURS', 'TOTAL_HOURS', 'TASK_DESCRIPTION', 'TASK_TYPE', 'TASK_TITLE', 'PROGRAM', 'AREA', 'PACKAGE', 'REMARKS', 'CHECK', 'dynamic_applicability')

    def before_import_row(self, row, **kwargs):
        user_kwargs = kwargs.get('user_kwargs', {})
        airline = user_kwargs.get('airline')
        aircrafts = user_kwargs.get('aircraft')

        if airline:
            row['Airline_Name'] = airline.id

        if aircrafts:
            sorted_aircraft_ids = sorted(ac.id for ac in aircrafts)
            row['Aircraft_Name'] = ','.join(map(str, sorted_aircraft_ids))
        
        unique_aircraft_types = list(AircraftDetails.objects.values_list('aircraft_type', flat=True).distinct())
        applicability = {}

        APL_data = row.get('APL', '')
        for aircraft_type in unique_aircraft_types:
            applicable_column_name = f"APPLICABLE_FOR_{aircraft_type}"
            
            # Modify the aircraft_type to handle the optional space around the hyphen
            aircraft_type_with_optional_space = aircraft_type.replace('-', '[- ]?')

            # Create the exact pattern to match aircraft_type with or without spaces around the hyphen
            exact_pattern = rf'\b{aircraft_type_with_optional_space}\b'
            
            general_patterns = ['ALL', 'ALL NOTE']

            if re.search(exact_pattern, APL_data) or any(pat in APL_data for pat in general_patterns):
                applicability[applicable_column_name] = 'Y'
            else:
                applicability[applicable_column_name] = 'N'

        row['dynamic_applicability'] = json.dumps(applicability)

        return row

    def get_instance(self, instance_loader, row):
        existing_instances = ExcelData.objects.filter(
            MPD_ITEM_NUMBER=row.get('MPD_ITEM_NUMBER'),
            Airline_Name=row.get('Airline_Name')
        )

        for instance in existing_instances:
            existing_aircraft_ids = {aircraft.id for aircraft in instance.Aircraft_Name.all()}
            row_aircraft_ids = set(map(int, row.get('Aircraft_Name').split(',')))

            if existing_aircraft_ids == row_aircraft_ids:
                return instance

        return None

    def after_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        if not dry_run:
            if 'user_kwargs' in kwargs:
                aircrafts = kwargs['user_kwargs'].get('aircraft', [])
                instance.Aircraft_Name.set(aircrafts)
            instance.save()
            
            
class ExcelDataAdmin(ImportExportModelAdmin):
    form = ExcelDataForm
    resource_class = ExcelDataResource
    list_display = ('Airline_Name', 'get_aircraft_names', 'MPD_ITEM_NUMBER', 'TASK_CARD_NUMBER', 'THRES', 'APL', 'REPEAT', 'PACKAGE', 'CHECK')
    search_fields = ('MPD_ITEM_NUMBER', 'TASK_CARD_NUMBER')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('Aircraft_Name')

    def get_aircraft_names(self, obj):
        return ", ".join([aircraft.aircraft_name for aircraft in obj.Aircraft_Name.all()])
    get_aircraft_names.short_description = 'Aircraft Names'

    def get_list_filter(self, request):
        return [AirlineFilter, AircraftFilter, PackageFilter, ChecksFilter] + [make_dynamic_applicability_filter(field_name) for field_name in self.get_dynamic_fields()]

    def get_dynamic_fields(self):
        unique_aircraft_types = AircraftDetails.objects.values_list('aircraft_type', flat=True).distinct()
        return [f'APPLICABLE_FOR_{aircraft_type.replace(" ", "_").upper()}' for aircraft_type in unique_aircraft_types]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import/', self.admin_site.admin_view(self.import_view), name='excel_data_import'),
        ]
        return my_urls + urls

    def import_view(self, request):
        form = ExcelDataImportForm(request.POST or None, request.FILES or None)
        if request.method == 'POST' and form.is_valid():
            airline = form.cleaned_data['airline']
            aircraft = form.cleaned_data['aircraft']
            import_file = form.cleaned_data['import_file']

            return self.process_import(request, import_file, airline, aircraft)
        return render(request, "admin/amp_excel_import.html", {'form': form})

    def process_import(self, request, import_file, airline, aircrafts):
        try:
            data = import_file.read()
            dataset = Dataset()
            dataset.load(data, format='xlsx')

            user_kwargs = {'airline': airline, 'aircraft': aircrafts}
            resource = self.resource_class()
            result = resource.import_data(dataset, dry_run=False, user_kwargs=user_kwargs)

            if not result.has_errors():
                messages.success(request, "Import successful!")
            else:
                messages.error(request, "Import failed with errors.")
        except Exception as e:
            messages.error(request, f"Error during import: {str(e)}")
        return HttpResponseRedirect("..")

        
class DueClearanceAdmin(admin.ModelAdmin):
    form = DueClearanceForm
    list_display = ['Airline_Name', 'get_aircraft_names', 'DY_clearance', 'FH_clearance', 'FC_clearance']
    
    def get_aircraft_names(self, obj):
        return ", ".join([aircraft.aircraft_name for aircraft in obj.Aircraft_Name.all()])
    get_aircraft_names.short_description = 'Aircraft Names'
                    
# Remember to register the LastDoneAdmin
admin.site.register(DueClearance, DueClearanceAdmin)

admin.site.register(ExcelData, ExcelDataAdmin)



    
######################################### Filters ############################################################  
class BaseDynamicApplicabilityFilter(admin.SimpleListFilter):
    title = ''  # Placeholder, will be set by the factory
    parameter_name = ''  # Placeholder, will be set by the factory

    def lookups(self, request, model_admin):
        return (('Y', _('Yes')), ('N', _('No')),)

    def queryset(self, request, queryset):
        if self.value() in ('Y', 'N'):
            return queryset.filter(**{f"{self.parameter_name}": self.value()})
        return queryset

def make_dynamic_applicability_filter(field_name):
    # Create a new filter class for the specific field
    return type(
        f'DynamicApplicabilityFilter_{field_name}',
        (BaseDynamicApplicabilityFilter,),
        {
            'title': field_name.replace('_', ' ').capitalize(),
            'parameter_name': f'dynamic_applicability__{field_name}'
        }
    )
    
class AirlineFilter(admin.SimpleListFilter):
    title = _('Airline')
    parameter_name = 'airline_name'

    def lookups(self, request, model_admin):
        # Fetch distinct airline names from the OperatorInput model
        airlines = OperatorInput.objects.order_by('Airline_Name').distinct().values_list('id', 'Airline_Name')
        return [(id, name) for id, name in airlines if name]

    def queryset(self, request, queryset):
        if self.value():
            # Filter the queryset by the selected airline's ID
            return queryset.filter(Airline_Name__id=self.value())
        
class AircraftFilter(admin.SimpleListFilter):
    title = _('Aircraft')
    parameter_name = 'aircraft_name'

    def lookups(self, request, model_admin):
        # Fetch all aircraft entries from AircraftDetails
        aircrafts = AircraftDetails.objects.order_by('aircraft_name').values_list('id', 'aircraft_name')
        unique_aircrafts = set(aircrafts)  # Use set to remove duplicates
        return list(unique_aircrafts)

    def queryset(self, request, queryset):
        if self.value():
            # Filter the queryset by entries that have the selected aircraft
            return queryset.filter(Aircraft_Name__id=self.value())
        
class PackageFilter(admin.SimpleListFilter):
    title = _('package')
    parameter_name = 'PACKAGE'

    def lookups(self, request, model_admin):
        packages = ExcelData.objects.values_list('PACKAGE', flat=True).distinct()
        # Ensure that we only deal with non-None and non-empty strings for sorting
        non_empty_packages = [pkg for pkg in packages if pkg]

        # Sort packages considering various possible formats
        def sort_key(x):
            # Find all numbers in the string and sort primarily by the first number, then alphabetically
            numbers = re.findall(r'\d+', x)
            prefix = re.match(r'\D*', x).group()  # Extract non-digit prefix
            return (prefix, int(numbers[0]) if numbers else 0, x)

        sorted_packages = sorted(non_empty_packages, key=sort_key)

        return [(package, package) for package in sorted_packages if package]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(PACKAGE=self.value())

class ChecksFilter(admin.SimpleListFilter):
    title = _('check')
    parameter_name = 'check'

    def lookups(self, request, model_admin):
        # Assuming OperatorInput is used to determine num_L_packages and num_C_packages dynamically
        operator_inputs= OperatorInput.objects.all()
        num_L_packages = 0
        num_C_packages = 0
        for operator_input in operator_inputs:
            if operator_input.L_no > num_L_packages:
                num_L_packages = operator_input.L_no
            if operator_input.C_no > num_C_packages:
                num_C_packages = operator_input.C_no

        # Generate checks dynamically based on num_L_packages and num_C_packages
        checks = [f'L{i}' for i in range(1, num_L_packages + 1)] + [f'C{i}' for i in range(1, num_C_packages + 1)]
        return [(check, check) for check in checks]

    def queryset(self, request, queryset):
        operator_inputs= OperatorInput.objects.all()
        num_L_packages = 0
        num_C_packages = 0
        for operator_input in operator_inputs:
            if operator_input.L_no > num_L_packages:
                num_L_packages = operator_input.L_no
            if operator_input.C_no > num_C_packages:
                num_C_packages = operator_input.C_no
                
        if self.value():
            check_type, check_num = self.value()[0], int(self.value()[1:])
            q_objects = Q()

            if check_type == 'L':
                # For L checks, include only the check itself and its direct multiples
                for i in range(1, check_num + 1):
                    if check_num % i == 0 or i == check_num:  # Adjust this condition as needed
                        q_objects |= Q(PACKAGE=f'L{i}')
            elif check_type == 'C':
                # For C checks, include all L packages and the C check itself
                for i in range(1, num_L_packages + 1):
                    q_objects |= Q(PACKAGE=f'L{i}')
                for i in range(1, check_num + 1):
                    if check_num % i == 0:  # Include C checks based on divisibility
                        q_objects |= Q(PACKAGE=f'C{i}')

            return queryset.filter(q_objects)
        return queryset
    

