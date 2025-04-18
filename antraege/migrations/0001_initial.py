# Generated by Django 4.2.19 on 2025-04-10 17:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Anfrage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('unterricht', models.TextField()),
                ('gm', models.EmailField(blank=True, max_length=254, null=True)),
                ('im', models.EmailField(blank=True, max_length=254, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('response', models.CharField(choices=[('not_responded', 'Noch nicht geantwortet'), ('accepted', 'Genehmigt'), ('declined', 'Abgelehnt')], default='not_responded', max_length=100)),
                ('reason', models.TextField(blank=True, null=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('is_principle', models.BooleanField(blank=True, default=False)),
                ('token', models.CharField(blank=True, max_length=64, null=True, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Antrag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titel', models.CharField(max_length=50)),
                ('grund', models.TextField()),
                ('klasse', models.CharField(choices=[('7', '7'), ('8', '8'), ('9a', '9a'), ('9b', '9b'), ('9c', '9c'), ('10a', '10a'), ('10b', '10b'), ('10c', '10c'), ('11', '11'), ('12', '12')], max_length=3)),
                ('erstellt_am', models.DateTimeField(auto_now_add=True)),
                ('anfangsdatum', models.DateField()),
                ('enddatum', models.DateField()),
                ('status', models.CharField(choices=[('in_progress', 'In Progress'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='in_progress', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Fach',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('kuerzel', models.CharField(max_length=10, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Lehrer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Zaehler',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zaehler', models.IntegerField(default=0)),
                ('temp', models.IntegerField(default=0)),
                ('fach', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='antraege.fach')),
                ('lehrer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='antraege.lehrer')),
            ],
        ),
    ]
