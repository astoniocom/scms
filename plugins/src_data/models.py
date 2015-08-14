from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class SrcData(SCMSPluginModel):
    is_blocked = models.BooleanField("Is blocked", blank=True)
    relpage = models.IntegerField("Page", blank=True, null=True )
