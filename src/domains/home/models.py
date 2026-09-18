from django.db import models


class ErrorLog(models.Model):
    LEVEL_CHOICES = [
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, db_index=True)
    logger_name = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    traceback = models.TextField(blank=True)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'[{self.level}] {self.message[:80]}'


class ScheduledJobRun(models.Model):
    """Persisted next-run time for a job in infrastructure/scheduler/jobs/.

    The runner is invoked on an arbitrary, possibly irregular tick, so dueness cannot be a
    match against the current clock — it is `next_run_at <= now`, advanced after each run.
    """
    job_id = models.CharField(max_length=100, unique=True)
    next_run_at = models.DateTimeField(db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['job_id']

    def __str__(self):
        return f'{self.job_id} → {self.next_run_at:%Y-%m-%d %H:%M}'
