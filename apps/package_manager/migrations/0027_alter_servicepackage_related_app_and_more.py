# Generated by Django 4.1.7 on 2023-04-01 01:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("package_manager", "0026_servicepackage_quantity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicepackage",
            name="related_app",
            field=models.CharField(
                choices=[
                    ("Duda", "Duda"),
                    ("Markit", "Markit"),
                    ("Ayrshare", "Ayrshare"),
                ],
                default="",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="servicepackage",
            name="type",
            field=models.CharField(
                choices=[
                    ("Webpage", "Webpage"),
                    ("Social", "Social"),
                    ("Blog", "Blog"),
                    ("Ads", "Ads"),
                ],
                default="",
                max_length=100,
            ),
        ),
    ]
