# coding=utf-8
from models import Terms
from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.forms.widgets import Select, SelectMultiple
from django.forms.models import ModelMultipleChoiceField, ModelChoiceField
from django.utils.safestring import mark_safe
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch
from urlparse import urljoin

class SCMSRelatedFieldWidgetWrapper(RelatedFieldWidgetWrapper):
    def __init__(self, widget, rel, admin_site, vocabulary, language):
        super(SCMSRelatedFieldWidgetWrapper, self).__init__(widget, rel, admin_site)
        self.vocabulary = vocabulary
        self.language = language
         
    def render(self, name, value, *args, **kwargs):
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        try:
            related_url = reverse('admin:%s_%s_add' % info, current_app=self.admin_site.name)
        except NoReverseMatch:
            info = (self.admin_site.root_path, rel_to._meta.app_label, rel_to._meta.object_name.lower())
            related_url = '%s%s/%s/add/' % info
        related_url += '?vocabulary=%s&language=%s' % (self.vocabulary, self.language) # единственная строчка, добавленная мною в изначальную функцию
        self.widget.choices = self.choices
        output = [self.widget.render(name, value, *args, **kwargs)]
        if rel_to in self.admin_site._registry: # If the related object has an admin interface:
            # TODO: "id_" is hard-coded here. This should instead use the correct
            # API to determine the ID dynamically.
            output.append(u'<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
                (related_url, name))
            output.append(u'<img src="%s" width="10" height="10" alt="%s"/></a>' % (urljoin(settings.STATIC_URL, 'admin/img/icon_addlink.gif'), _('Add Another')))
        return mark_safe(u''.join(output))
    
class TaxonomyForm(forms.ModelForm):
    #terms = forms.ModelMultipleChoiceField(label=_("Terms"), widget=RelatedFieldWidgetWrapper())
    class Meta:
        model = Terms
        
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                initial=None, error_class=ErrorList, label_suffix=':',
                empty_permitted=False, instance=None):
        
        # Формируем список возможных значений
        queryset = Terms.objects.filter(vocabulary=self.admin_field.vocabulary)
        if self.admin_field.lang_depended:
            queryset = queryset.filter(language=self.language)
        
        # Определяем язык
        language = self.admin_field.lang_depended and self.language or ''
        
        # Обращаемся к обработчику по-умолчанию
        super(TaxonomyForm, self).__init__(data, files, auto_id, prefix, initial,
                               error_class, label_suffix, empty_permitted, instance)
        
        old_widget = self.fields['terms'].widget
        
        if self.admin_field.multiple: # Если поле множественного выбора
            widget = SelectMultiple(old_widget.widget.attrs, queryset)
            widget_wrapped = SCMSRelatedFieldWidgetWrapper(widget, old_widget.rel, old_widget.admin_site, self.admin_field.vocabulary, language)
            self.fields['terms'] = ModelMultipleChoiceField(queryset, required=False, widget=widget_wrapped)
        else: # Если поле одиночного выбора
            widget = Select(old_widget.widget.attrs, queryset)
            widget_wrapped = SCMSRelatedFieldWidgetWrapper(widget, old_widget.rel, old_widget.admin_site, self.admin_field.vocabulary, language)
            self.fields['terms'] = ModelChoiceField(queryset, required=False, widget=widget_wrapped)
            try: # Определяем значение по умолчанию -- первое в списке значений
                initial = instance.terms.get_query_set()[0].id
            except:
                initial = None
            self.initial['terms'] = initial
            self.fields['terms'].initial = initial
        pass
        
    def clean(self):
        if 'terms' in self.cleaned_data:
            if self.cleaned_data['terms']: # Вдруг он None
                errors = []
    
                if not self.admin_field.multiple:
                    self.cleaned_data['terms'] = (self.cleaned_data['terms'],) # Т.к. обработчик django всё еще думает, что у нас множественный выбор, но если это поле одиночного выбора, то надо приводить к списку
                    
                for term in self.cleaned_data['terms']: # Проверяем каждый термин и помещаем все ошибки в список ошибок
                    if not term.vocabulary == self.admin_field.vocabulary :
                        errors += [_('Value "%(value)s" cannot be selected since it belongs to other vocabulary (%(voc)s)') % {'value': str(term), 'voc': term.vocabulary}]
                        
                    language = self.admin_field.lang_depended and self.language or ''
                    if not term.language == language:
                        errors += [_('Value "%(value)s" cannot be selected since it belongs to other language (%(lang)s)') % {'value':str(term), 'lang': term.language}]
                    
                if errors:
                    self._errors['terms'] = ErrorList(errors)
                    del self.cleaned_data['terms']
            else:
                self.cleaned_data['terms'] = []  # На случай, если ничего не выбрано при поле одиночного выбора
        return self.cleaned_data
      
            
        
        
