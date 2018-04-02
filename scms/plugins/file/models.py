# coding: utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models
from filebrowser.fields import FileBrowseField 
from django import forms

class FileDescriptionField(models.TextField):
    def formfield(self, **kwargs):
        kwargs['widget'] = forms.TextInput(attrs = {'style': 'width:90%;'})
        return super(FileDescriptionField, self).formfield(**kwargs)    

class File(SCMSPluginModel):
    file = FileBrowseField(_("File"), max_length=200, blank=True, null=True) 
    description = FileDescriptionField(_("Description"), max_length=200, blank=True, null=True)
    