from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Integer(SCMSPluginModel):
    data = models.IntegerField(_("Integer"), blank=True, null=True)
