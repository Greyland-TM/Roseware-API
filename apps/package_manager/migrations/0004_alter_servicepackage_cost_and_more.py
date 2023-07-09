# Generated by Django 4.1.7 on 2023-02-27 00:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0003_alter_servicepackage_action_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackage",
            name="cost",
            field=models.DecimalField(decimal_places=2, max_digits=6),
        ),
        migrations.AlterField(
            model_name="servicepackage",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]