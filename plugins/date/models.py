# coding: utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Date(SCMSPluginModel):
    date = models.DateField("Дата")
