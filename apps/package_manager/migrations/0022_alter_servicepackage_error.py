# Generated by Django 4.1.7 on 2023-03-26 22:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0021_servicepackage_pipedrive_product_attachment_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackage",
            name="error",
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]
