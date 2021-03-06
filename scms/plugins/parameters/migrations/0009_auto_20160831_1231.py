# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-31 12:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('parameters', '0008_auto_20160803_1440'),
    ]

    operations = [
        migrations.AddField(
            model_name='colors',
            name='sites',
            field=models.ManyToManyField(to='sites.Site'),
        ),
        migrations.AddField(
            model_name='parameters',
            name='sites',
            field=models.ManyToManyField(to='sites.Site'),
        ),
    ]
