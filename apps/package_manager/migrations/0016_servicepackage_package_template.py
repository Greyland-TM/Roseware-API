# Generated by Django 4.1.7 on 2023-03-23 04:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        (
            "package_manager",
            "0015_rename_pipedrive_product_code_servicepackagetemplate_pipedrive_id",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepackage",
            name="package_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="package_manager.servicepackagetemplate",
            ),
        ),
    ]