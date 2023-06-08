# Generated by Django 4.1.7 on 2023-02-25 02:31

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_customer_ayrshare_key_customer_ayrshare_ref_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="customer",
            old_name="start_date",
            new_name="onboarding_date",
        ),
        migrations.RemoveField(
            model_name="customer",
            name="ayrshare_key",
        ),
        migrations.RemoveField(
            model_name="customer",
            name="ayrshare_ref_id",
        ),
        migrations.AddField(
            model_name="customer",
            name="email",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AddField(
            model_name="customer",
            name="phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True, max_length=128, null=True, region=None
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="first_name",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="customer",
            name="last_name",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="marketer",
            name="first_name",
            field=models.CharField(default="Joe", max_length=100),
        ),
        migrations.AlterField(
            model_name="marketer",
            name="last_name",
            field=models.CharField(default="Dierte", max_length=100),
        ),
    ]
