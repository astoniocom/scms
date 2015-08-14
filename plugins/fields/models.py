# coding=utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.conf import settings

class Fields(SCMSPluginModel):
    name = models.SlugField(_("Name"), blank=False, max_length=40, unique=True, help_text='Имя поля для идентификации. Должно быть уникальным, может содержать буквы и знак `_`')
    type = models.CharField(_("Type"), choices=settings.SCMS_PLUGINS, blank=False, max_length=70, help_text='Тип поля ввода') 
    verbose_name = models.CharField(_("Verbose name"), blank=False, db_index=False, max_length=80, help_text='Имя поля для отображения на формах создания и редактирования страниц')
    extra = models.IntegerField(_("Extra"), null= True, blank=True, db_index=False, max_length=1, help_text='Количество пустых полей предлагаемых для ввода.')
    can_order = models.BooleanField(_("Can order"), blank=True, default=True, help_text='Можно ли менять порязок зачений')
    lang_depended = models.BooleanField(_("Is language depended"), blank=True, default=True, help_text='Для каждого языка страницы необходимо указывать собственные значения поля, либо для всех языков страницы использовать одинаковые значения поля')
    can_delete = models.BooleanField(_("Is can delete"), blank=True, default=True, help_text='Можно ли удалять поля')
    max_num = models.IntegerField(_("Max fields"),  null= True,blank=True, db_index=False, max_length=2, help_text='Максимальное количество полей ввода')    
    ext_params = models.CharField(_("Extra params"), null= True, blank=True, max_length=256, unique=False, help_text='Дополнительные параметры настройки в формате `поле=значение,поле2=значение`. Возможные поля смотрите в документации')
    filter_type = models.IntegerField(_("Filter Type"), choices=((1, 'Тип %s'%1),(2, 'Тип %s'%2),), null= True, blank=True, default=None, max_length=2, help_text='Тип фильтра, при его использовании')	
    
    class Meta:
        ordering = ['weight', 'name',]