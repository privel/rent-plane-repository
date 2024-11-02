# Generated by Django 5.1.2 on 2024-11-01 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.PositiveIntegerField(verbose_name='ID person in TG')),
                ('name', models.TextField(verbose_name='Name TG')),
            ],
            options={
                'verbose_name': 'TG Profile',
            },
        ),
    ]
