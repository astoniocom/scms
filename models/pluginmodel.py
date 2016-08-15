# coding=utf-8
from django.db import models
from scms.models.pagemodel import Page
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
import scms

class SCMSPluginModel(models.Model):    
    page = models.ForeignKey(Page, verbose_name=_("page"), editable=False)
    language = models.CharField(_("language"), max_length=5, blank=False, db_index=True, editable=False)
    field_name = models.CharField(_("field name"), max_length=40, blank=False, db_index=True, editable=False)
    weight = models.IntegerField(_("Weight"), blank=False, db_index=True, default=0)
    
    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        #if (self.slug): непонятно, как определять родителя, да и надо ли. Да и как быть в ситуации перемещения...
        #    slug_copy = Slugs.objects.filter(slug=self.slug, language=self.language, page__parent=self.parent).exclude(page=self.page)
        #    if slug_copy.count():
        #        raise ValueError, u"Дублирование поля Slug"
        
        cache.delete('page_%s_%s' % (self.page.id, self.language))
        
        return super(SCMSPluginModel, self).save(force_insert, force_update, using, update_fields) 
    
    def __unicode__(self):
        for field in scms.site.get_content_type(self.page.type).get_fields():
            if self.field_name == field.name:
                return field.name
        return u''
