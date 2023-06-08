# Generated by Django 4.1.7 on 2023-03-12 04:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0008_servicepackage_requires_onboarding_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackage",
            name="last_completed",
            field=models.DateTimeField(
                blank=True, default=None, max_length=100, null=True
            ),
        ),
        migrations.AlterField(
            model_name="servicepackage",
            name="next_scheduled",
            field=models.DateTimeField(
                blank=True, default=None, max_length=100, null=True
            ),
        ),
    ]
