# Generated by Django 4.2.2 on 2023-06-24 08:23

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketing_manager", "0013_alter_socialpost_date_posted"),
    ]

    operations = [
        migrations.RenameField(
            model_name="socialpost",
            old_name="image",
            new_name="image_url",
        ),
    ]