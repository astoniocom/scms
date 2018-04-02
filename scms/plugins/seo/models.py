from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class SEO(SCMSPluginModel):
    title = models.CharField(_("Title"), max_length=2048, blank=True, db_index=False, null=True)
    keywords = models.CharField(_("Keywords"), max_length=2048, blank=True, db_index=False, null=True)
    description = models.TextField(_("Description"), blank=True, db_index=False, null=True)