# coding: utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models

from django import forms

class PageDescriptionField(models.TextField):
    def formfield(self, **kwargs):
        kwargs['widget'] = forms.TextInput(attrs = {'style': 'width:90%;'})
        return super(PageDescriptionField, self).formfield(**kwargs)    

class PageSelect(SCMSPluginModel):
    relpage = models.ForeignKey('scms.Page', verbose_name="Страница", blank=False, related_name='relpage', on_delete=models.CASCADE)
    description = PageDescriptionField(_("Description"), max_length=200, blank=True, null=True)
