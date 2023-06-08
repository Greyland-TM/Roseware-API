# Generated by Django 4.2 on 2023-04-05 01:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0029_packageplan_stripe_subscription_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackage",
            name="action",
            field=models.CharField(default="create", max_length=100),
        ),
        migrations.AlterField(
            model_name="servicepackage",
            name="related_app",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="servicepackage",
            name="type",
            field=models.CharField(default="", max_length=100),
        ),
    ]
