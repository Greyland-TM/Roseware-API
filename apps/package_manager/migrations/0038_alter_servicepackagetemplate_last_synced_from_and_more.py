# Generated by Django 4.2 on 2023-04-15 04:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0037_alter_servicepackagetemplate_pipedrive_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="last_synced_from",
            field=models.CharField(
                blank=True, default="roseware", max_length=100, null=True
            ),
        ),
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="original_sync_from",
            field=models.CharField(
                blank=True, default="roseware", max_length=100, null=True
            ),
        ),
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="related_app",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="type",
            field=models.CharField(default="", max_length=100),
        ),
    ]