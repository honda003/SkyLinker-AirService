from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import LastDone
import logging
from .models import LastDone, ChangeLog

# Get an instance of a logger
logger = logging.getLogger(__name__)

