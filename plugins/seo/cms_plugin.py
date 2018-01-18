from django.forms.models import ModelForm
from django.forms.utils import ErrorList
from scms.plugin_base import SCMSPluginBase
from .models import SEO

class SEOPluginModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['style'] = 'width: 85%;'
        self.fields['keywords'].widget.attrs['style'] = 'width:85%;'
        self.fields['description'].widget.attrs['style'] = 'width: 85%;'
        self.fields['description'].widget.attrs['rows'] = 2
        
class SEOPlugin(SCMSPluginBase):
    model = SEO
    # template = 'admin/scms/page/edit_inline/stacked_1.html'
    template = 'admin/edit_inline/stacked.html'
    form = SEOPluginModelForm




