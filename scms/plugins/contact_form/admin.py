# coding=utf-8
from django.contrib import admin
from django.forms import widgets
from django.utils.safestring import mark_safe
from django import forms
from django.utils.translation import ugettext as _
from .models import ContactFormHistory

class ContactFormHistoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'adminlist_alias', 'recipient', 'date', )
    list_filter = ('alias', 'date', 'recipient',)
    readonly_fields = ('page', 'date', 'recipient', 'alias', 'body',)
    exclude = ('type',)
    declared_fieldsets = ()

    def adminlist_alias(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (obj.alias, obj.alias))
    adminlist_alias.allow_tags = True
    adminlist_alias.short_description = _('Sent from page')

admin.site.register(ContactFormHistory, ContactFormHistoryAdmin)
        
