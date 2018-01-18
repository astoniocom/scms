# coding=utf-8
from django.contrib import admin
from django.forms import widgets
from django.utils.translation import ugettext as _
from .models import Terms

class TermsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'vocabulary', 'language', 'weight')
    list_filter = ('vocabulary', 'language')
    list_editable = ('weight',)
    readonly_fields = ()
    declared_fieldsets = ()
        
    def get_form(self, request, obj=None, **kwargs):
        form = super(TermsAdmin, self).get_form(request, obj, **kwargs)
        self.declared_fieldsets = None
        
        advanced = []
        all = ['name', 'vocabulary', 'language', 'description', 'weight']
        if 'language' in request.GET:
            advanced += ['language']
            all.remove('language')
        if 'vocabulary' in request.GET:
            advanced += ['vocabulary']
            all.remove('vocabulary')

        # Переформировываем вывод, чтобы неважные поля были скрыты
        if advanced:
            advanced += ['description']
            all.remove('description')
            advanced += ['weight']
            all.remove('weight')
            self.declared_fieldsets = (
                (None, {'fields': all,}),
                (_('Advanced options'), {'classes': ('collapse',), 'fields': advanced,}),
            )
        return form


admin.site.register(Terms, TermsAdmin)
        
