# Generated by Django 4.1.7 on 2023-03-30 02:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0010_customer_stripe_customer_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentDetails",
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
                ("type", models.CharField(max_length=255)),
                ("card_number", models.CharField(max_length=255)),
                ("expiry_date", models.CharField(max_length=255)),
                ("cvv", models.CharField(max_length=255)),
                ("card_holder_name", models.CharField(max_length=255)),
                (
                    "card_holder_email",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_phone",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_address",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_city",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_state",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_zip",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "card_holder_country",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "stripe_card_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.customer",
                    ),
                ),
            ],
        ),
    ]