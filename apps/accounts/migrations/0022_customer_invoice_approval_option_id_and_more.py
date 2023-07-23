# Generated by Django 4.2.3 on 2023-07-23 00:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0021_customer_pipedrive_user_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="invoice_approval_option_id",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="one_time_option_id",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="process_immediately_option_id",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="subscription_option_id",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
    ]
