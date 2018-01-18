# coding=utf-8
from django import forms
from django.utils.translation import ugettext_lazy as _
from .models import PageSelect

class PageSelectForm(forms.ModelForm):
    description = forms.CharField(label=_("Description"), widget=forms.TextInput(attrs = {'size': 90}), required=False)

    class Meta:
        model = PageSelect
        fields = "__all__"

