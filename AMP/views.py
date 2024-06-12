from django.shortcuts import render, redirect
from .models import ExcelData
from Operator.models import OperatorInput, AircraftDetails 
from .forms import ExcelDataForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import json
import re
from urllib.parse import urlencode, parse_qs
from django.http import QueryDict
from django.urls import reverse
from django.contrib.auth.decorators import login_required

def extract_unique_keys_from_dynamic_applicability():
    unique_keys = set()
    for entry in ExcelData.objects.only('dynamic_applicability'):
        if entry.dynamic_applicability:
            unique_keys.update(entry.dynamic_applicability.keys())
    return sorted(list(unique_keys))


def natural_sort_key(s):
    """Provides a natural sort key function for sorting strings that contain numbers."""
    if s is None:
        return []
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]


def get_checks_options():
    operator_inputs= OperatorInput.objects.all()
    num_L_packages = 0
    num_C_packages = 0
    for operator_input in operator_inputs:
        if operator_input.L_no > num_L_packages:
            num_L_packages = operator_input.L_no
        if operator_input.C_no > num_C_packages:
            num_C_packages = operator_input.C_no

    # Generate and sort L and C checks based on num_L_packages and num_C_packages
    checks = []
    for i in range(1, num_L_packages + 1):
        checks.append(f'L{i}')
    for i in range(1, num_C_packages + 1):
        checks.append(f'C{i}')
    
    # Now, we sort the list of checks alphabetically and then numerically
    sorted_checks = sorted(checks, key=lambda check: (check[0], int(check[1:])))
    return sorted_checks


def apply_check_filter(queryset, check_filter):
    if check_filter:
        check_type = check_filter[0]
        check_num = int(check_filter[1:])
        q_objects = Q()

        if check_type == 'L':
            # Include the L check and any L checks where the number is a factor of the selected L check
            for i in range(1, check_num + 1):
                if check_num % i == 0:
                    regex_pattern = fr'^L{i}$'  # Exact match at the end
                    q_objects |= Q(PACKAGE__regex=regex_pattern)
        
        elif check_type == 'C':
            operator_inputs= OperatorInput.objects.all()
            num_L_packages = 0
            num_C_packages = 0
            for operator_input in operator_inputs:
                if operator_input.L_no > num_L_packages:
                    num_L_packages = operator_input.L_no
                if operator_input.C_no > num_C_packages:
                    num_C_packages = operator_input.C_no
                    
            # Include all L checks
            for i in range(1, num_L_packages + 1):
                q_objects |= Q(PACKAGE__regex=fr'^L{i}$')  # Exact match for L packages

            # Include the C check and any C checks where the number is a factor of the selected C check
            for i in range(1, check_num + 1):
                if check_num % i == 0:
                    regex_pattern = fr'^C{i}$'  # Exact match at the end
                    q_objects |= Q(PACKAGE__regex=regex_pattern)

        queryset = queryset.filter(q_objects)
    return queryset

@login_required
def excel_data_view(request): 
    queryset = ExcelData.objects.all().prefetch_related('Aircraft_Name')
    query = request.GET.get('q', '')
    
    columns = {
        'Airline_Name': 'Airline Name',
        'Aircraft_Name': 'Aircraft Name',
        'MPD_ITEM_NUMBER': 'MPD Item Number',
        'TASK_CARD_NUMBER': 'TASK CARD NUMBER',
        'THRES': 'THRES',
        'REPEAT': 'REPEAT',
        'ZONE': 'ZONE',
        'ACCESS': 'ACCESS',
        'APL': 'APL',
        'ENG': 'ENG',
        'ACESS_HOURS': 'ACESS HOURS',
        'MAN_HOURS': 'MAN HOURS',
        'TOTAL_HOURS': 'TOTAL HOURS',
        'TASK_DESCREPTION': 'TASK DESCREPTION',
        'TASK_TYPE': 'TASK TYPE',
        'TASK_TITLE': 'TASK TITLE',
        'PROGRAM': 'PROGRAM',
        'AREA': 'AREA',
        'PACKAGE': 'PACKAGE',
        'REMARKS': 'REMARKS',
        'CHECK': 'CHECK',
        'Dynamic_Applicability': 'dynamic_applicability',
    }
    
    # Sorting
    sort = request.GET.get('sort', '')
    sort_dir = request.GET.get('dir', 'asc')  # Default direction is ascending

    if sort:  # Check if sort parameter exists
        if sort_dir == 'desc':  # Toggle sort direction
            sort = f'-{sort}'
        queryset = queryset.order_by(sort)

    # MPD_ITEM_NUMBER and TASK_CARD_NUMBER search filter
    if query:
        queryset = queryset.filter(Q(MPD_ITEM_NUMBER__icontains=query) | Q(TASK_CARD_NUMBER__icontains=query))

    # Package filter
    package_filter = request.GET.get('package', '')
    if package_filter:
        queryset = queryset.filter(PACKAGE=package_filter)
        
    # Check filter - apply the divisibility-based filter
    check_filter = request.GET.get('check', '')
    if check_filter:
        queryset = apply_check_filter(queryset, check_filter)
        
    # Dynamic applicability filters
    dynamic_applicability_keys = extract_unique_keys_from_dynamic_applicability()

    # Filter the queryset manually because of database backend limitations
    if dynamic_applicability_keys:
        filtered_queryset = []
        for item in queryset:
            include_item = True
            for key in dynamic_applicability_keys:
                filter_value = request.GET.get(key, '')
                if filter_value:
                    item_value = item.dynamic_applicability.get(key, 'N')
                    if (filter_value == 'Y' and item_value != 'Y') or (filter_value == 'N' and item_value == 'Y'):
                        include_item = False
                        break
            if include_item:
                filtered_queryset.append(item)
        queryset = filtered_queryset
        
        
    # Prepare the base query string without 'page' parameter
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    base_query_string = query_params.urlencode()

    # Pagination
    paginator = Paginator(queryset, 50)  # Display 50 items per page
    page = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        
    # Retrieve and sort package options
    package_options = sorted(ExcelData.objects.values_list('PACKAGE', flat=True).distinct(), key=natural_sort_key)
    check_options = get_checks_options()

    # Updating the context
    dynamic_filters = {key: request.GET.get(key, '') for key in dynamic_applicability_keys}
    
    # Airline Names for filtering dropdown
    airline_names = OperatorInput.objects.order_by('Airline_Name').values_list('Airline_Name', flat=True).distinct()
    
    # Aircraft Names for filtering dropdown
    aircraft_names = AircraftDetails.objects.order_by('aircraft_name').values_list('aircraft_name', flat=True).distinct()


    context = {
        'query': query,
        'airline_names': airline_names,
        'aircraft_names': aircraft_names,
        'package_options': package_options,
        'check_options': check_options,
        'dynamic_filters': dynamic_filters,
        'dynamic_applicability_keys': dynamic_applicability_keys,
        'page_obj': page_obj,
        'base_query_string': base_query_string,
        'sort': sort,
        'sort_dir': sort_dir,
        'columns': columns,
    }

    return render(request, 'pages/amp.html', context)
