# coding=utf-8
from django.conf import settings
import scms

class CMSContent(object):
    name = ''
    id = ''
    admin_list = []
    children = []
    permissions = [] # TODO избавиться от пермиссинс
    get_queryset = None
    adminlist_ordering = ()
    icon = ''

    def __init__(self, id, name, admin_list = ['weight'], admin_list_exclude = [], children = [], permissions = ['edit', 'delete', 'create'], get_queryset = None, adminlist_ordering = (), icon=None ):
        self._fields = []
        self.name = name # человеческое название
        self.id = id # строка-идентификатор
        self.admin_list = admin_list + ['adminlist_children', 'adminlist_slug', 'adminlist_type', 'published', 'hidden', ]
        for col in admin_list_exclude:
            if col in self.admin_list:
                self.admin_list.remove(col)
        
        self.children = children
        self.permissions = permissions # TODO избавиться от пермиссинс
        self.permissions.append('view') # Просмотр доступен всегда
        self.get_queryset = get_queryset
        self.adminlist_ordering = adminlist_ordering
        
        if not icon:
            self.icon = 'scms/icons/%s.png' % self.id
        else:
            self.icon = icon
            
		
    def register_field(self, plugin):
        self._fields.append(plugin)
		
    def get_fields(self, obj=None):
        inlines = []
        for field in self._fields:
            inlines += field.get_inline_instances(obj)
        return inlines

    def get_changelist_fields(self, with_no_plugin_fields=False):
        result = []
        for col in self.admin_list: # Пробегаем каждый столец для отображения
            if isinstance(col, dict): # Если это словарь, а не просто текст, значит, поле из плагина 
                for child in self.children: # Пробегаем типы возможных потомков
                    for plugin_field in scms.site.get_content_type(child).get_fields(): # Пробегаем поля каждого следующего возможного типа потомков
                        if plugin_field.name == col['field']: # Если поле совпадает с тем, что мы хотим
                            field_info = col.copy()
                            field_info['field'] = plugin_field
                            field_info['pos'] = col.get('pos', 0)
                            field_info['db_field'] = col['col']
                            field_info['column_name'] = col.get('name', plugin_field.verbose_name) 
                            field_info['list_name'] = '%s_%s_%s' % (field_info['field'].name, col['col'], field_info['pos'])
                            result.append(field_info)
            elif with_no_plugin_fields:
                result.append(col)
        return result