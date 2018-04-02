# coding=utf-8
from django import forms
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _
from .models import File

class FileForm(forms.ModelForm):
    description = forms.CharField(label=_("Description"), widget=forms.TextInput(attrs = {'size': 90}), required=False)
    
    class Meta:
        model = File
        fields = "__all__"
        
    def __init__(self, *args, **kwargs):
        from scms.utils import build_page_folder_path
        

        super().__init__(*args, **kwargs)
            
        self.fields['file'].widget.directory = build_page_folder_path(self.page.id, isrelative = True)

