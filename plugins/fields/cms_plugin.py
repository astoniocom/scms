# coding: utf-8
from scms.plugin_base import SCMSPluginBase
from models import Fields
from forms import FieldsForm
from utils import get_classplugin_from_str
from scms.utils import query_str_to_dict
import inspect
from django.utils.datastructures import ImmutableList

class FieldsPlugin(SCMSPluginBase):
    form = FieldsForm
    model = Fields
    template = 'admin/scms/page/edit_inline/tabular.html'


    def __init__(self, 
                 name, 
                 verbose_name=None, 
                 verbose_name_plural=None, 
                 form=None, 
                 formset=None, 
                 extra=3, 
                 can_order=False, 
                 lang_depended=True, 
                 can_delete=True, 
                 max_num=1, 
                 template = None,
                 filter_type = None,
                 show_weight = True,
                 is_slave=False):
        self.lang_depended = False
        self.is_slave = is_slave # Маркер конфигурируем поли, или же отображаем поля
        super(FieldsPlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, show_weight, filter_type)
        
    def get_inline_instances(self, obj=None):
        if self.is_slave:
            if not obj:
                return []
            
            inline_instances = []
            ancestors = obj.get_ancestors()
            fields = Fields.objects.filter(page__in = ancestors).order_by('weight')
            for field in fields:
                p_class = get_classplugin_from_str(field.type)
                
                if not p_class:
                    continue
    
                init_values = query_str_to_dict(field.ext_params)
                
                if field.verbose_name:
                    init_values['verbose_name'] = field.verbose_name
                    
                if field.extra:
                    init_values['extra'] = field.extra
                init_values['can_order'] = field.can_order
                init_values['lang_depended'] = field.lang_depended
                init_values['can_delete'] = field.can_delete
                if field.max_num:
                    init_values['max_num'] = field.max_num
                if field.filter_type:
                    init_values['filter_type'] = field.filter_type
                # Получаем список всех параметров, которые принимает функция
                init_attribs=inspect.getargspec(p_class.__init__) 
                init_attribs=init_attribs[0] + ['verbose_name','verbose_name_plural','form','formset','extra','can_order','lang_depended','can_delete','max_num','template','filter_type','show_weight'] # тут 1й список, то что функция принимает, а второй, что обязательно может принимать базовый класс Plugin, но тут лучще не в ручную, а по классу плагина, либо класс плагина через родителя определять TODO
                init_attribs.remove('self') # убираем параметр self
                for key in init_values.keys():
                    if key not in init_attribs: # если значение из словаря подготовленных для функции значений
                        del init_values[key]    # не принимается самой функцией, удаляем его из словаря
                    pass
                                
                        
                #try:
                inline_instance = p_class(field.name, **init_values)
                inline_instance.dynamic = True
                inline_instance.group_name = field.field_name

                #except: # Возможно, не все параметры что необходимы для плагина установлены в поле дополнительные параметры
                #    continue
                inline_instances.append(inline_instance)
            return inline_instances
        else:
            return [self]        