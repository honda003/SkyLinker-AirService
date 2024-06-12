from django.db import models
from datetime import datetime
from Operator.models import AircraftDetails, OperatorInput

class AircraftData(models.Model):
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Airline Name")
    Aircraft_Name = models.ForeignKey(AircraftDetails, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Aircraft Name")
    current_date = models.DateField(default=datetime.now, verbose_name="Data Entry Date")
    current_flight_hours = models.CharField(max_length=255, default='40000:00', null=True, blank=True, verbose_name="Current Total Flight Hours")  # HH:MM format
    current_flight_cycles = models.IntegerField(null=True, default=15000, blank=True, verbose_name="Current Total Flight Cycles")
    apu_hours_to_flight_hours_ratio = models.FloatField(default=0.3, null=True, blank=True, verbose_name="APU FH To AC Fh Ratio")
    apu_sn = models.CharField(max_length=255,null=True, default='X0000', blank=True, verbose_name="APU Serial Number")
    apu_fh = models.CharField(max_length=255,null=True, default='25000:00', blank=True, verbose_name="APU Flight Hours")  # HH:MM format
    apu_fc = models.IntegerField(null=True, blank=True, default=17000, verbose_name="APU Flight Cycles")
    num_engs = models.IntegerField(default=1, verbose_name="Number of Engines")


    def get_flight_hours_as_float(self):
        hours, minutes = self.current_flight_hours.split(':')
        return float(hours) + float(minutes) / 60

    def __str__(self):
        return f"{self.Aircraft_Name}"
    
    class Meta:
        verbose_name = "Aircraft'"
        
class EngineDetails(models.Model):
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Airline Name")
    Aircraft_Name = models.ForeignKey(AircraftData, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Aircraft Name")
    eng_sn = models.CharField(max_length=100, default='000000', verbose_name="Engine Serial Number")
    eng_fh = models.CharField(max_length=255, default='40000:00', null=True, blank=True, verbose_name="Engine Flight Hours")  # HH:MM format
    eng_fc = models.IntegerField(null=True, default=18000, blank=True, verbose_name="Engine Flight Cycles")

    class Meta:
        verbose_name = "Engines Detail"