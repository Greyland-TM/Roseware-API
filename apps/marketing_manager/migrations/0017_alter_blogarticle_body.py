# Generated by Django 4.2.4 on 2023-08-26 05:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing_manager', '0016_remove_blogarticle_auther_blogarticle_author'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogarticle',
            name='body',
            field=models.TextField(default=''),
        ),
    ]
