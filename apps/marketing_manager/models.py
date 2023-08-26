from django.contrib.auth.models import User
from django.db import models
import datetime

class Day(models.Model):
    """ 
    This represents a day of the week, for a customers day selections.
    I want to add 
    """

    name = models.CharField(max_length=20, unique=True)
    index = models.IntegerField()
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name
    
class CustomerSelectedPlatform(models.Model):
    """ This represents a social media platform, for a customers platform selections """

    name = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

class MarketingSchedule(models.Model):
    """ This object represent a Clients Monthly Marketing Schedule """
    
    # Imports
    from apps.accounts.models import Customer

    # Fields
    start_date = models.DateField(default=datetime.date.today)
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.title}"

class WeeklyTopic(models.Model):
    """ Each MarketingSchedule object should have 4 WeeklyTopic objects """

    schedule = models.ForeignKey(MarketingSchedule, on_delete=models.CASCADE, related_name='marketing_schedule')
    week_start_date = models.DateField()
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    index = models.IntegerField()

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
    index = models.IntegerField()
    content_type = models.CharField(max_length=100, choices=CONTENT_TYPES)
    scheduled_date = models.DateField()

    def __str__(self):
        return f"{self.title}"

class SocialPost(models.Model):
    """ This model represents a single social media post """

    platform = models.CharField(max_length=100)
    date_posted = models.DateField(null=True, blank=True)
    caption = models.CharField(max_length=100)
    image_url = models.ImageField(upload_to='social_media_posts', null=True, blank=True)

    def __str__(self):
        return f"{self.platform}"

class BlogArticle(models.Model):
    CATEGORY_CHOICES = (
        ('news', 'News'),
        ('updates', 'Updates'),
        ('events', 'Events'),
        ('marketing', 'Marketing'),
    )

    title = models.CharField(default="", max_length=100, null=False, blank=False)
    description = models.CharField(default="", max_length=100, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    image = models.ImageField(upload_to='blog_images/', null=False, blank=False)
    category = models.CharField(default="", max_length=100, null=False, blank=False, choices=CATEGORY_CHOICES)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="author", null=True, blank=True)
    body = models.TextField(default="", null=False, blank=False)