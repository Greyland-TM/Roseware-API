# Generated by Django 4.2.1 on 2023-06-16 00:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketing_manager", "0006_day"),
    ]

    operations = [
        migrations.AddField(
            model_name="day",
            name="index",
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]