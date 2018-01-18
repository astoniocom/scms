# coding=utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.conf import settings
from tinymce import models as tinymce_models

class PVParams(models.Model):
    name = models.CharField(_("Name"), max_length=64, blank=False, db_index=False)
    description = tinymce_models.HTMLField(_("Description"), blank=True, null=True)
    language = models.CharField(_("Language"), max_length=5, blank=True, db_index=True)

    class Meta:
        verbose_name = _('Parameter')
        verbose_name_plural = _('Parameters')
        ordering = ['name',]
    
    def __str__(self):
        return self.name




class ParamValue(SCMSPluginModel):
    param = models.ForeignKey('PVParams', verbose_name=_("Parameter") )
    value = models.CharField(_("Value"), max_length=254, blank=False, db_index=False)
