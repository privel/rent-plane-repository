# Generated by Django 5.1.2 on 2024-11-05 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0008_rent_type_plane'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rent',
            name='dateEnd',
            field=models.DateField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rent',
            name='dateStart',
            field=models.DateField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rent',
            name='timeEnd',
            field=models.TimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rent',
            name='timeStart',
            field=models.TimeField(default=None, null=True),
        ),
    ]
