# Generated by Django 4.2 on 2023-04-06 03:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_customer_stripe_customer_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="OngoingSync",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("type", models.CharField(default="", max_length=100)),
                ("stop_pipedrive_webhook", models.BooleanField(default=False)),
                ("has_recieved_pipedrive_webhook", models.BooleanField(default=False)),
                ("stop_stripe_webhook", models.BooleanField(default=False)),
                ("has_recieved_stripe_webhook", models.BooleanField(default=False)),
            ],
        ),
    ]
