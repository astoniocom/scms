# coding=utf-8
from django.contrib.admin import actions
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib import messages
from scms.models import Page, Slugs
from scms.plugins.wysiwyg.models  import TinyMCE
import scms

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

import copy

def copy_selected(modeladmin, request, queryset):
    for sd in queryset:
        copy_page(sd)

copy_selected.short_description = "Скопировать выбранные страницы".decode('utf-8')
#copy_selected.short_description = ugettext_lazy("Copy selected %(verbose_name_plural)s") 
# нужено сделать django-admin.py makemessages -l ru

# функция копирования объекта вместе с его полями
def copy_page(obj):
    # Полное копирование страницы
    obj = Page(pk=obj.pk).full_load(only_cached=False)
    type = scms.site.get_content_type(obj.type)
    inline_instances = scms.site.get_content_type(obj.type).get_fields(obj)
    old_fields = obj.fields.items()
    old_authors = obj.authors.all()
    old_slug = Slugs.objects.get(page=obj)
    obj.lft = None
    obj.rft = None
    obj.tree_id = None
    obj.id = None
    obj.save()
    obj.authors = old_authors
    old_slug.page = obj
    old_slug.id = None
    old_slug.slug = ""
    old_slug.alias = None
    old_slug.save()

    for val in old_fields:
        field = val[-1]
        for value in field['values'].values():
            pk  = value['id']
            f = field['plugin'].__class__.model.objects.get(pk=pk)
            f.id = None
            f.page = obj
            f.save()
    #pagecache_delete(p.pk, lang, p.type)
    obj.save()
    return obj
