from django.db import models
from datetime import datetime
from django.conf import settings

class OperatorInput(models.Model):
    Airline_Name = models.CharField(max_length=255, default='SkyLinker Airline', null=False, blank=False, verbose_name="Airline Name")
    FC_DY = models.FloatField(default=6.0, verbose_name="FC To DY Ratio")
    FH_DY = models.FloatField(default=15.0, verbose_name="FH to DY Ratio")
    Daily = models.FloatField(default=2.0, verbose_name="Daily Task Interval")
    Weekly = models.FloatField(default=7.0, verbose_name="Weekly Task Interval")
    Service_DY = models.FloatField(default=60.0, verbose_name="Service Task DY Interval")
    Service_FH = models.FloatField(default=500.0, verbose_name="Service Task FH Interval")
    Service_FC = models.FloatField(default=250.0, verbose_name="Service Task FC Interval")
    L_no = models.IntegerField(default=5, verbose_name="Number of L packages")
    L1_DY = models.FloatField(default=120.0, verbose_name="L1 Task DY Interval")
    L1_FH = models.FloatField(default=900.0, verbose_name="L1 Task FH Interval")
    L1_FC = models.FloatField(default=360.0, verbose_name="L1 Task FC Interval")
    C_no = models.IntegerField(default=10, verbose_name="Number of C packages")
    C1_YR = models.FloatField(default=2.0, verbose_name="C1 Tasks DY Interval")
    C1_FH = models.FloatField(default=6000.0, verbose_name="C1 Task FH Interval")
    C1_FC = models.FloatField(default=3000.0, verbose_name="C1 Task FC Interval")
    num_aircrafts = models.IntegerField(default=1, verbose_name="Number of Aircraft")  # New field
    
    def __str__(self):
        return self.Airline_Name

    class Meta:
        verbose_name = "Operator'"
    
class AircraftDetails(models.Model):
    Airline_Name = models.ForeignKey(OperatorInput, on_delete=models.CASCADE, verbose_name="Airline Name")
    aircraft_type = models.CharField(max_length=100, default="B737-700", verbose_name="Aircraft Type")
    aircraft_name = models.CharField(max_length=100, default='SU-AAA', verbose_name="Aircraft Name")
    production_date = models.DateField(default=datetime.now, verbose_name="Aircraft Production Date")
    ac_sn = models.CharField(max_length=255, default="00000", null=True, blank=True, verbose_name="Aircraft Serial Number")
    ac_ln = models.CharField(max_length=255, default="0000", null=True, blank=True, verbose_name="Aircraft Line Number")
    ac_bn = models.CharField(max_length=255, default="XY000", null=True, blank=True, verbose_name="Aircraft Block Number")
    
    def __str__(self):
        return self.aircraft_name
    
    class Meta:
        verbose_name = "Aircraft Detail"