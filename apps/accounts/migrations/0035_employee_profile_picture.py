# Generated by Django 4.2.4 on 2023-08-26 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0034_delete_blogarticle'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_picture/'),
        ),
    ]
