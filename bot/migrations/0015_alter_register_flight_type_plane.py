# Generated by Django 5.1.2 on 2024-11-08 08:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0014_remove_register_flight_hobbs_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='register_flight',
            name='type_plane',
            field=models.ForeignKey(limit_choices_to={'available': True}, on_delete=django.db.models.deletion.PROTECT, to='bot.planes', verbose_name='Тип'),
        ),
    ]
