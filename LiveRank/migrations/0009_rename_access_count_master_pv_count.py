# Generated by Django 3.2.5 on 2022-07-21 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('LiveRank', '0008_master_access_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='master',
            old_name='access_count',
            new_name='pv_count',
        ),
    ]