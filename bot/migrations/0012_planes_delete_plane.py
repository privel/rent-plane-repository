# Generated by Django 5.1.2 on 2024-11-07 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0011_plane_alter_profile_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Planes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_plane', models.CharField(default='Plane 1', max_length=255)),
                ('available', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Самолёт',
                'verbose_name_plural': 'Самолёты',
            },
        ),
        migrations.DeleteModel(
            name='Plane',
        ),
    ]
