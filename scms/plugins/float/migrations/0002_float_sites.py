# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-31 12:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('float', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='float',
            name='sites',
            field=models.ManyToManyField(to='sites.Site'),
        ),
    ]