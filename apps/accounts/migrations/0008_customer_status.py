# Generated by Django 4.1.7 on 2023-03-11 06:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_customer_monday_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="status",
            field=models.CharField(
                choices=[("lead", "Lead"), ("customer", "Customer")],
                default="lead",
                max_length=100,
            ),
        ),
    ]
