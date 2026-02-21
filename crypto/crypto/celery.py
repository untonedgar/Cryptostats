import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto.settings')

app = Celery('crypto')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Ежедневные снапшоты в 00:30
    'daily-snapshots': {
        'task': 'balance.tasks.process_all_users_snapshots',
        'schedule': crontab(hour=0, minute=30),
        'args': ('daily',)
    },

    # Ежемесячные снапшоты 1-го числа в 01:00
    'monthly-snapshots': {
        'task': 'balance.tasks.process_all_users_snapshots',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),
        'args': ('monthly',)
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
