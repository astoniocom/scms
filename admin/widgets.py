# coding=utf-8
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

class CMSForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    def __init__(self, parent_type, *args, **kwargs):
        self.parent_type = parent_type
        super(CMSForeignKeyRawIdWidget, self).__init__(*args, **kwargs)
        
    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR, ERROR_FLAG
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        params.update({'parent_type': self.parent_type})
        return params
    
    def label_for_value(self, value):
        # сделано с целью предотвращения ошибки, если в поле введен
        # идентификтор несуществующей страницы.
        from django.utils.html import escape
        from django.utils.text import Truncator
        
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            return ''
        return '&nbsp;<strong>%s</strong>' % escape(Truncator(obj).chars(14))
    
"""
class ModelChoiceParent(ModelChoiceField):
    # преопределено для того, чтобы в случае, когда в поле записано не число, а строка, не выдавала ошибку
    def to_python(self, value):
        if value:
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(self.error_messages['invalid_choice'])
        
        return super(ModelChoiceParent, self).to_python(value)
"""