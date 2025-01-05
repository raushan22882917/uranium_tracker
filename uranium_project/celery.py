# uranium_project\uranium_project\celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uranium_project.settings')

app = Celery('uranium_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
