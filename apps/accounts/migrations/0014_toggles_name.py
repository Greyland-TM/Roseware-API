# Generated by Django 4.2 on 2023-04-08 21:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="toggles",
            name="name",
            field=models.CharField(default="Toggles", max_length=100),
        ),
    ]
