# Generated by Django 4.2 on 2023-04-11 00:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0032_servicepackagetemplate_description"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackagetemplate",
            name="description",
            field=models.CharField(default="", max_length=100),
        ),
    ]
