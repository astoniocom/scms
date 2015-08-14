from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Boolean(SCMSPluginModel):
    state = models.BooleanField(_("Boolean"), blank=True)