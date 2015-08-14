# coding=utf-8
from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from django.db import models
from datetime import datetime
from scms.models import Page

class ContactForm(SCMSPluginModel):
    name = models.CharField(_("Verbose name"), blank=False, db_index=False, max_length=80, help_text='Имя поля. Например: "Телефон", "E-mail"')
    type = models.CharField(_("Type"), choices=(('text_field', 'Текстовая строка'), ('text_area', 'Многострочный текст'), ('email', 'E-mail-адрес'), ), blank=False, max_length=70, help_text='Тип поля ввода') 
    required = models.BooleanField(_("Required"), blank=True, default=False, help_text='Является ли поле обязательным')

    
class ContactFormHistory(models.Model):
    page = models.ForeignKey(Page, blank=False, db_index=True)
    alias = models.CharField(_("Sent from page"), max_length=512, blank=True, null=True, db_index=False)
    date = models.DateTimeField(_("Date"), default=datetime.now)
    recipient = models.EmailField(_("E-mail Recipient"))
    body = models.TextField(_("Text"))
    type = models.IntegerField(_("Type"), max_length=1, blank=False, db_index=True, default=0)
    
    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ('-date',)
    
    def __unicode__(self):
        return self.body[:84]
    
    def _get_BODY_display(self, field):
        return 'ddd'
 