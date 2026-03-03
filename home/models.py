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
