# coding=utf-8
from models import Fields
from django import forms
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from utils import get_classplugin_from_str
from scms.utils import query_str_to_dict
import inspect

class FieldsForm(forms.ModelForm):
    class Meta:
        model = Fields
        fields = "__all__"
        
    def clean(self):
        if 'type' in self.cleaned_data and 'ext_params' in self.cleaned_data:
            errors = []
            
            # Проверяем, чтобы дополнительные параметры были из ряда допустимых
            p_class = get_classplugin_from_str(self.cleaned_data['type'])
                    
            if not p_class:
                raise ValidationError("Выбран недоступный тип поля.")
    
            try:
                init_values = query_str_to_dict(self.cleaned_data['ext_params'])
            except ValueError:
                errors += ['Ошибка форматирования строки параметров.']
                
            if not errors:
                # Получаем список всех параметров, которые принимает функция
                init_attribs=inspect.getargspec(p_class.__init__) 
                init_attribs=init_attribs[0]
                init_attribs.remove('self') # убираем атрибуты общие для всех плагинов
                for field_name in ('name', 'verbose_name', 'verbose_name_plural', 'form', 'formset', 'extra', 'can_order', 'lang_depended', 'can_delete', 'max_num', 'template', 'filter_type'):
                    if field_name in init_attribs:
                        init_attribs.remove(field_name)
                
                for key in init_values.keys():
                    if key not in init_attribs: # если значение из словаря подготовленных для функции значений
                        errors += ["Параметр `%s` является недопустимым для данного типа поля." % key]                
                        if len(init_attribs):
                            errors += ["Допустимые параметры: %s" % ', '.join(init_attribs)]                    
                        else:
                            errors += ["Для данного типа поля не существует дополнительных параметров."]
            if errors:
                del self.cleaned_data['ext_params']
                self._errors['ext_params'] = ErrorList(errors)                
        return self.cleaned_data

