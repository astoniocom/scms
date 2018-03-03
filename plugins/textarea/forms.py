# coding=utf-8
from models import TextArea
from django import forms
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

class TextAreaForm(forms.ModelForm):
    class Meta:
        model = TextArea
        
    def __init__(self, *args, **kwargs):
        
        super(TextAreaForm, self).__init__(*args, **kwargs)
        self.base_fields['body'] = self.fields['body'] = forms.CharField(label=_("Text"), help_text="asfasdf", widget=forms.Textarea({'rows': self.rows, 'style': "width: 100%"}), required=False)


