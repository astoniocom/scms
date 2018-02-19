# coding: utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models
from scms.widgets import ColorPickerWidget

from django import forms

# class PageDescriptionField(models.TextField):
#     def formfield(self, **kwargs):
#         kwargs['widget'] = forms.TextInput(attrs = {'style': 'width:90%;'})
#         return super(PageDescriptionField, self).formfield(**kwargs)    

class Parameter(models.Model):
    vocabulary = models.CharField("Слово в транслитирации", max_length=64, blank=False, null=False, db_index=True )
    name = models.CharField("Название", max_length=256, blank=False, null=False, db_index=True)
    measure = models.CharField("Измерение", max_length=256, blank=True, default="", db_index=False)
    language = models.CharField(_("Language"), max_length=5, blank=True, db_index=True)
    weight = models.IntegerField("Вес", blank=False, null=False, db_index=True)

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Параметры"
        ordering = ['weight', 'vocabulary', 'name']

    def __str__(self):
        return self.name

class Parameters(SCMSPluginModel):
    parameter = models.ForeignKey(Parameter, verbose_name="Параметр", blank=False, related_name='parameters', on_delete=models.CASCADE)
    value = models.CharField("Значение", max_length=256, blank=False, null=False, db_index=True )
    # weight = models.IntegerField("Вес", max_length=256, blank=False, null=False, db_index=True)

class ColorField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorPickerWidget
        return super(ColorField, self).formfield(**kwargs)

class Color(models.Model):
    name = models.CharField("Название цвета", max_length=64, blank=False, null=True, db_index=True )
    html = ColorField("HTML-предстовление", max_length=64, blank=False, null=True, db_index=False )
    
    class Meta:
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Colors(SCMSPluginModel):
    color = models.ForeignKey('Color', verbose_name="Цвет", blank=True, null=True, on_delete=models.CASCADE)
