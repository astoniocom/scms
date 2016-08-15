# coding=utf-8
from models import File
from django import forms
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

class FileForm(forms.ModelForm):
    description = forms.CharField(label=_("Description"), widget=forms.TextInput(attrs = {'size': 90}), required=False)
    
    class Meta:
        model = File
        fields = "__all__"
        
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
             initial=None, error_class=ErrorList, label_suffix=':',
             empty_permitted=False, instance=None):
        from scms.utils import build_page_folder_path
        

        super(FileForm, self).__init__(data, files, auto_id, prefix, initial,
                                    error_class, label_suffix, empty_permitted, instance)
            
        self.fields['file'].widget.directory = build_page_folder_path(self.page.id, isrelative = True)

