# coding=utf-8
from django.contrib import admin
from models import Parameter, Parameters, Color
from django.forms import widgets
from django.utils.translation import ugettext as _

class ParameterAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'vocabulary', 'name', 'measure', 'weight')
    list_filter = ('vocabulary', 'name')
    list_editable = ('weight', 'measure')
    readonly_fields = ()
    declared_fieldsets = ()
    fieldsets = (
       (None, {'fields': ('vocabulary', 'name', 'measure', 'weight')}),
    )
        
    # def get_form(self, request, obj=None, **kwargs):
    #     form = super(Parameters, self).get_form(request, obj, **kwargs)
    #     self.declared_fieldsets = None
        
    #     advanced = []
    #     all = ['name', 'vocabulary', 'language', 'description', 'weight']
        # if 'language' in request.GET:
        #     advanced += ['language']
        #     all.remove('language')
        # if 'vocabulary' in request.GET:
        #     advanced += ['vocabulary']
        #     all.remove('vocabulary')

        # Переформировываем вывод, чтобы неважные поля были скрыты
        # if advanced:
        #     advanced += ['description']
        #     all.remove('description')
        #     advanced += ['weight']
        #     all.remove('weight')
        #     self.declared_fieldsets = (
        #         (None, {'fields': all,}),
        #         (_('Advanced options'), {'classes': ('collapse',), 'fields': advanced,}),
        #     )
        # return form


admin.site.register(Parameter, ParameterAdmin)

class ColorAdmin(admin.ModelAdmin):
    pass
admin.site.register(Color, ColorAdmin)
