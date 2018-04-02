from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Links(SCMSPluginModel):
    name = models.CharField(_("Name"), max_length=200, blank=True, null=True)
    link = models.URLField(_("URL"), blank=True, null=True) # removed verify_exists=False, 
    description = models.CharField(_("Description"), max_length=400, blank=True, null=True)
