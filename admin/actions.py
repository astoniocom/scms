# coding=utf-8
from django.contrib.admin import actions
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib import messages
from scms.models import Page

def delete_selected(modeladmin, request, queryset):
    filtered_qs = []
    for obj in queryset:
        if modeladmin.has_delete_permission(request, obj):
            filtered_qs.append(obj.pk)
        else:
            messages.warning(request, _("Cannot delete %(name)s") % {"name": obj.title})
    filtered_qs = Page.objects.filter(pk__in=filtered_qs)
    if filtered_qs:
        result = actions.delete_selected(modeladmin, request, filtered_qs)
        if not request.POST.get('post'):
            result.context_data['breadcrumbs'] = request.scms['page'].full_load().parents
        return result
    else:
        return None
delete_selected.short_description = ugettext_lazy("Delete selected %(verbose_name_plural)s")