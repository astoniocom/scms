from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Text(SCMSPluginModel):
    body = models.CharField(_("Text"), max_length=2048, blank=True)
