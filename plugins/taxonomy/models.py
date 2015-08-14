from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

class Taxonomy(SCMSPluginModel):
    terms = models.ManyToManyField('Terms')
    class Meta:
        verbose_name = _('Taxonomy')
        verbose_name_plural = _('Taxonomy')	

class Terms(models.Model):
    vocabulary = models.CharField(_("Vocabulary"), max_length=16, blank=False, db_index=True)
    name = models.CharField(_("Name"), max_length=64, blank=False, db_index=False)
    description = models.CharField(_("Description"), max_length=256, blank=True, db_index=False)
    language = models.CharField(_("Language"), max_length=5, blank=True, db_index=True)
    weight = models.IntegerField(_("Weight"), max_length=4, blank=True, db_index=True, default=0)

    class Meta:
        verbose_name = _('Term')
        verbose_name_plural = _('Terms')
        ordering = ['weight', 'name',]
    
    def __unicode__(self):
        return self.name


