# Generated by Django 4.1.7 on 2023-03-23 01:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0011_servicepackagetemplate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="error",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
    ]
