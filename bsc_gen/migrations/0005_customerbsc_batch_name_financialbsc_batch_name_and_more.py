# Generated by Django 4.2.1 on 2025-07-13 06:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bsc_gen', '0004_learninggrowthbsc_internalbsc_financialbsc_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerbsc',
            name='batch_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='financialbsc',
            name='batch_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='internalbsc',
            name='batch_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='learninggrowthbsc',
            name='batch_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
