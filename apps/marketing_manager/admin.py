from django.contrib import admin
from .models import MarketingSchedule, WeeklyTopic, DailyContent

class DailyContentInline(admin.TabularInline):
    model = DailyContent
    extra = 1

class WeeklyTopicInline(admin.TabularInline):
    model = WeeklyTopic
    extra = 1
    inlines = [DailyContentInline]

class MarketingScheduleAdmin(admin.ModelAdmin):
    inlines = [WeeklyTopicInline]

admin.site.register(MarketingSchedule, MarketingScheduleAdmin)
