from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GenAIwithDjangoRestApi.settings')

app = Celery('GenAIwithDjangoRestApi',broker_connection_retry_on_startup=True,worker_send_task_events = True,broker='amqp://guesthome:yesyoucan2025@rabbitmq:5672//')
app.config_from_object(settings, namespace='CELERY')

app.conf.beat_schedule = {}

app.autodiscover_tasks()