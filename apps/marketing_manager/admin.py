from django.contrib import admin

from .models import DailyContent, MarketingSchedule, WeeklyTopic, Day, CustomerSelectedPlatform, SocialPost

class DailyContentInline(admin.TabularInline):
    model = DailyContent
    extra = 1

class WeeklyTopicAdmin(admin.ModelAdmin):
    inlines = [DailyContentInline]

class WeeklyTopicInline(admin.TabularInline):
    model = WeeklyTopic
    extra = 1

class MarketingScheduleAdmin(admin.ModelAdmin):
    inlines = [WeeklyTopicInline]

admin.site.register(MarketingSchedule, MarketingScheduleAdmin)
admin.site.register(WeeklyTopic, WeeklyTopicAdmin)
admin.site.register(Day)
admin.site.register(CustomerSelectedPlatform)
admin.site.register(SocialPost)
