# coding=utf-8
from django.contrib import admin
from models import PVParams
from django.utils.translation import ugettext as _

class PVParamsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'language', )
    list_filter = ('language',)
        
admin.site.register(PVParams, PVParamsAdmin)
        
