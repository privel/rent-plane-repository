# Generated by Django 5.1.2 on 2024-11-02 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_alter_profile_options_alter_profile_external_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rent',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Time of create '),
        ),
    ]
