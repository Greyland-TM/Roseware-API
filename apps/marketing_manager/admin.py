from django.contrib import admin

from .models import DailyContent, MarketingSchedule, WeeklyTopic, Day, CustomerSelectedPlatform, SocialPost, BlogArticle

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

class BlogArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author_email", "created_at", "category")
    
    def author_email(self, obj):
        if obj.author:
            return obj.author.email
        else:
            return ""
    
    author_email.short_description = "Author"

admin.site.register(MarketingSchedule, MarketingScheduleAdmin)
admin.site.register(WeeklyTopic, WeeklyTopicAdmin)
admin.site.register(Day)
admin.site.register(CustomerSelectedPlatform)
admin.site.register(SocialPost)
admin.site.register(BlogArticle, BlogArticleAdmin)
