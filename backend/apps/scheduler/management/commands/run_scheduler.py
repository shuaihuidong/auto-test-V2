import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scheduler.services import run_due_scheduled_tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the plan scheduler loop.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Polling interval in seconds.',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run one scheduler tick and exit.',
        )

    def handle(self, *args, **options):
        interval = max(5, int(options['interval']))
        once = bool(options['once'])

        self.stdout.write(self.style.SUCCESS(f'Scheduler started (interval={interval}s).'))

        while True:
            started_at = timezone.now()
            try:
                dispatched = run_due_scheduled_tasks(now=started_at)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[{started_at:%Y-%m-%d %H:%M:%S}] dispatched {dispatched} due task(s).'
                    )
                )
            except Exception as exc:
                logger.exception('Scheduler loop failed')
                self.stderr.write(self.style.ERROR(f'Scheduler loop failed: {exc}'))

            if once:
                break

            time.sleep(interval)
