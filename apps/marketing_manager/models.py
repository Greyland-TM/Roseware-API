from django.db import models
import datetime
from apps.accounts.models import Customer

class MarketingSchedule(models.Model):
    """ This object represent a Clients Monthly Marketing Schedule """

    start_date = models.DateField(default=datetime.date.today)
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.title}"

class WeeklyTopic(models.Model):
    """ Each MarketingSchedule object should have 4 WeeklyTopic objects """

    schedule = models.ForeignKey(MarketingSchedule, on_delete=models.CASCADE, related_name='marketing_schedule')
    week_start_date = models.DateField()
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=100)

    class Meta:
        unique_together = ['schedule', 'week_start_date']

    def __str__(self):
        return f"Week starting {self.week_start_date}: {self.topic}"


class DailyContent(models.Model):
    """ This model represents a single days content """

    CONTENT_TYPES = (
        ('social_media', 'Social Media'),
    )

    weekly_topic = models.ForeignKey(WeeklyTopic, on_delete=models.CASCADE, related_name="weekly_topic")
    daily_topic = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    content_type = models.CharField(max_length=100, choices=CONTENT_TYPES)
    scheduled_date = models.DateField()

    def __str__(self):
        return f"{self.title}"
