from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class TextArea(SCMSPluginModel):
    body = models.TextField(_("Text"))
