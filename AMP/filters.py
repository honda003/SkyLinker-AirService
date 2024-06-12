import django_filters
from django import forms
from .models import ExcelData

# def get_unique_checks():
#     unique_checks = set()
#     for data in ExcelData.objects.all():
#         if data.Checks:
#             checks_list = data.Checks.split(',')
#             unique_checks.update(checks_list)
    
#     # Separate "L" and "C" checks
#     l_checks = sorted([check for check in unique_checks if check.startswith('L')], key=lambda x: (x[0], int(x[1:])))
#     c_checks = sorted([check for check in unique_checks if check.startswith('C')], key=lambda x: (x[0], int(x[1:])))
    
#     # Combine "L" and "C" checks, maintaining the desired order
#     sorted_checks = l_checks + c_checks
    
#     # Pair each check for the choices format
#     return [(check, check) for check in sorted_checks]

# def safe_int_cast(s):
#     """Attempt to cast a string to int, return the original string if it fails."""
#     try:
#         return int(s)
#     except ValueError:
#         return s

# def package_sort_key(pkg):
#     """Custom sort key for handling mixed-format package names."""
#     prefix = pkg[0]
#     suffix = pkg[1:]

#     # Attempt to split suffix on non-numeric characters, if any, and cast the first part to int.
#     # This handles cases like 'C6/C5', extracting '6' for numeric sorting.
#     first_numeric_part = safe_int_cast(''.join(filter(str.isdigit, suffix)))

#     return (prefix, first_numeric_part, suffix)


# def get_unique_packages():
#     unique_packages = set(ExcelData.objects.values_list('Package', flat=True).distinct())

#     l_packages = sorted([pkg for pkg in unique_packages if pkg.startswith('L')], key=package_sort_key)
#     c_packages = sorted([pkg for pkg in unique_packages if pkg.startswith('C')], key=package_sort_key)
#     other_packages = sorted([pkg for pkg in unique_packages if not pkg.startswith('L') and not pkg.startswith('C')])

#     sorted_packages = l_packages + c_packages + other_packages
#     return [(pkg, pkg) for pkg in sorted_packages]


# class AmpFilter(django_filters.FilterSet):
    
#     task_card_number_search = django_filters.CharFilter(
#         method='filter_task_card_number',
#         label='Task Card Number'
#     )
    
#     Checks = django_filters.ChoiceFilter(
#         choices=get_unique_checks,
#         method='filter_checks_by_choice',
#         label='Checks',
#     )
    
#     #Applicability_APL = django_filters.ChoiceFilter(
#         #field_name='Applicability_APL',
#         #choices=lambda: ExcelData.objects.values_list('Applicability_APL', 'Applicability_APL').distinct(),
#         #label='Applicability APL',
#         #lookup_expr='iexact'  # Perform case-insensitive comparison
#     #)

#     Package = django_filters.ChoiceFilter(
#         choices=get_unique_packages,
#         method='filter_packages_by_choice',
#         label='Packages',
#     )

#     Type = django_filters.ChoiceFilter(
#         field_name='Type',
#         choices=lambda: ExcelData.objects.values_list('Type', 'Type').distinct(),
#         label='Type',
#         lookup_expr='iexact'  # Perform case-insensitive comparison
#     )

#     def filter_task_card_number(self, queryset, name, value):
#         """
#         This method filters the queryset based on whether any part of the Task_Card_Number field
#         matches the search query using a regular expression to account for complex formats.
#         """
#         # Construct a regex pattern to match the task card number format within the field
#         # Adjust the pattern as needed to match the specific formatting and separation of your task card numbers
#         regex_pattern = r"\b{}\b".format(value.replace('-', '\-'))
#         return queryset.filter(Task_Card_Number__regex=regex_pattern)
    
#     def filter_checks_by_choice(self, queryset, name, value):
#         if value in ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10', 'L11', 'L12', 'L13', 'L14', 'L15', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10']:  # Add all standard "L" and "C" checks here
#             regex_pattern = r"\b{}\b".format(value)
#             return queryset.filter(Checks__regex=regex_pattern)
#         else:
#             # For non-standard values like "OutOfPhase", use a different approach
#             return queryset.filter(Checks__icontains=value)
        
    
#     def filter_packages_by_choice(self, queryset, name, value):
#         # Ensure we're filtering on the 'Package' field for package-related queries
#         if value in ['L1', 'L2', 'L3', 'L4', 'L5', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10']:  # Standard "L" and "C" packages
#             regex_pattern = r"\b{}\b".format(value)
#             return queryset.filter(Package__regex=regex_pattern)
#         else:
#             # For non-standard values like "OutOfPhase", properly target the 'Package' field
#             return queryset.filter(Package__icontains=value)

#     class Meta:
#         model = ExcelData
#         fields = ['MPD_Item_Number', 'Package', 'Type', 'Checks']