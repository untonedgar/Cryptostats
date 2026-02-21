from django.core.management.base import BaseCommand
from balance.tasks.tasks import process_all_users_snapshots


class Command(BaseCommand):
    help = 'Запускает снапшоты для всех пользователей'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, default='daily', choices=['daily', 'monthly'])

    def handle(self, *args, **options):
        snapshot_type = options['type']
        self.stdout.write(f"🚀 Запуск {snapshot_type} снапшотов...")

        task = process_all_users_snapshots.delay(snapshot_type)

        self.stdout.write(self.style.SUCCESS(f"✅ Задача запущена: {task.id}"))