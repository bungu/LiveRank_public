# Generated by Django 3.2.5 on 2022-08-13 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LiveRank', '0009_rename_access_count_master_pv_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='YT_record',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('userid', models.CharField(max_length=50)),
                ('img', models.URLField()),
                ('name', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=20)),
                ('day', models.DateField()),
                ('superchat_record', models.IntegerField()),
                ('subscriber_record', models.IntegerField()),
            ],
        ),
        migrations.DeleteModel(
            name='Update',
        ),
    ]
