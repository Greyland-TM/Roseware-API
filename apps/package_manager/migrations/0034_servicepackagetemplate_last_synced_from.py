# Generated by Django 4.2 on 2023-04-11 00:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0033_alter_servicepackagetemplate_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepackagetemplate",
            name="last_synced_from",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
    ]
