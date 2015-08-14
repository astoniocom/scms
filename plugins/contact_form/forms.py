# coding=utf-8
from models import ContactForm
from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
#import supercaptcha
from django_fortima_utils.form_honeypots import FormHoneypotsField

class FormContactForm(forms.Form):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix='',
                 empty_permitted=False, fields={}):

        self.base_fields = SortedDict()

        for id, field_desc in fields['values'].iteritems():
            field_name = 'field_%s' % id
            if field_desc['type_id'] == 'text_field':
                self.base_fields[field_name] = forms.CharField(label=field_desc['name'], max_length=200, required=field_desc['required'])
            elif field_desc['type_id'] == 'text_area': 
                self.base_fields[field_name] = forms.CharField(label=field_desc['name'], max_length=5000, required=field_desc['required'], widget=forms.Textarea())
            elif field_desc['type_id'] == 'email':
                self.base_fields[field_name] = forms.EmailField(label=field_desc['name'], required=field_desc['required'])


        #self.base_fields['captcha'] = supercaptcha.CaptchaField(label=u'Код на картинке')
        self.base_fields['fhp'] = FormHoneypotsField(timelimit=5)
        
        super(FormContactForm, self).__init__(data, files, auto_id, prefix, initial,
                                          error_class, label_suffix, empty_permitted)