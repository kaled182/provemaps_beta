from django.db import models


class CronJob(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    schedule    = models.CharField(max_length=100)   # cron expression: "0 3 * * 0"
    command     = models.TextField()
    enabled     = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name     = 'Cron Job'
        verbose_name_plural = 'Cron Jobs'

    def __str__(self):
        return self.name
