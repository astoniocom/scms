# coding=utf-8
from django.contrib.admin.views import main
from scms.utils import get_query_string
from scms.models import Slugs, page_state
from scms.utils.i18n import get_default_language
from django.conf import settings
import scms

main.IGNORED_PARAMS = main.IGNORED_PARAMS + ('parent_type',)

class SCMSChangeList(main.ChangeList):
    def __init__(self, request, model, *args):
        # Блок определения ссылок списка для строк "На уровень в верх" и "В корень"
        self.list_toroot_link = None
        self.list_toup_link = None    
        if request.scms['page'].id:
            self.list_toroot_link = self.list_toup_link = get_query_string(request.GET, remove=['parent__id__exact'], addq=True)
            if request.scms['page'].parent_id:
                  self.list_toup_link = get_query_string(request.GET, new_params={'parent__id__exact': str(request.scms['page'].parent_id)}, addq=True)
          
        super(SCMSChangeList, self).__init__(request, model, *args)
    
    def get_ordering(self, request, queryset):
        adminlist_ordering = scms.site.get_content_type(request.scms['page_type']).adminlist_ordering 
        if main.ORDER_VAR in self.params or not adminlist_ordering:
            return super(SCMSChangeList, self).get_ordering(request, queryset)
        else:
            return adminlist_ordering 
    
    def get_query_set(self, request):
        qs = super(SCMSChangeList, self).get_query_set(request)
        
        
        page_table_name = self.model._meta.db_table
        slugs_table_name = Slugs._meta.db_table
        language = getattr(settings, 'SCMS_ADMIN_LIST_LANG', get_default_language())

        select = {}
        
        parent_content_type = scms.site.get_content_type(request.scms['page_type'])
        for plugin_field_info in parent_content_type.get_changelist_fields():
            plugin_qs = plugin_field_info['field'].model.objects \
                .filter(
                    language='"%s"' % language, 
                    field_name='"%s"' % plugin_field_info['field'].name) \
                .extra(
                    select = {plugin_field_info['db_field']: '`%s`.`%s`' % (plugin_field_info['field'].model._meta.db_table, plugin_field_info['db_field'])},
                    where=['`%s`.`id` = `page_id`' % page_table_name])[plugin_field_info['pos']:plugin_field_info['pos']+1] # Лимит на случай нескольких полей
    
            plugin_qs.query.default_cols = False
            select[plugin_field_info['list_name']] = str(plugin_qs.query) 

        # Добавляем в селект поля модели Slugs и подсчет количества потомков
        select['title'] = '`%s`.`title`' % slugs_table_name 
        select['slug'] = '`%s`.`slug`' % slugs_table_name
        select['alias'] = 'IF (`'+page_table_name+'`.`state`='+str(page_state.MAIN)+', "/", REPLACE(`'+slugs_table_name+'`.`alias`,"*",""))'
        select['nchildren'] = 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (page_table_name, page_table_name)
        
        qs = qs \
            .filter(slugs__language='%s' % language) \
            .exclude(state__in=[page_state.EXTRAHIDDEN, page_state.IN_TRASH, page_state.SETTINGS]) \
            .extra(select=select)

        # TODO!!! Проверить корректность следующих строк
        queryset_ext = scms.site.get_content_type(request.scms['page_type']).get_queryset # дополнительный фильтр в зависимости от родительского контента
        if queryset_ext:
            qs = request.queryset_ext(self.model, language, qs)

        # Если не установлен родитель устанавливаем его как корень,
        # если установлен django.admin добавит соответствующий фильтр самостоятельно
        if 'parent__id__exact' not in request.GET:
            qs = qs.filter(parent__id__exact = None)
        return qs
