from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from infrastructure.scheduler import run_due_jobs


class Command(BaseCommand):
    help = (
        'Run every scheduled job that is due this hour (see infrastructure/scheduler/jobs/). '
        'Intended to run hourly, e.g. as a PythonAnywhere Scheduled Task.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--job',
            dest='job_ids',
            action='append',
            help='Run only this job id, regardless of whether it is due. Repeatable.',
        )

    def handle(self, *args, **options):
        try:
            results = run_due_jobs(job_ids=options.get('job_ids'))
        except ValueError as exc:
            raise CommandError(str(exc))

        for entry in results:
            status, job_id = entry['status'], entry['id']
            if status == 'ran':
                self.stdout.write(self.style.SUCCESS(f'  ran       {job_id}: {entry["result"]}'))
            elif status == 'error':
                self.stderr.write(self.style.ERROR(f'  error     {job_id}: {entry["result"]}'))
            elif status == 'misfired':
                self.stdout.write(self.style.WARNING(f'  misfired  {job_id} (too late to be useful)'))
            else:
                self.stdout.write(f'  skipped   {job_id}')

        counts = Counter(e['status'] for e in results)
        summary = (
            f'Ran {counts["ran"]} job(s), {counts["error"]} error(s), '
            f'{counts["misfired"]} misfire(s).'
        )
        self.stdout.write(self.style.ERROR(summary) if counts['error'] else self.style.SUCCESS(summary))
