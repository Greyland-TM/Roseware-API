# Generated by Django 4.1.7 on 2023-03-23 02:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0013_servicepackagetemplate_pipedrive_product_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepackagetemplate",
            name="name",
            field=models.CharField(default="", max_length=100),
        ),
    ]
