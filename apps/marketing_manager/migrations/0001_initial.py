# Generated by Django 4.2.5 on 2023-10-05 06:26

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketingSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(default=datetime.date.today)),
                ('topic', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('customer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
            ],
        ),
        migrations.CreateModel(
            name='SocialPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(max_length=100)),
                ('date_posted', models.DateField(blank=True, null=True)),
                ('caption', models.CharField(max_length=100)),
                ('image_url', models.ImageField(blank=True, null=True, upload_to='social_media_posts')),
            ],
        ),
        migrations.CreateModel(
            name='WeeklyTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start_date', models.DateField()),
                ('topic', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('index', models.IntegerField()),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_schedule', to='marketing_manager.marketingschedule')),
            ],
            options={
                'unique_together': {('schedule', 'week_start_date')},
            },
        ),
        migrations.CreateModel(
            name='Day',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, unique=True)),
                ('index', models.IntegerField()),
                ('customer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
            ],
        ),
        migrations.CreateModel(
            name='DailyContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('daily_topic', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('index', models.IntegerField()),
                ('content_type', models.CharField(choices=[('social_media', 'Social Media')], max_length=100)),
                ('scheduled_date', models.DateField()),
                ('weekly_topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_topic', to='marketing_manager.weeklytopic')),
            ],
        ),
        migrations.CreateModel(
            name='CustomerSelectedPlatform',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, unique=True)),
                ('customer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
            ],
        ),
        migrations.CreateModel(
            name='BlogArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='', max_length=100)),
                ('description', models.CharField(default='', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('image', models.ImageField(upload_to='blog_images/')),
                ('category', models.CharField(choices=[('news', 'News'), ('updates', 'Updates'), ('events', 'Events'), ('marketing', 'Marketing')], default='', max_length=100)),
                ('body', models.TextField(default='')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='author', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
