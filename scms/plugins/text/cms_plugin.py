from django.forms.models import ModelForm
from django.forms.utils import ErrorList
from django.forms.widgets import Select
from scms.plugin_base import SCMSPluginBase
from .models import Text

class TextPluginModelForm(ModelForm):
    choices = None
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.fields['body'].widget.attrs['style'] = 'width: 100%;'
        

class TextPlugin(SCMSPluginBase):
    model = Text
    form = TextPluginModelForm
    choices = None
    
    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('choices', None)
        super(TextPlugin, self).__init__(*args, **kwargs)
        



    def get_plugin_formset(self, *args, **kwargs):
        formset = super(TextPlugin, self).get_plugin_formset(*args, **kwargs)
        
        if self.choices: 
            for next_form in formset.forms:
                next_form.fields['body'].widget = Select(choices=self.choices)    
        return formset