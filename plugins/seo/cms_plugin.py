from scms.plugin_base import SCMSPluginBase
from models import SEO
from django.forms.models import ModelForm
from django.forms.util import ErrorList

class SEOPluginModelForm(ModelForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        
        super(SEOPluginModelForm, self).__init__(data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted, instance)
        self.fields['title'].widget.attrs['style'] = 'width: 85%;'
        self.fields['keywords'].widget.attrs['style'] = 'width:85%;'
        self.fields['description'].widget.attrs['style'] = 'width: 85%;'
        self.fields['description'].widget.attrs['rows'] = 2
        
class SEOPlugin(SCMSPluginBase):
    model = SEO
    template = 'admin/scms/page/edit_inline/stacked_1.html'
    form = SEOPluginModelForm




