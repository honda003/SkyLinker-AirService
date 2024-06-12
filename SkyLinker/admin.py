from django.contrib import admin
from django.conf import settings

class CustomAdminSite(admin.AdminSite):
    site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Skylinker administration')
    site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'Skylinker administration')
    index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Skylinker administration')

custom_admin_site = CustomAdminSite(name='customadmin')