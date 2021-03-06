# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-25 10:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scms', '__first__'),
        ('parameters', '0002_auto_20160725_0959'),
    ]

    operations = [
        migrations.CreateModel(
            name='ColorPlugin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_index=True, editable=False, max_length=5, verbose_name='language')),
                ('field_name', models.CharField(db_index=True, editable=False, max_length=40, verbose_name='field name')),
                ('weight', models.IntegerField(db_index=True, default=0, verbose_name='Weight')),
                ('color', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parameters.Color', verbose_name=b'\xd0\xa6\xd0\xb2\xd0\xb5\xd1\x82')),
                ('page', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='scms.Page', verbose_name='page')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
