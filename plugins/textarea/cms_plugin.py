from scms.plugin_base import SCMSPluginBase
from models import TextArea
from django import forms
from django.utils.translation import ugettext_lazy as _

class TextAreaPlugin(SCMSPluginBase):
    model = TextArea

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
                 show_weight = False,
                 rows = 10,):
        self.rows = rows
        super(TextAreaPlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, filter_type, show_weight)
   
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'body':
            return forms.CharField(label=_("Text"), widget=forms.Textarea({'rows': self.rows, 'style': "width: 100%"}), required=False)
        return super(TextAreaPlugin, self).formfield_for_dbfield(db_field, **kwargs)