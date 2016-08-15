# coding=utf-8
from models import TextArea
from django import forms
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

class TextAreaForm(forms.ModelForm):
    class Meta:
        model = TextArea
        
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        
        super(TextAreaForm, self).__init__(data, files, auto_id, prefix, initial,
                                            error_class, label_suffix, empty_permitted, instance)
        self.base_fields['body'] = self.fields['body'] = forms.CharField(label=_("Text"), widget=forms.Textarea({'rows': self.rows, 'style': "width: 100%"}), required=False)


