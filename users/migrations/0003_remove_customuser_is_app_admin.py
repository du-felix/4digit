# Generated by Django 4.2.19 on 2025-03-25 22:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_customuser_is_app_admin'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='is_app_admin',
        ),
    ]
