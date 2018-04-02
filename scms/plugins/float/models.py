from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Float(SCMSPluginModel):
    data = models.FloatField(_("Float"), blank=True, null=True)
