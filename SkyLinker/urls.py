"""
URL configuration for SkyLinker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Home.urls')),
    path('about/', include('About.urls')),
    path('services/', include('Services.urls')),
    path('maintenance/', include('Maintenance.urls')),
    path('maintenance/operator/', include('Operator.urls')),
    path('maintenance/aircraftdata/', include('AircraftData.urls')),
    path('maintenance/amp/', include('AMP.urls')),
    path('maintenance/ldnd/', include('LDND.urls')),
    path('maintenance/upcomingtasks/', include('UpcomingTasks.urls')),
    path('airlineoperations/', include('AirlineOperations.urls')),
    path('airlineoperations/routing/', include('Routing.urls')),
    path('airlineoperations/itinerarybuilder/', include('ItineraryBuilder.urls')),
    path('airlineoperations/fleetassignment/', include('FleetAssignment.urls')),
    path('airlineoperations/marketshare/', include('MarketShare.urls')),
    path('i18n/', include('django.conf.urls.i18n')),  # Include language selection URLs

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
