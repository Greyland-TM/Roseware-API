# Generated by Django 4.2 on 2023-04-06 04:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_ongoingsync"),
    ]

    operations = [
        migrations.AddField(
            model_name="ongoingsync",
            name="action",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AddField(
            model_name="ongoingsync",
            name="customer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="accounts.customer",
            ),
        ),
    ]
